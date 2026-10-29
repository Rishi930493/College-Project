
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
import sqlite3
from pathlib import Path
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from secrets import token_hex

app = Flask(__name__)
app.secret_key = "laundry-project-secret-change-later"

DB_PATH = Path(__file__).with_name("laundry.db")

STATUSES = [
    "Pending", "Processing", "Ready",
    "Delivered", "Cancelled"
]


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            price REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            weight REAL NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            payment TEXT DEFAULT 'Unpaid',
            pickup_date TEXT,
            delivery_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(service_id) REFERENCES services(id)
        );
        """)

        admin = db.execute(
            "SELECT id FROM admins WHERE username = ?",
            ("admin",)
        ).fetchone()

        if not admin:
            db.execute(
                "INSERT INTO admins(username, password_hash) VALUES(?, ?)",
                ("admin", generate_password_hash("admin123"))
            )

        services = [
            ("Wash & Fold", 60),
            ("Ironing", 40),
            ("Dry Cleaning", 150),
            ("Wash & Iron", 90)
        ]

        for name, price in services:
            db.execute(
                "INSERT OR IGNORE INTO services(name, price) VALUES(?, ?)",
                (name, price)
            )


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("admin_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as db:
            admin = db.execute(
                "SELECT * FROM admins WHERE username = ?",
                (username,)
            ).fetchone()

        if admin and check_password_hash(
            admin["password_hash"], password
        ):
            session.clear()
            session["admin_id"] = admin["id"]
            session["username"] = admin["username"]
            return redirect(url_for("dashboard"))

        flash("Username किंवा password चुकीचा आहे.", "danger")

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    with get_db() as db:
        customers = db.execute(
            "SELECT COUNT(*) FROM customers"
        ).fetchone()[0]

        orders = db.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]

        pending = db.execute(
            """SELECT COUNT(*) FROM orders
               WHERE status IN ('Pending', 'Processing', 'Ready')"""
        ).fetchone()[0]

        revenue = db.execute(
            """SELECT COALESCE(SUM(total), 0) FROM orders
               WHERE payment = 'Paid'"""
        ).fetchone()[0]

        recent = db.execute("""
            SELECT o.*, c.name AS customer_name,
                   s.name AS service_name
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            JOIN services s ON s.id = o.service_id
            ORDER BY o.id DESC LIMIT 5
        """).fetchall()

    return render_template(
        "dashboard.html",
        customers=customers,
        orders=orders,
        pending=pending,
        revenue=revenue,
        recent=recent
    )


@app.route("/customers", methods=["GET", "POST"])
@login_required
def customers_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        if not name or not phone:
            flash("Name आणि phone आवश्यक आहेत.", "danger")
        else:
            with get_db() as db:
                db.execute("""
                    INSERT INTO customers(name, phone, email, address)
                    VALUES (?, ?, ?, ?)
                """, (name, phone, email or None, address or None))

            flash("Customer add झाला!", "success")

        return redirect(url_for("customers_page"))

    q = request.args.get("q", "").strip()

    with get_db() as db:
        if q:
            like = f"%{q}%"
            customers = db.execute("""
                SELECT * FROM customers
                WHERE name LIKE ? OR phone LIKE ?
                ORDER BY id DESC
            """, (like, like)).fetchall()
        else:
            customers = db.execute(
                "SELECT * FROM customers ORDER BY id DESC"
            ).fetchall()

    return render_template(
        "customers.html", customers=customers, q=q
    )


@app.route("/orders")
@login_required
def orders_page():
    q = request.args.get("q", "").strip()

    sql = """
        SELECT o.*, c.name AS customer_name,
               c.phone, s.name AS service_name
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        JOIN services s ON s.id = o.service_id
    """
    params = ()

    if q:
        like = f"%{q}%"
        sql += """
            WHERE o.order_code LIKE ?
            OR c.name LIKE ? OR c.phone LIKE ?
        """
        params = (like, like, like)

    sql += " ORDER BY o.id DESC"

    with get_db() as db:
        orders = db.execute(sql, params).fetchall()

    return render_template(
        "orders.html",
        orders=orders,
        q=q,
        statuses=STATUSES,
        payments=["Unpaid", "Paid", "Partial"]
    )


@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def new_order():
    with get_db() as db:
        customers = db.execute(
            "SELECT * FROM customers ORDER BY name"
        ).fetchall()

        services = db.execute(
            "SELECT * FROM services ORDER BY name"
        ).fetchall()

    if request.method == "POST":
        try:
            customer_id = int(request.form["customer_id"])
            service_id = int(request.form["service_id"])
            weight = float(request.form["weight"])
        except (ValueError, KeyError):
            flash("योग्य customer, service आणि weight निवड.", "danger")
            return redirect(url_for("new_order"))

        pickup = request.form.get("pickup_date") or None
        delivery = request.form.get("delivery_date") or None

        if weight <= 0 or weight > 1000:
            flash("Weight 0 पेक्षा जास्त आणि 1000 kg पर्यंत असावे.", "danger")
            return redirect(url_for("new_order"))

        with get_db() as db:
            customer = db.execute(
                "SELECT id FROM customers WHERE id = ?",
                (customer_id,)
            ).fetchone()

            service = db.execute(
                "SELECT * FROM services WHERE id = ?",
                (service_id,)
            ).fetchone()

            if not customer or not service:
                flash("Customer किंवा service सापडली नाही.", "danger")
                return redirect(url_for("new_order"))

            total = round(weight * service["price"], 2)
            code = "LMS" + token_hex(4).upper()

            db.execute("""
                INSERT INTO orders(
                    order_code, customer_id, service_id,
                    weight, total, pickup_date, delivery_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                code, customer_id, service_id,
                weight, total, pickup, delivery
            ))

        flash(f"Order तयार झाली! Bill: ₹{total:.2f}", "success")
        return redirect(url_for("orders_page"))

    return render_template(
        "order_new.html",
        customers=customers,
        services=services
    )


@app.route("/orders/<int:order_id>/update", methods=["POST"])
@login_required
def update_order(order_id):
    status = request.form.get("status", "")
    payment = request.form.get("payment", "")

    if status not in STATUSES or payment not in [
        "Unpaid", "Paid", "Partial"
    ]:
        flash("Invalid status.", "danger")
    else:
        with get_db() as db:
            db.execute("""
                UPDATE orders SET status = ?, payment = ?
                WHERE id = ?
            """, (status, payment, order_id))

        flash("Order update झाली.", "success")

    return redirect(url_for("orders_page"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/orders/<int:order_id>/receipt")
@login_required
def print_receipt(order_id):
    conn = get_db()

    try:
        order = conn.execute("""
            SELECT
                o.*,
                c.name AS customer_name,
                c.phone AS customer_phone,
                c.address AS customer_address,
                s.name AS service_name,
                s.price AS service_price
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            JOIN services s ON s.id = o.service_id
            WHERE o.id = ?
        """, (order_id,)).fetchone()
    finally:
        conn.close()

    if order is None:
        flash("Receipt not found.", "danger")
        return redirect(url_for("orders_page"))

    return render_template("receipt.html", order=order)




if __name__ == "__main__":
    init_db()
    app.run(debug=True)
