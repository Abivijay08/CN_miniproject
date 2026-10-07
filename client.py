"""
Library Management System - CLIENT
Computer Networks Laboratory Project
Connects to the library server over TCP and provides a menu interface.
Usage: python client.py [server_ip] [port]
"""
import socket
import json
import sys
import getpass

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5000


class LibraryClient:
    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(None)
        self.f = self.sock.makefile("rw", encoding="utf-8", newline="\n")

    def request(self, **req):
        self.f.write(json.dumps(req) + "\n")
        self.f.flush()
        line = self.f.readline()
        if not line:
            raise ConnectionError("Server closed the connection.")
        return json.loads(line)

    def close(self):
        try:
            self.f.close()
        finally:
            self.sock.close()


def show_books(books):
    if not books:
        print("  (no books found)")
        return
    print(f"\n  {'ID':<4}{'Title':<38}{'Author':<26}{'Avail/Total'}")
    print("  " + "-" * 78)
    for b in books:
        print(f"  {b['id']:<4}{b['title'][:36]:<38}{b['author'][:24]:<26}{b['available']}/{b['copies']}")


def show_loans(loans, admin=False):
    if not loans:
        print("  (none)")
        return
    for l in loans:
        who = f"{l['username']:<12}" if admin else ""
        print(f"  {who}{l['title'][:36]:<38} issued: {l['issue_date']}  due: {l['due_date']}")


def ask_int(prompt):
    try:
        return int(input(prompt).strip())
    except ValueError:
        return 0


def report(resp):
    print(("  ✔ " if resp["status"] == "ok" else "  ✘ ") + resp.get("message", ""))


def member_menu(c):
    while True:
        print("\n--- MEMBER MENU ---\n1. View all books\n2. Search books\n3. Issue a book\n"
              "4. Return a book\n5. My borrowed books\n6. Logout")
        ch = input("Choice: ").strip()
        if ch == "1":
            show_books(c.request(cmd="list").get("books", []))
        elif ch == "2":
            show_books(c.request(cmd="search", query=input("Search title/author: ")).get("books", []))
        elif ch == "3":
            report(c.request(cmd="issue", book_id=ask_int("Book ID: ")))
        elif ch == "4":
            report(c.request(cmd="return", book_id=ask_int("Book ID: ")))
        elif ch == "5":
            show_loans(c.request(cmd="my_books").get("loans", []))
        elif ch == "6":
            c.request(cmd="logout")
            return
        else:
            print("  Invalid choice.")


def admin_menu(c):
    while True:
        print("\n--- ADMIN MENU ---\n1. View all books\n2. Search books\n3. Add a book\n"
              "4. Remove a book\n5. View all issued books\n6. Logout")
        ch = input("Choice: ").strip()
        if ch == "1":
            show_books(c.request(cmd="list").get("books", []))
        elif ch == "2":
            show_books(c.request(cmd="search", query=input("Search title/author: ")).get("books", []))
        elif ch == "3":
            t, a = input("Title: "), input("Author: ")
            report(c.request(cmd="add", title=t, author=a, copies=ask_int("Copies: ")))
        elif ch == "4":
            report(c.request(cmd="remove", book_id=ask_int("Book ID: ")))
        elif ch == "5":
            show_loans(c.request(cmd="all_loans").get("loans", []), admin=True)
        elif ch == "6":
            c.request(cmd="logout")
            return
        else:
            print("  Invalid choice.")


def main():
    try:
        c = LibraryClient(HOST, PORT)
    except OSError as e:
        print(f"Could not connect to {HOST}:{PORT} -> {e}")
        return
    print(f"Connected to Library Server at {HOST}:{PORT}")
    try:
        while True:
            print("\n=== LIBRARY MANAGEMENT SYSTEM ===\n1. Login\n2. Register\n3. Exit")
            ch = input("Choice: ").strip()
            if ch == "1":
                resp = c.request(cmd="login", username=input("Username: ").strip(),
                                 password=getpass.getpass("Password: "))
                report(resp)
                if resp["status"] == "ok":
                    (admin_menu if resp["role"] == "admin" else member_menu)(c)
            elif ch == "2":
                report(c.request(cmd="register", username=input("Choose username: ").strip(),
                                 password=getpass.getpass("Choose password: ")))
            elif ch == "3":
                break
            else:
                print("  Invalid choice.")
    except (ConnectionError, OSError) as e:
        print(f"\nConnection lost: {e}")
    except KeyboardInterrupt:
        print()
    finally:
        c.close()
        print("Goodbye!")


if __name__ == "__main__":
    main()
