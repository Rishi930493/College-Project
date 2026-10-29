from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
import sqlite3
from pathlib import Path
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-deployment"

DB_PATH = Path(__file__).with_name("exam.db")


# ---------------- DATABASE ----------------

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student'
        );

        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            duration INTEGER NOT NULL DEFAULT 10,
            total_marks INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            marks INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exam_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_marks INTEGER NOT NULL,
            submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, exam_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(exam_id) REFERENCES exams(id)
        );

        CREATE TABLE IF NOT EXISTS student_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exam_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_answer TEXT,
            is_correct INTEGER NOT NULL DEFAULT 0,
            marks_awarded INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(exam_id) REFERENCES exams(id),
            FOREIGN KEY(question_id) REFERENCES questions(id),
            UNIQUE(user_id, exam_id, question_id)
        );
        """)

        # Create default admin if not already present
        admin = db.execute(
            "SELECT id FROM users WHERE username = ?",
            ("admin",)
        ).fetchone()

        if not admin:
            db.execute("""
                INSERT INTO users(name, username, password_hash, role)
                VALUES (?, ?, ?, ?)
            """, (
                "Administrator",
                "admin",
                generate_password_hash("admin123"),
                "admin"
            ))

        # Create a sample exam only if no exams exist
        exam_count = db.execute(
            "SELECT COUNT(*) FROM exams"
        ).fetchone()[0]

        if exam_count == 0:
            cur = db.execute("""
                INSERT INTO exams(title, duration, total_marks, is_active)
                VALUES (?, ?, ?, ?)
            """, ("General Knowledge Test", 10, 5, 1))

            exam_id = cur.lastrowid

            sample_questions = [
                (
                    "What is the capital of India?",
                    "Mumbai", "New Delhi", "Chennai", "Kolkata",
                    "B", 1
                ),
                (
                    "Which planet is known as the Red Planet?",
                    "Earth", "Venus", "Mars", "Jupiter",
                    "C", 1
                ),
                (
                    "How many days are there in a leap year?",
                    "365", "366", "364", "360",
                    "B", 1
                ),
                (
                    "Which language is used with Flask?",
                    "Python", "Java", "C++", "PHP",
                    "A", 1
                ),
                (
                    "Which is the largest ocean?",
                    "Indian Ocean", "Arctic Ocean",
                    "Atlantic Ocean", "Pacific Ocean",
                    "D", 1
                )
            ]

            for q in sample_questions:
                db.execute("""
                    INSERT INTO questions(
                        exam_id, question_text,
                        option_a, option_b, option_c, option_d,
                        correct_answer, marks
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (exam_id, *q))


# ---------------- LOGIN DECORATORS ----------------

def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


