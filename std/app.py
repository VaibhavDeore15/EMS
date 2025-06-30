from flask import Flask, request, redirect, render_template, url_for, flash, session, Blueprint, jsonify
import sqlite3, os
from datetime import datetime

std_bp = Blueprint('std_bp', __name__, template_folder='templates')

# Set unified database path
MAIN_DB = os.path.join(os.path.dirname(__file__), '..', 'main.db')

def get_main_db_connection():
    conn = sqlite3.connect(MAIN_DB)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------
# Registration
# ---------------------------
@std_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        branch = request.form['branch']
        if not username or not password:
            flash("Please fill out all fields", "danger")
            return redirect(url_for('std_bp.register'))

        conn = get_main_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password, branch) VALUES (?, ?, ?)",
                        (username, password, branch))
            conn.commit()
            flash("Registration successful, please login", "success")
            return redirect(url_for('std_bp.login'))
        except sqlite3.IntegrityError:
            flash("Username already exists", "danger")
        finally:
            conn.close()

    return render_template('register.html')

# ---------------------------
# Login
# ---------------------------
@std_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = get_main_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?",
                            (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['branch'] = user['branch']
            flash("Logged in successfully", "success")
            return redirect(url_for('std_bp.home'))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('std_bp.login'))

    return render_template('login.html')

# ---------------------------
# Dashboard
# ---------------------------
@std_bp.route('/home')
def home():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('std_bp.login'))
    return render_template('home.html', username=session['username'])

# ---------------------------
# Logout
# ---------------------------
@std_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out.')
    return redirect(url_for('std_bp.login'))

# ---------------------------
# View Results
# ---------------------------
@std_bp.route('/result')
def result():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('std_bp.login'))

    conn = get_main_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT exam_name, date, score, total FROM results WHERE user_id = ?', (session['user_id'],))
    user_results = cur.fetchall()
    conn.close()

    results_with_status = []
    for row in user_results:
        status = "✅ Passed" if row['score'] >= row['total'] * 0.4 else "❌ Failed"
        results_with_status.append({
            'exam': row['exam_name'],
            'date': row['date'],
            'score': f"{row['score']} / {row['total']}",
            'status': status
        })

    return render_template('result.html', results=results_with_status)

# ---------------------------
# Submit Query
# ---------------------------
@std_bp.route('/query', methods=['GET', 'POST'])
def query():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('std_bp.login'))

    if request.method == 'POST':
        message = request.form['message'].strip()
        if not message:
            flash("Query cannot be empty", "danger")
            return redirect(url_for('std_bp.query'))

        conn = get_main_db_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO querie (user_id, username, message, submitted_at)
            VALUES (?, ?, ?, ?)
        ''', (session['user_id'], session['username'], message, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()

        flash("Query submitted successfully!", "success")
        return redirect(url_for('std_bp.home'))

    return render_template('query.html')

# ---------------------------
# View Active Exams
# ---------------------------
@std_bp.route('/exams')
def exams():
    if 'user_id' not in session:
        return redirect(url_for('std_bp.login'))

    conn = get_main_db_connection()
    exams = conn.execute("SELECT * FROM exams WHERE status = 'active'").fetchall()
    conn.close()

    return render_template('exams.html', exams=exams)

# ---------------------------
# Take Exam
# ---------------------------
@std_bp.route('/exam/<int:exam_id>', methods=['GET', 'POST'])
def start_exam(exam_id):
    if 'user_id' not in session:
        return redirect(url_for('std_bp.login'))

    conn = get_main_db_connection()
    cur = conn.cursor()
    questions = cur.execute("SELECT * FROM questions WHERE exam_id = ?", (exam_id,)).fetchall()
    exam = cur.execute("SELECT title, duration FROM exams WHERE id = ?", (exam_id,)).fetchone()
    conn.close()

    return render_template('exam_page.html', questions=questions,
                           exam_id=exam_id, exam_title=exam['title'], duration=exam['duration'])
    


# ---------------------------
# Submit Exam
# ---------------------------
@std_bp.route('/submit_exam/<int:exam_id>', methods=['POST'])
def submit_exam(exam_id):
    if 'user_id' not in session:
        return redirect(url_for('std_bp.login'))

    conn = get_main_db_connection()
    cur = conn.cursor()
    questions = cur.execute("SELECT * FROM questions WHERE exam_id = ?", (exam_id,)).fetchall()

    score = 0
    for q in questions:
        selected = request.form.get(f"q{q['id']}")
        if selected and selected == q['correct_option']:
            score += 1
    total = len(questions)

    exam_title_row = cur.execute("SELECT title FROM exams WHERE id = ?", (exam_id,)).fetchone()
    exam_title = exam_title_row['title'] if exam_title_row else f"Exam {exam_id}"

    cur.execute('''
        INSERT INTO results (user_id, exam_name, date, score, total)
        VALUES (?, ?, DATE('now'), ?, ?)
    ''', (session['user_id'], exam_title, score, total))
    conn.commit()
    conn.close()

    flash(f"Exam submitted. You scored {score} out of {total}", "success")
    return redirect(url_for('std_bp.result'))

@std_bp.route('/favicon.ico')
def favicon():
    return '', 204  # No Content
