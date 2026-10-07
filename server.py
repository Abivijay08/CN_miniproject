"""
Library Management System - SERVER
Computer Networks Laboratory Project
Multi-threaded TCP server using Python sockets + SQLite.
Protocol: one JSON object per line (newline-delimited) over TCP.
Usage: python server.py [port]
"""
import socket
import threading
import sqlite3
import json
import hashlib
import secrets
import sys
from datetime import datetime, timedelta

HOST = "0.0.0.0"          # listen on all network interfaces
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
DB_FILE = "library.db"
LOAN_DAYS = 14
FINE_PER_DAY = 2          # Rs. per overdue day
DATE_FMT = "%Y-%m-%d"
db_lock = threading.Lock()


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def hash_pw(password, salt):
    return hashlib.sha256((salt + password).encode()).hexdigest()


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        salt TEXT NOT NULL,
        pw_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'member');
    CREATE TABLE IF NOT EXISTS books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        copies INTEGER NOT NULL DEFAULT 1,
        available INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS loans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        return_date TEXT);
    """)
    if not conn.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        salt = secrets.token_hex(8)
        conn.execute("INSERT INTO users(username,salt,pw_hash,role) VALUES(?,?,?,?)",
                     ("admin", salt, hash_pw("admin123", salt), "admin"))
    if not conn.execute("SELECT 1 FROM books").fetchone():
        sample = [("Computer Networks", "Andrew S. Tanenbaum", 3),
                  ("Data Communications and Networking", "Behrouz Forouzan", 2),
                  ("Operating System Concepts", "Silberschatz", 2),
                  ("Introduction to Algorithms", "Cormen", 1)]
        for t, a, c in sample:
            conn.execute("INSERT INTO books(title,author,copies,available) VALUES(?,?,?,?)", (t, a, c, c))
    conn.commit()
    conn.close()


# ---------------- request handlers ----------------
def ok(**kw):
    return {"status": "ok", **kw}


def err(msg):
    return {"status": "error", "message": msg}


def do_register(db, s, r):
    u, p = r.get("username", "").strip(), r.get("password", "")
    if len(u) < 3 or len(p) < 4:
        return err("Username must be >= 3 and password >= 4 characters.")
    salt = secrets.token_hex(8)
    try:
        db.execute("INSERT INTO users(username,salt,pw_hash,role) VALUES(?,?,?,'member')",
                   (u, salt, hash_pw(p, salt)))
        db.commit()
    except sqlite3.IntegrityError:
        return err("Username already exists.")
    return ok(message="Registration successful. Please login.")


def do_login(db, s, r):
    row = db.execute("SELECT * FROM users WHERE username=?", (r.get("username", ""),)).fetchone()
    if not row or row["pw_hash"] != hash_pw(r.get("password", ""), row["salt"]):
        return err("Invalid username or password.")
    s["user"] = {"id": row["id"], "username": row["username"], "role": row["role"]}
    return ok(message=f"Welcome, {row['username']}!", role=row["role"])


def do_logout(db, s, r):
    s["user"] = None
    return ok(message="Logged out.")


def do_list(db, s, r):
    rows = db.execute("SELECT id,title,author,copies,available FROM books ORDER BY id").fetchall()
    return ok(books=[dict(x) for x in rows])


def do_search(db, s, r):
    q = f"%{r.get('query', '')}%"
    rows = db.execute("SELECT id,title,author,copies,available FROM books "
                      "WHERE title LIKE ? OR author LIKE ?", (q, q)).fetchall()
    return ok(books=[dict(x) for x in rows])


def do_add(db, s, r):
    t, a, c = r.get("title", "").strip(), r.get("author", "").strip(), int(r.get("copies", 1))
    if not t or not a or c < 1:
        return err("Title, author and copies (>=1) are required.")
    db.execute("INSERT INTO books(title,author,copies,available) VALUES(?,?,?,?)", (t, a, c, c))
    db.commit()
    return ok(message="Book added.")


def do_remove(db, s, r):
    bid = int(r.get("book_id", 0))
    if db.execute("SELECT 1 FROM loans WHERE book_id=? AND return_date IS NULL", (bid,)).fetchone():
        return err("Cannot remove: copies of this book are currently issued.")
    cur = db.execute("DELETE FROM books WHERE id=?", (bid,))
    db.commit()
    return ok(message="Book removed.") if cur.rowcount else err("Book not found.")


def do_issue(db, s, r):
    bid, uid = int(r.get("book_id", 0)), s["user"]["id"]
    book = db.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()
    if not book:
        return err("Book not found.")
    if book["available"] < 1:
        return err("No copies available right now.")
    if db.execute("SELECT 1 FROM loans WHERE book_id=? AND user_id=? AND return_date IS NULL",
                  (bid, uid)).fetchone():
        return err("You already have this book.")
    if db.execute("SELECT COUNT(*) c FROM loans WHERE user_id=? AND return_date IS NULL",
                  (uid,)).fetchone()["c"] >= 3:
        return err("Borrow limit reached (max 3 books).")
    today = datetime.now()
    due = today + timedelta(days=LOAN_DAYS)
    db.execute("INSERT INTO loans(book_id,user_id,issue_date,due_date) VALUES(?,?,?,?)",
               (bid, uid, today.strftime(DATE_FMT), due.strftime(DATE_FMT)))
    db.execute("UPDATE books SET available=available-1 WHERE id=?", (bid,))
    db.commit()
    return ok(message=f"Issued '{book['title']}'. Due date: {due.strftime(DATE_FMT)}")


def do_return(db, s, r):
    bid, uid = int(r.get("book_id", 0)), s["user"]["id"]
    loan = db.execute("SELECT * FROM loans WHERE book_id=? AND user_id=? AND return_date IS NULL",
                      (bid, uid)).fetchone()
    if not loan:
        return err("You have not borrowed this book.")
    now = datetime.now()
    late = (now - datetime.strptime(loan["due_date"], DATE_FMT)).days
    fine = max(0, late) * FINE_PER_DAY
    db.execute("UPDATE loans SET return_date=? WHERE id=?", (now.strftime(DATE_FMT), loan["id"]))
    db.execute("UPDATE books SET available=available+1 WHERE id=?", (bid,))
    db.commit()
    msg = "Book returned." + (f" Overdue fine: Rs. {fine}" if fine else " No fine.")
    return ok(message=msg)


def do_my_books(db, s, r):
    rows = db.execute("""SELECT b.id,b.title,l.issue_date,l.due_date FROM loans l
                         JOIN books b ON b.id=l.book_id
                         WHERE l.user_id=? AND l.return_date IS NULL""", (s["user"]["id"],)).fetchall()
    return ok(loans=[dict(x) for x in rows])


def do_all_loans(db, s, r):
    rows = db.execute("""SELECT u.username,b.title,l.issue_date,l.due_date FROM loans l
                         JOIN books b ON b.id=l.book_id JOIN users u ON u.id=l.user_id
                         WHERE l.return_date IS NULL ORDER BY l.due_date""").fetchall()
    return ok(loans=[dict(x) for x in rows])


# command -> (handler, auth_required, admin_only)
COMMANDS = {
    "register": (do_register, False, False),
    "login": (do_login, False, False),
    "logout": (do_logout, True, False),
    "list": (do_list, True, False),
    "search": (do_search, True, False),
    "issue": (do_issue, True, False),
    "return": (do_return, True, False),
    "my_books": (do_my_books, True, False),
    "add": (do_add, True, True),
    "remove": (do_remove, True, True),
    "all_loans": (do_all_loans, True, True),
}


def handle_client(conn, addr):
    print(f"[+] Client connected: {addr[0]}:{addr[1]}")
    session = {"user": None}
    db = get_db()
    try:
        f = conn.makefile("rw", encoding="utf-8", newline="\n")
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                cmd = req.get("cmd")
                if cmd not in COMMANDS:
                    resp = err("Unknown command.")
                else:
                    handler, need_auth, admin_only = COMMANDS[cmd]
                    if need_auth and not session["user"]:
                        resp = err("Please login first.")
                    elif admin_only and session["user"]["role"] != "admin":
                        resp = err("Admin access required.")
                    else:
                        with db_lock:       # serialise DB access across threads
                            resp = handler(db, session, req)
                        who = session["user"]["username"] if session["user"] else "-"
                        print(f"    {addr[0]} [{who}] {cmd}")
            except (ValueError, TypeError) as e:
                resp = err(f"Bad request: {e}")
            f.write(json.dumps(resp) + "\n")
            f.flush()
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        db.close()
        conn.close()
        print(f"[-] Client disconnected: {addr[0]}:{addr[1]}")


def main():
    init_db()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(10)
    print(f"Library Server listening on {HOST}:{PORT}  (Ctrl+C to stop)")
    try:
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
    finally:
        srv.close()


if __name__ == "__main__":
    main()
