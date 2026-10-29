
from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from pathlib import Path
from datetime import date

app = Flask(__name__)
DB_PATH = Path(__file__).with_name("library.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT DEFAULT '',
            quantity INTEGER NOT NULL DEFAULT 1
                CHECK(quantity >= 0)
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT DEFAULT '',
            phone TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS issued_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL REFERENCES books(id),
            student_id INTEGER NOT NULL REFERENCES students(id),
            issue_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT NOT NULL DEFAULT 'Issued'
                CHECK(status IN ('Issued', 'Returned'))
        );
        """)


@app.route("/")
def index():
    with get_db() as db:
        books = db.execute(
            "SELECT * FROM books ORDER BY id DESC"
        ).fetchall()
        students = db.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()
        issues = db.execute("""
            SELECT i.id, b.title AS book_title,
                   s.name AS student_name,
                   i.issue_date, i.return_date, i.status
            FROM issued_books i
            JOIN books b ON b.id = i.book_id
            JOIN students s ON s.id = i.student_id
            ORDER BY i.id DESC
        """).fetchall()
        stats = {
            "books": db.execute(
                "SELECT COUNT(*) FROM books"
            ).fetchone()[0],
            "students": db.execute(
                "SELECT COUNT(*) FROM students"
            ).fetchone()[0],
            "available": db.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM books"
            ).fetchone()[0],
            "issued": db.execute(
                "SELECT COUNT(*) FROM issued_books WHERE status='Issued'"
            ).fetchone()[0]
        }

    return render_template(
        "index.html", books=books, students=students,
        issues=issues, stats=stats
    )


@app.route("/books/add", methods=["POST"])
def add_book():
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    category = request.form.get("category", "").strip()

    try:
        quantity = int(request.form.get("quantity", "1"))
        if not title or not author or quantity < 0:
            raise ValueError
    except ValueError:
        return "Invalid book details", 400

    with get_db() as db:
        db.execute("""
            INSERT INTO books (title, author, category, quantity)
            VALUES (?, ?, ?, ?)
        """, (title, author, category, quantity))

    return redirect(url_for("index"))


@app.route("/books/update/<int:book_id>", methods=["POST"])
def update_book(book_id):
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    category = request.form.get("category", "").strip()

    try:
        quantity = int(request.form.get("quantity", "0"))
        if not title or not author or quantity < 0:
            raise ValueError
    except ValueError:
        return "Invalid book details", 400

    with get_db() as db:
        active = db.execute("""
            SELECT COUNT(*) FROM issued_books
            WHERE book_id=? AND status='Issued'
        """, (book_id,)).fetchone()[0]

        if quantity < active:
            return "Quantity cannot be less than active issues", 400

        cur = db.execute("""
            UPDATE books
            SET title=?, author=?, category=?, quantity=?
            WHERE id=?
        """, (title, author, category, quantity, book_id))

        if cur.rowcount == 0:
            return "Book not found", 404

    return redirect(url_for("index"))


@app.route("/books/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    with get_db() as db:
        history = db.execute(
            "SELECT COUNT(*) FROM issued_books WHERE book_id=?",
            (book_id,)
        ).fetchone()[0]

        if history:
            return "Book has issue history and cannot be deleted", 400

        db.execute("DELETE FROM books WHERE id=?", (book_id,))

    return redirect(url_for("index"))


@app.route("/students/add", methods=["POST"])
def add_student():
    name = request.form.get("name", "").strip()
    department = request.form.get("department", "").strip()
    phone = request.form.get("phone", "").strip()

    if not name:
        return "Student name is required", 400

    with get_db() as db:
        db.execute("""
            INSERT INTO students (name, department, phone)
            VALUES (?, ?, ?)
        """, (name, department, phone))

    return redirect(url_for("index"))


@app.route("/students/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    with get_db() as db:
        history = db.execute(
            "SELECT COUNT(*) FROM issued_books WHERE student_id=?",
            (student_id,)
        ).fetchone()[0]

        if history:
            return "Student has issue history and cannot be deleted", 400

        db.execute("DELETE FROM students WHERE id=?", (student_id,))

    return redirect(url_for("index"))


@app.route("/books/search")
def search_books():
    q = request.args.get("q", "").strip()

    with get_db() as db:
        books = db.execute("""
            SELECT * FROM books
            WHERE title LIKE ? OR author LIKE ? OR category LIKE ?
            ORDER BY title
        """, (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()

    return jsonify([dict(book) for book in books])


@app.route("/issues/add", methods=["POST"])
def issue_book():
    try:
        book_id = int(request.form.get("book_id", ""))
        student_id = int(request.form.get("student_id", ""))
    except ValueError:
        return "Select a valid book and student", 400

    with get_db() as db:
        db.execute("BEGIN IMMEDIATE")

        book = db.execute(
            "SELECT quantity FROM books WHERE id=?", (book_id,)
        ).fetchone()
        student = db.execute(
            "SELECT id FROM students WHERE id=?", (student_id,)
        ).fetchone()

        if not book or not student:
            return "Book or student not found", 404

        if book["quantity"] <= 0:
            return "No copies available", 400

        db.execute("""
            INSERT INTO issued_books
            (book_id, student_id, issue_date, status)
            VALUES (?, ?, ?, 'Issued')
        """, (book_id, student_id, date.today().isoformat()))

        db.execute(
            "UPDATE books SET quantity=quantity-1 WHERE id=?",
            (book_id,)
        )

    return redirect(url_for("index"))


@app.route("/issues/return/<int:issue_id>", methods=["POST"])
def return_book(issue_id):
    with get_db() as db:
        db.execute("BEGIN IMMEDIATE")

        issue = db.execute("""
            SELECT book_id FROM issued_books
            WHERE id=? AND status='Issued'
        """, (issue_id,)).fetchone()

        if not issue:
            return "Active issue not found", 404

        db.execute("""
            UPDATE issued_books
            SET status='Returned', return_date=?
            WHERE id=? AND status='Issued'
        """, (date.today().isoformat(), issue_id))

        db.execute(
            "UPDATE books SET quantity=quantity+1 WHERE id=?",
            (issue["book_id"],)
        )

    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
