# 📚 Client–Server Library Management System over Network

A **TCP client–server** Library Management System built with Python sockets for the **Computer Networks Laboratory**. The server holds the library database and serves multiple clients at the same time over a network (LAN / localhost). Clients connect, log in, and manage or borrow books through a simple menu interface.

## ✨ Features

**Member**
- Register and log in
- View all books and search by title/author
- Issue a book (14-day loan, max 3 books at a time)
- Return a book (fine of Rs. 2/day if overdue)
- View currently borrowed books

**Admin**
- Add and remove books
- View all issued books across members

**Networking / Server**
- Multi-threaded TCP server (one thread per client)
- Newline-delimited JSON application protocol
- SQLite database with a lock for safe concurrent access
- Salted SHA-256 password hashing
- Role-based access control (admin / member)

## 🧠 Networking Concepts Demonstrated

| Concept | Where used |
|---|---|
| TCP socket programming | `socket.socket(AF_INET, SOCK_STREAM)` |
| Client–server architecture | `server.py` / `client.py` |
| `bind`, `listen`, `accept`, `connect` | Server and client setup |
| Concurrency with threads | One thread per connected client |
| Application-layer protocol | JSON request/response over TCP |
| Ports and IP addressing | Configurable host and port |

## 🏗️ Architecture

```
 ┌──────────────┐   JSON over TCP    ┌─────────────────────┐
 │  Client 1    │ ◄────────────────► │                     │
 ├──────────────┤                    │   Server (threads)  │ ◄──► library.db
 │  Client 2    │ ◄────────────────► │                     │      (SQLite)
 ├──────────────┤                    └─────────────────────┘
 │  Client N    │ ◄────────────────►
 └──────────────┘
```

## 📁 Project Structure

```
library-management-system/
├── server.py    # Multi-threaded TCP server + database logic
├── client.py    # Menu-driven client
└── README.md
```

`library.db` is created automatically on the first server run.

## ⚙️ Requirements

- Python 3.8 or later
- No external libraries (standard library only)

## 🚀 How to Run

**1. Start the server** (on the server machine)

```bash
python server.py            # default port 5000
python server.py 6000       # custom port
```

**2. Start a client** (same machine or any machine on the same network)

```bash
python client.py                         # connects to 127.0.0.1:5000
python client.py 192.168.1.10 5000       # connect to server IP and port
```

To find the server's IP address: `ipconfig` (Windows) or `ifconfig` / `ip a` (Linux/macOS). Make sure the port is allowed through the firewall.

## 🔑 Default Admin Login

| Username | Password |
|---|---|
| `admin` | `admin123` |

New members can register from the client's main menu. Change the default admin password before any real use.

## 📡 Protocol

Each message is a single JSON line terminated by `\n`.

**Request**
```json
{"cmd": "issue", "book_id": 1}
```

**Response**
```json
{"status": "ok", "message": "Issued 'Computer Networks'. Due date: 2026-10-20"}
```

| Command | Access | Parameters |
|---|---|---|
| `register` | Public | `username`, `password` |
| `login` | Public | `username`, `password` |
| `logout` | Logged in | – |
| `list` | Logged in | – |
| `search` | Logged in | `query` |
| `issue` | Logged in | `book_id` |
| `return` | Logged in | `book_id` |
| `my_books` | Logged in | – |
| `add` | Admin | `title`, `author`, `copies` |
| `remove` | Admin | `book_id` |
| `all_loans` | Admin | – |

## 🔮 Future Enhancements

- TLS/SSL encryption for traffic (`ssl` module)
- GUI client (Tkinter)
- Book reservations and email reminders
- Web dashboard for the admin

## 👤 Author

**V. Abishek** – B.E. CSE, Kamaraj College of Engineering and Technology
GitHub: [Abivijay08](https://github.com/Abivijay08)

## 📄 License

Released for educational purposes (Computer Networks Laboratory).
