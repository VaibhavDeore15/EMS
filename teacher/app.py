from flask import Blueprint, request, redirect, render_template, url_for, flash, session, send_file
import sqlite3, os, io
from datetime import datetime
from fpdf import FPDF

teacher_bp = Blueprint('teacher_bp', __name__, template_folder='templates')

# Shared unified DB
MAIN_DB = os.path.join(os.path.dirname(__file__), '..', 'main.db')

def get_db_connection():
    conn = sqlite3.connect(MAIN_DB)
    conn.row_factory = sqlite3.Row
    return conn

@teacher_bp.route('/')
def student_home():
    return render_template('Tlogin.html')

@teacher_bp.route('/Tregister', methods=['GET', 'POST'])
def Tregister():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        branch = request.form['branch']
        email = request.form['email']
        if not username or not password:
            flash("Please fill out all fields", "danger")
            return redirect(url_for('teacher_bp.Tregister'))

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password, branch, email) VALUES (?, ?, ?, ?)",
                        (username, password, branch, email))
            conn.commit()
            flash("Registration successful, please login", "success")
            return redirect(url_for('teacher_bp.Tlogin'))
        except sqlite3.IntegrityError:
            flash("Username already exists", "danger")
            return redirect(url_for('teacher_bp.Tregister'))
        finally:
            conn.close()
    return render_template('Tregister.html')

@teacher_bp.route('/', methods=['GET', 'POST'])
def Tlogin():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['branch'] = user['branch']
            flash("Logged in successfully", "success")
            return redirect(url_for('teacher_bp.dashboard'))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('teacher_bp.Tlogin'))
    return render_template('Tlogin.html')

@teacher_bp.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('teacher_bp.Tlogin'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM exams WHERE created_by = ?", (session['username'],))
    total_exams = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM results")
    students_appeared = cur.fetchone()[0]
    conn.close()

    return render_template("dashboard.html", total_exams=total_exams, students_appeared=students_appeared)

@teacher_bp.route('/view_queries')
def view_queries():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM querie ORDER BY submitted_at DESC")
    queries = cur.fetchall()
    conn.close()
    return render_template('view_queries.html', queries=queries)

@teacher_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out.')
    return redirect(url_for('teacher_bp.Tlogin'))

@teacher_bp.route('/create_exam', methods=['GET', 'POST'])
def create_exam():
    if 'username' not in session:
        return redirect(url_for('teacher_bp.Tlogin'))

    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        duration = request.form['duration']
        branch = session['branch']
        created_by = session['username']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO exams (title, date, duration, branch, created_by, status) VALUES (?, ?, ?, ?, ?, ?)',
                    (title, date, duration, branch, created_by, 'active'))
        conn.commit()
        conn.close()

        flash("Exam created successfully", "success")
        return redirect(url_for('teacher_bp.dashboard'))

    return render_template('create_exam.html')

@teacher_bp.route('/exam/<int:exam_id>/add-question', methods=['GET', 'POST'])
def add_question(exam_id):
    if request.method == 'POST':
        q_text = request.form['question_text']
        a = request.form['option_a']
        b = request.form['option_b']
        c = request.form['option_c']
        d = request.form['option_d']
        correct = request.form['correct_option']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''INSERT INTO questions 
            (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option)
            VALUES (?, ?, ?, ?, ?, ?, ?)''', (exam_id, q_text, a, b, c, d, correct))
        conn.commit()
        conn.close()

        flash("Question added", "success")
        return redirect(url_for('teacher_bp.manage_exams'))

    return render_template('add_question.html', exam_id=exam_id)

@teacher_bp.route('/exam/<int:exam_id>/set-status/<status>')
def set_exam_status(exam_id, status):
    if status not in ['active', 'ended']:
        flash("Invalid status", "danger")
        return redirect(url_for('teacher_bp.manage_exams'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE exams SET status = ? WHERE id = ?", (status, exam_id))
    conn.commit()
    conn.close()

    flash(f"Exam status set to {status}", "info")
    return redirect(url_for('teacher_bp.manage_exams'))

@teacher_bp.route('/manage-exams')
def manage_exams():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM exams WHERE created_by = ?", (session['username'],))
    exams = cur.fetchall()
    conn.close()
    return render_template('manage_exams.html', exams=exams)

def generate_all_results_pdf():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.username, r.exam_name, r.date, r.score, r.total
        FROM results r
        JOIN users u ON u.id = r.user_id
    """)
    data = cur.fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "All Students Exam Results", 0, 1, "C")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(40, 10, "Student", 1)
    pdf.cell(50, 10, "Exam", 1)
    pdf.cell(30, 10, "Date", 1)
    pdf.cell(20, 10, "Score", 1)
    pdf.cell(20, 10, "Total", 1)
    pdf.cell(30, 10, "Status", 1)
    pdf.ln()

    pdf.set_font("Arial", "", 10)
    for row in data:
        status = "Passed" if row["score"] >= 0.4 * row["total"] else "Failed"
        pdf.cell(40, 10, str(row["username"])[:15], 1)
        pdf.cell(50, 10, str(row["exam_name"])[:24], 1)
        pdf.cell(30, 10, str(row["date"]), 1)
        pdf.cell(20, 10, str(row["score"]), 1)
        pdf.cell(20, 10, str(row["total"]), 1)
        pdf.cell(30, 10, status, 1)
        pdf.ln()

    pdf_output = pdf.output(dest='S').encode('latin1')
    buffer = io.BytesIO(pdf_output)
    buffer.seek(0)
    return buffer

@teacher_bp.route('/download_all_results')
def download_all_results():
    if 'username' not in session:
        flash("Please login first", "danger")
        return redirect(url_for('teacher_bp.Tlogin'))

    pdf_buffer = generate_all_results_pdf()
    return send_file(pdf_buffer, as_attachment=True, download_name="all_results.pdf", mimetype="application/pdf")
