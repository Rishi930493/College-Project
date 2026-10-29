from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
import csv
import io

app = Flask(__name__)
app.secret_key = "festival_sms_secret_key"

DATABASE = "database.db"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL UNIQUE,
            category TEXT DEFAULT 'General'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            festival TEXT NOT NULL,
            message TEXT NOT NULL,
            sent_to INTEGER DEFAULT 0,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def index():
    conn = get_db()

    total_contacts = conn.execute(
        "SELECT COUNT(*) FROM contacts"
    ).fetchone()[0]

    total_messages = conn.execute(
        "SELECT COUNT(*) FROM messages"
    ).fetchone()[0]

    categories = conn.execute(
        "SELECT COUNT(DISTINCT category) FROM contacts"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        total_contacts=total_contacts,
        total_messages=total_messages,
        categories=categories
    )


@app.route("/import-contacts", methods=["GET", "POST"])
def import_contacts():

    if request.method == "POST":

        file = request.files.get("file")

        if not file or file.filename == "":
            flash("Please select a CSV file.", "error")
            return redirect(url_for("import_contacts"))

        if not file.filename.lower().endswith(".csv"):
            flash("Please upload a CSV file only.", "error")
            return redirect(url_for("import_contacts"))

        try:

            content = file.read().decode("utf-8-sig")

            reader = csv.DictReader(io.StringIO(content))

            conn = get_db()

            added = 0
            skipped = 0

            for row in reader:

                name = row.get("Name", "").strip()
                mobile = row.get("Mobile", "").strip()
                category = row.get("Category", "General").strip()

                if not name or not mobile:
                    skipped += 1
                    continue

                if not mobile.isdigit() or len(mobile) != 10:
                    skipped += 1
                    continue

                try:

                    conn.execute(
                        """
                        INSERT INTO contacts
                        (name, mobile, category)
                        VALUES (?, ?, ?)
                        """,
                        (name, mobile, category or "General")
                    )

                    added += 1

                except sqlite3.IntegrityError:

                    # Duplicate mobile number
                    skipped += 1

            conn.commit()
            conn.close()

            flash(
                f"{added} contacts imported successfully. "
                f"{skipped} contacts skipped.",
                "success"
            )

        except Exception as e:

            flash(
                f"Import failed: {str(e)}",
                "error"
            )

        return redirect(url_for("contacts"))

    return render_template("import_contacts.html")



# ---------------- CONTACTS ----------------

@app.route("/contacts")
def contacts():
    conn = get_db()

    contacts = conn.execute(
        "SELECT * FROM contacts ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template("contacts.html", contacts=contacts)


# ---------------- ADD CONTACT ----------------

@app.route("/add-contact", methods=["GET", "POST"])
def add_contact():

    if request.method == "POST":

        name = request.form["name"].strip()
        mobile = request.form["mobile"].strip()
        category = request.form["category"].strip()

        # Basic mobile validation
        if not mobile.isdigit() or len(mobile) != 10:
            flash("Please enter a valid 10-digit mobile number.", "error")
            return redirect(url_for("add_contact"))

        conn = get_db()

        try:
            conn.execute(
                """
                INSERT INTO contacts (name, mobile, category)
                VALUES (?, ?, ?)
                """,
                (name, mobile, category)
            )

            conn.commit()
            flash("Contact added successfully!", "success")

        except sqlite3.IntegrityError:
            flash("This mobile number already exists.", "error")

        finally:
            conn.close()

        return redirect(url_for("contacts"))

    return render_template("add_contact.html")


# ---------------- DELETE CONTACT ----------------

@app.route("/delete-contact/<int:id>")
def delete_contact(id):

    conn = get_db()

    conn.execute(
        "DELETE FROM contacts WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    flash("Contact deleted successfully.", "success")

    return redirect(url_for("contacts"))


# ---------------- MESSAGES ----------------

@app.route("/messages")
def messages():

    conn = get_db()

    messages = conn.execute(
        "SELECT * FROM messages ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "messages.html",
        messages=messages
    )


# ---------------- SEND MESSAGE ----------------

@app.route("/send-message", methods=["GET", "POST"])
def send_message():

    conn = get_db()

    contacts = conn.execute(
        "SELECT * FROM contacts ORDER BY name"
    ).fetchall()

    conn.close()

    if request.method == "POST":

        festival = request.form["festival"].strip()
        message = request.form["message"].strip()

        selected_contacts = request.form.getlist("contacts")

        if not festival:
            flash("Please select a festival.", "error")
            return redirect(url_for("send_message"))

        if not message:
            flash("Please enter a message.", "error")
            return redirect(url_for("send_message"))

        if not selected_contacts:
            flash("Please select at least one contact.", "error")
            return redirect(url_for("send_message"))

        # ------------------------------------
        # IMPORTANT:
        # Currently this only saves the message.
        # Actual SMS API will be connected later.
        # ------------------------------------

        conn = get_db()

        conn.execute(
            """
            INSERT INTO messages
            (festival, message, sent_to)
            VALUES (?, ?, ?)
            """,
            (
                festival,
                message,
                len(selected_contacts)
            )
        )

        conn.commit()
        conn.close()

        flash(
            f"Message saved for {len(selected_contacts)} contacts. "
            "SMS API will be connected in the next step.",
            "success"
        )

        return redirect(url_for("messages"))

    return render_template(
        "send_message.html",
        contacts=contacts
    )


# ---------------- START APPLICATION ----------------

if __name__ == "__main__":

    init_db()

    print("----------------------------------")
    print(" Festival Bulk SMS Manager")
    print("----------------------------------")
    print("Server running at:")
    print("http://127.0.0.1:5000")
    print("----------------------------------")

    app.run(debug=True)