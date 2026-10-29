
from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import date

app = Flask(__name__)
DB_NAME = "expenses.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                kind TEXT NOT NULL CHECK(kind IN ('Income', 'Expense')),
                category TEXT NOT NULL,
                trans_date TEXT NOT NULL,
                note TEXT DEFAULT ''
            )
        """)


@app.route("/")
def index():
    search = request.args.get("search", "").strip()
    kind = request.args.get("kind", "")
    category = request.args.get("category", "")

    query = "SELECT * FROM transactions WHERE 1=1"
    params = []

    if search:
        query += " AND (title LIKE ? OR category LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if kind in ("Income", "Expense"):
        query += " AND kind = ?"
        params.append(kind)

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY trans_date DESC, id DESC"

    with get_db() as db:
        transactions = db.execute(query, params).fetchall()

        totals = db.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN kind='Income'
                    THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN kind='Expense'
                    THEN amount ELSE 0 END), 0) AS expenses
            FROM transactions
        """).fetchone()

        categories = db.execute("""
            SELECT DISTINCT category
            FROM transactions
            ORDER BY category
        """).fetchall()

        monthly = db.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN kind='Income'
                    THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN kind='Expense'
                    THEN amount ELSE 0 END), 0) AS expenses
            FROM transactions
            WHERE strftime('%Y-%m', trans_date) = strftime('%Y-%m', 'now', 'localtime')
        """).fetchone()

    income = totals["income"]
    expenses = totals["expenses"]

    return render_template(
        "index.html",
        transactions=transactions,
        income=income,
        expenses=expenses,
        balance=income - expenses,
        categories=categories,
        monthly_income=monthly["income"],
        monthly_expenses=monthly["expenses"],
        today=date.today().isoformat(),
        search=search,
        selected_kind=kind,
        selected_category=category
    )


@app.route("/add", methods=["POST"])
def add_transaction():
    title = request.form.get("title", "").strip()
    kind = request.form.get("kind", "")
    category = request.form.get("category", "").strip()
    trans_date = request.form.get("trans_date", "")
    note = request.form.get("note", "").strip()

    try:
        amount = float(request.form.get("amount", "0"))
    except (ValueError, TypeError):
        amount = 0

    if (
        not title or not category or not trans_date
        or amount <= 0 or kind not in ("Income", "Expense")
    ):
        return "Invalid transaction details. Please go back and check the form.", 400

    with get_db() as db:
        db.execute("""
            INSERT INTO transactions
            (title, amount, kind, category, trans_date, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, amount, kind, category, trans_date, note))

    return redirect(url_for("index"))


@app.route("/edit/<int:transaction_id>", methods=["POST"])
def edit_transaction(transaction_id):
    title = request.form.get("title", "").strip()
    kind = request.form.get("kind", "")
    category = request.form.get("category", "").strip()
    trans_date = request.form.get("trans_date", "")
    note = request.form.get("note", "").strip()

    try:
        amount = float(request.form.get("amount", "0"))
    except (ValueError, TypeError):
        amount = 0

    if (
        not title or not category or not trans_date
        or amount <= 0 or kind not in ("Income", "Expense")
    ):
        return "Invalid transaction details.", 400

    with get_db() as db:
        db.execute("""
            UPDATE transactions
            SET title=?, amount=?, kind=?, category=?, trans_date=?, note=?
            WHERE id=?
        """, (
            title, amount, kind, category, trans_date, note,
            transaction_id
        ))

    return redirect(url_for("index"))


@app.route("/delete/<int:transaction_id>", methods=["POST"])
def delete_transaction(transaction_id):
    with get_db() as db:
        db.execute(
            "DELETE FROM transactions WHERE id=?",
            (transaction_id,)
        )

    return redirect(url_for("index"))


@app.route("/api/transactions")
def api_transactions():
    with get_db() as db:
        rows = db.execute("""
            SELECT kind, category, SUM(amount) AS total
            FROM transactions
            GROUP BY kind, category
            ORDER BY kind, category
        """).fetchall()

    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