# ---------------- LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            ).fetchone()

        if user and check_password_hash(
            user["password_hash"], password
        ):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("student_dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


# ---------------- STUDENT REGISTRATION ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not name or not username or len(password) < 6:
            flash(
                "Enter all details. Password must be at least 6 characters.",
                "danger"
            )
            return render_template("register.html")

        try:
            with get_db() as db:
                db.execute("""
                    INSERT INTO users(name, username, password_hash, role)
                    VALUES (?, ?, ?, 'student')
                """, (
                    name,
                    username,
                    generate_password_hash(password)
                ))

            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("This username is already registered.", "danger")

    return render_template("register.html")


# ---------------- STUDENT DASHBOARD ----------------

@app.route("/student")
@login_required
def student_dashboard():
    if session.get("role") != "student":
        return redirect(url_for("admin_dashboard"))

    user_id = session["user_id"]

    with get_db() as db:
        exams = db.execute("""
            SELECT e.*,
                (SELECT COUNT(*) FROM questions q
                 WHERE q.exam_id = e.id) AS question_count,
                (SELECT id FROM results r
                 WHERE r.exam_id = e.id AND r.user_id = ?) AS result_id
            FROM exams e
            WHERE e.is_active = 1
            ORDER BY e.id DESC
        """, (user_id,)).fetchall()

        results = db.execute("""
            SELECT r.*, e.title
            FROM results r
            JOIN exams e ON e.id = r.exam_id
            WHERE r.user_id = ?
            ORDER BY r.id DESC
        """, (user_id,)).fetchall()

    return render_template(
        "student_dashboard.html",
        exams=exams,
        results=results
    )


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    with get_db() as db:
        student_count = db.execute("""
            SELECT COUNT(*) FROM users WHERE role = 'student'
        """).fetchone()[0]

        exam_count = db.execute("""
            SELECT COUNT(*) FROM exams
        """).fetchone()[0]

        exams = db.execute("""
            SELECT e.*,
                (SELECT COUNT(*) FROM questions q
                 WHERE q.exam_id = e.id) AS question_count
            FROM exams e
            ORDER BY e.id DESC
        """).fetchall()

        results = db.execute("""
            SELECT r.*,
                   u.name AS student_name,
                   u.username AS student_username,
                   e.title AS exam_title
            FROM results r
            JOIN users u ON u.id = r.user_id
            JOIN exams e ON e.id = r.exam_id
            ORDER BY r.id DESC
        """).fetchall()

    return render_template(
        "admin_dashboard.html",
        student_count=student_count,
        exam_count=exam_count,
        results=results,
        exams=exams
    )


# ---------------- CREATE EXAM / QUESTION PAPER ----------------

@app.route("/admin/create-exam", methods=["GET", "POST"])
@login_required
@admin_required
def create_exam():
    if request.method == "POST":
        title = request.form.get("title", "").strip()

        try:
            duration = int(request.form.get("duration", "10"))
        except ValueError:
            duration = 0

        question_texts = request.form.getlist("question_text[]")
        option_as = request.form.getlist("option_a[]")
        option_bs = request.form.getlist("option_b[]")
        option_cs = request.form.getlist("option_c[]")
        option_ds = request.form.getlist("option_d[]")
        correct_answers = request.form.getlist("correct_answer[]")
        marks_list = request.form.getlist("marks[]")

        if not title or duration < 1:
            flash("Enter exam name and a valid duration.", "danger")
            return render_template("admin_create_exam.html")

        valid_questions = []

        for i, q_text in enumerate(question_texts):
            q_text = q_text.strip()

            a = option_as[i].strip() if i < len(option_as) else ""
            b = option_bs[i].strip() if i < len(option_bs) else ""
            c = option_cs[i].strip() if i < len(option_cs) else ""
            d = option_ds[i].strip() if i < len(option_ds) else ""

            answer = (
                correct_answers[i].strip().upper()
                if i < len(correct_answers) else ""
            )

            raw_marks = (
                marks_list[i].strip()
                if i < len(marks_list) else "1"
            )

            # Ignore a completely empty question block
            if not any([q_text, a, b, c, d]):
                continue

            try:
                marks = int(raw_marks)
            except ValueError:
                marks = 0

            if (
                not q_text or not all([a, b, c, d])
                or answer not in ["A", "B", "C", "D"]
                or marks < 1
            ):
                flash(
                    f"Please complete question {i + 1} correctly.",
                    "danger"
                )
                return render_template("admin_create_exam.html")

            valid_questions.append(
                (q_text, a, b, c, d, answer, marks)
            )

        if not valid_questions:
            flash("Please add at least one question.", "danger")
            return render_template("admin_create_exam.html")

        total_marks = sum(q[6] for q in valid_questions)

        with get_db() as db:
            cur = db.execute("""
                INSERT INTO exams(title, duration, total_marks, is_active)
                VALUES (?, ?, ?, 1)
            """, (title, duration, total_marks))

            exam_id = cur.lastrowid

            for q in valid_questions:
                db.execute("""
                    INSERT INTO questions(
                        exam_id, question_text,
                        option_a, option_b, option_c, option_d,
                        correct_answer, marks
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (exam_id, *q))

        flash("Question paper created successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_create_exam.html")


# ---------------- ACTIVATE / DEACTIVATE EXAM ----------------

@app.route("/admin/toggle-exam/<int:exam_id>", methods=["POST"])
@login_required
@admin_required
def toggle_exam(exam_id):
    with get_db() as db:
        exam = db.execute(
            "SELECT id, is_active FROM exams WHERE id = ?",
            (exam_id,)
        ).fetchone()

        if not exam:
            flash("Exam not found.", "danger")
        else:
            new_status = 0 if exam["is_active"] else 1
            db.execute(
                "UPDATE exams SET is_active = ? WHERE id = ?",
                (new_status, exam_id)
            )
            flash("Exam status updated.", "success")

    return redirect(url_for("admin_dashboard"))


# ---------------- TAKE EXAM / SAVE ANSWERS ----------------

@app.route("/exam/<int:exam_id>", methods=["GET", "POST"])
@login_required
def take_exam(exam_id):
    if session.get("role") != "student":
        return redirect(url_for("admin_dashboard"))

    user_id = session["user_id"]

    with get_db() as db:
        exam = db.execute("""
            SELECT * FROM exams
            WHERE id = ? AND is_active = 1
        """, (exam_id,)).fetchone()

        if not exam:
            flash("Exam not found or inactive.", "danger")
            return redirect(url_for("student_dashboard"))

        existing = db.execute("""
            SELECT id FROM results
            WHERE user_id = ? AND exam_id = ?
        """, (user_id, exam_id)).fetchone()

        if existing:
            flash("You have already submitted this exam.", "warning")
            return redirect(url_for("student_dashboard"))

        questions = db.execute("""
            SELECT id, question_text,
                   option_a, option_b, option_c, option_d, marks
            FROM questions
            WHERE exam_id = ?
            ORDER BY id
        """, (exam_id,)).fetchall()

        if not questions:
            flash("This exam has no questions yet.", "warning")
            return redirect(url_for("student_dashboard"))

        if request.method == "POST":
            correct_rows = db.execute("""
                SELECT id, correct_answer, marks
                FROM questions
                WHERE exam_id = ?
            """, (exam_id,)).fetchall()

            score = 0
            total_marks = 0

            for question in correct_rows:
                question_id = question["id"]
                correct_answer = question["correct_answer"]
                marks = question["marks"]

                selected_answer = request.form.get(
                    f"question_{question_id}", ""
                ).upper()

                if selected_answer not in ["A", "B", "C", "D"]:
                    selected_answer = ""

                is_correct = int(
                    selected_answer == correct_answer
                )
                marks_awarded = marks if is_correct else 0

                score += marks_awarded
                total_marks += marks

                db.execute("""
                    INSERT INTO student_answers(
                        user_id, exam_id, question_id,
                        selected_answer, is_correct, marks_awarded
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    exam_id,
                    question_id,
                    selected_answer or None,
                    is_correct,
                    marks_awarded
                ))

            db.execute("""
                INSERT INTO results(user_id, exam_id, score, total_marks)
                VALUES (?, ?, ?, ?)
            """, (user_id, exam_id, score, total_marks))

            return redirect(
                url_for("show_result", exam_id=exam_id)
            )

    return render_template(
        "exam.html",
        exam=exam,
        questions=questions
    )


# ---------------- STUDENT RESULT ----------------

@app.route("/result/<int:exam_id>")
@login_required
def show_result(exam_id):
    user_id = session["user_id"]

    with get_db() as db:
        result = db.execute("""
            SELECT r.*, e.title
            FROM results r
            JOIN exams e ON e.id = r.exam_id
            WHERE r.user_id = ? AND r.exam_id = ?
        """, (user_id, exam_id)).fetchone()

    if not result:
        flash("Result not found.", "danger")

        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("student_dashboard"))

    percentage = (
        round(result["score"] * 100 / result["total_marks"], 2)
        if result["total_marks"] else 0
    )

    return render_template(
        "result.html",
        result=result,
        percentage=percentage
    )


