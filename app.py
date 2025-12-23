from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "feedback-secret-key"

# --- Database helpers ---

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # change if needed
        password="kalyani",      # change if needed
        database="feedback_mgmt"
    )


# --- Auth helpers ---
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please login to continue", "error")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # store hashed password instead of plain text
        hashed = generate_password_hash(password)

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed),
            )
            conn.commit()
            flash("Signup successful. Please login.", "success")
            return redirect(url_for("login"))
        except mysql.connector.Error:
            conn.rollback()
            flash("Username already exists.", "error")
        finally:
            cur.close()
            conn.close()

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Logged in successfully", "success")
            # redirect to next if provided (preserve where user wanted to go)
            next_url = request.args.get('next') or request.form.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "success")
    return redirect(url_for("login"))


@app.route("/")
def index():
    # simple counts for dashboard
    conn = get_connection()
    cur = conn.cursor()
    counts = {}
    for table in ["students", "courses", "faculty", "questions", "feedback"]:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
        except Exception:
            counts[table] = 0
    cur.close()
    conn.close()
    return render_template("index.html", counts=counts)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/teams')
def teams():
    return render_template('teams.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # simple feedback — not persisted
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        flash('Thanks for reaching out — we will get back to you.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')


# --- Students ---
@app.route("/students")
@login_required
def students_list():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM students ORDER BY id DESC")
    students = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("students_list.html", students=students)


@app.route("/students/add", methods=["GET", "POST"])
@login_required
def students_add():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO students (name, email) VALUES (%s, %s)", (name, email))
        conn.commit()
        cur.close()
        conn.close()
        flash("Student added successfully", "success")
        return redirect(url_for("students_list"))
    return render_template("student_form.html", student=None)


@app.route("/students/edit/<int:student_id>", methods=["GET", "POST"])
@login_required
def students_edit(student_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM students WHERE id=%s", (student_id,))
    student = cur.fetchone()
    if not student:
        flash("Student not found", "error")
        return redirect(url_for("students_list"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        cur.execute("UPDATE students SET name=%s, email=%s WHERE id=%s", (name, email, student_id))
        conn.commit()
        flash("Student updated", "success")
        cur.close()
        conn.close()
        return redirect(url_for("students_list"))

    cur.close()
    conn.close()
    return render_template("student_form.html", student=student)


@app.route("/students/delete/<int:student_id>")
@login_required
def students_delete(student_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id=%s", (student_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Student deleted", "success")
    return redirect(url_for("students_list"))


# --- Courses ---
@app.route("/courses")
@login_required
def courses_list():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM courses ORDER BY id DESC")
    courses = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("courses_list.html", courses=courses)


@app.route("/courses/add", methods=["GET", "POST"])
@login_required
def courses_add():
    if request.method == "POST":
        name = request.form.get("name")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO courses (name) VALUES (%s)", (name,))
        conn.commit()
        cur.close()
        conn.close()
        flash("Course added", "success")
        return redirect(url_for("courses_list"))
    return render_template("course_form.html", course=None)


@app.route("/courses/edit/<int:course_id>", methods=["GET", "POST"])
@login_required
def courses_edit(course_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM courses WHERE id=%s", (course_id,))
    course = cur.fetchone()
    if not course:
        flash("Course not found", "error")
        return redirect(url_for("courses_list"))

    if request.method == "POST":
        name = request.form.get("name")
        cur.execute("UPDATE courses SET name=%s WHERE id=%s", (name, course_id))
        conn.commit()
        flash("Course updated", "success")
        cur.close()
        conn.close()
        return redirect(url_for("courses_list"))

    cur.close()
    conn.close()
    return render_template("course_form.html", course=course)


@app.route("/courses/delete/<int:course_id>")
@login_required
def courses_delete(course_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM courses WHERE id=%s", (course_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Course deleted", "success")
    return redirect(url_for("courses_list"))


# --- Faculty ---
@app.route("/faculty")
@login_required
def faculty_list():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM faculty ORDER BY id DESC")
    faculty = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("faculty_list.html", faculty=faculty)


@app.route("/faculty/add", methods=["GET", "POST"])
@login_required
def faculty_add():
    if request.method == "POST":
        name = request.form.get("name")
        dept = request.form.get("department")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO faculty (name, department) VALUES (%s, %s)", (name, dept))
        conn.commit()
        cur.close()
        conn.close()
        flash("Faculty member added", "success")
        return redirect(url_for("faculty_list"))
    return render_template("faculty_form.html", faculty=None)


@app.route("/faculty/edit/<int:faculty_id>", methods=["GET", "POST"])
@login_required
def faculty_edit(faculty_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM faculty WHERE id=%s", (faculty_id,))
    fac = cur.fetchone()
    if not fac:
        flash("Faculty not found", "error")
        return redirect(url_for("faculty_list"))

    if request.method == "POST":
        name = request.form.get("name")
        dept = request.form.get("department")
        cur.execute("UPDATE faculty SET name=%s, department=%s WHERE id=%s", (name, dept, faculty_id))
        conn.commit()
        flash("Faculty updated", "success")
        cur.close()
        conn.close()
        return redirect(url_for("faculty_list"))

    cur.close()
    conn.close()
    return render_template("faculty_form.html", faculty=fac)


@app.route("/faculty/delete/<int:faculty_id>")
@login_required
def faculty_delete(faculty_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM faculty WHERE id=%s", (faculty_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Faculty deleted", "success")
    return redirect(url_for("faculty_list"))


# --- Feedback Questions ---
@app.route("/questions")
@login_required
def questions_list():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM questions ORDER BY id DESC")
    questions = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("questions_list.html", questions=questions)


@app.route("/questions/add", methods=["GET", "POST"])
@login_required
def questions_add():
    if request.method == "POST":
        text = request.form.get("text")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO questions (text) VALUES (%s)", (text,))
        conn.commit()
        cur.close()
        conn.close()
        flash("Question added", "success")
        return redirect(url_for("questions_list"))
    return render_template("question_form.html", question=None)


@app.route("/questions/edit/<int:question_id>", methods=["GET", "POST"])
@login_required
def questions_edit(question_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM questions WHERE id=%s", (question_id,))
    question = cur.fetchone()
    if not question:
        flash("Question not found", "error")
        return redirect(url_for("questions_list"))

    if request.method == "POST":
        text = request.form.get("text")
        cur.execute("UPDATE questions SET text=%s WHERE id=%s", (text, question_id))
        conn.commit()
        flash("Question updated", "success")
        cur.close()
        conn.close()
        return redirect(url_for("questions_list"))

    cur.close()
    conn.close()
    return render_template("question_form.html", question=question)


@app.route("/questions/delete/<int:question_id>")
@login_required
def questions_delete(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM questions WHERE id=%s", (question_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Question deleted", "success")
    return redirect(url_for("questions_list"))


# --- Feedback (responses) ---
@app.route("/feedback")
@login_required
def feedback_list():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    query = """
        SELECT f.id, s.name AS student_name, c.name AS course_name,
               q.text AS question_text, f.rating, f.remark
        FROM feedback f
        LEFT JOIN students s ON f.student_id = s.id
        LEFT JOIN courses c ON f.course_id = c.id
        LEFT JOIN questions q ON f.question_id = q.id
        ORDER BY f.id DESC
    """
    cur.execute(query)
    feedback_rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("feedback_list.html", feedback_rows=feedback_rows)


@app.route("/feedback/add", methods=["GET", "POST"])
@login_required
def feedback_add():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM students ORDER BY name")
    students = cur.fetchall()
    cur.execute("SELECT id, name FROM courses ORDER BY name")
    courses = cur.fetchall()
    cur.execute("SELECT id, text FROM questions ORDER BY id")
    questions = cur.fetchall()

    if request.method == "POST":
        student_id = request.form.get("student_id")
        course_id = request.form.get("course_id")
        question_id = request.form.get("question_id")
        rating = request.form.get("rating")
        remark = request.form.get("remark")

        cur2 = conn.cursor()
        cur2.execute(
            "INSERT INTO feedback (student_id, course_id, question_id, rating, remark) VALUES (%s, %s, %s, %s, %s)",
            (student_id, course_id, question_id, rating, remark)
        )
        conn.commit()
        cur2.close()
        conn.close()
        flash("Feedback saved", "success")
        return redirect(url_for("feedback_list"))

    conn.close()
    return render_template("feedback_form.html", students=students, courses=courses, questions=questions)


@app.route("/feedback/delete/<int:feedback_id>")
@login_required
def feedback_delete(feedback_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM feedback WHERE id=%s", (feedback_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Feedback deleted", "success")
    return redirect(url_for("feedback_list"))


if __name__ == "__main__":
    app.run(debug=True)