# ---------------- ADMIN REVIEW STUDENT ANSWERS ----------------

@app.route("/admin/review/<int:exam_id>/<int:user_id>")
@login_required
@admin_required
def review_answers(exam_id, user_id):
    with get_db() as db:
        student = db.execute("""
            SELECT id, name, username
            FROM users
            WHERE id = ? AND role = 'student'
        """, (user_id,)).fetchone()

        exam = db.execute("""
            SELECT * FROM exams WHERE id = ?
        """, (exam_id,)).fetchone()

        result = db.execute("""
            SELECT * FROM results
            WHERE exam_id = ? AND user_id = ?
        """, (exam_id, user_id)).fetchone()

        answers = db.execute("""
            SELECT
                q.id AS question_id,
                q.question_text,
                q.option_a, q.option_b, q.option_c, q.option_d,
                q.correct_answer, q.marks,
                sa.selected_answer,
                sa.is_correct,
                sa.marks_awarded
            FROM questions q
            LEFT JOIN student_answers sa
              ON sa.question_id = q.id
             AND sa.exam_id = q.exam_id
             AND sa.user_id = ?
            WHERE q.exam_id = ?
            ORDER BY q.id
        """, (user_id, exam_id)).fetchall()

    if not student or not exam or not result:
        flash("Student result not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    return render_template(
        "admin_review.html",
        student=student,
        exam=exam,
        result=result,
        answers=answers
    )


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
