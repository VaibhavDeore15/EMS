from flask import Blueprint, request, render_template, redirect, url_for, session, flash, jsonify, make_response, render_template_string, send_file,get_flashed_messages
import sqlite3, os, base64, cv2
import numpy as np
from datetime import datetime
from xhtml2pdf import pisa
from io import BytesIO

protector_bp = Blueprint('protector_bp', __name__, template_folder='templates')

# Use shared main.db
MAIN_DB = os.path.join(os.path.dirname(__file__), '..', 'main.db')

def get_db_connection():
    conn = sqlite3.connect(MAIN_DB)
    conn.row_factory = sqlite3.Row
    return conn

@protector_bp.route('/')
def student_home():
    return render_template('admin.html')

@protector_bp.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['admin'] = True
            return redirect(url_for('protector_bp.dashboard'))
    return render_template('admin.html')

@protector_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('protector_bp.login'))

@protector_bp.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('protector_bp.login'))

    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM logs ORDER BY exam_title, timestamp DESC").fetchall()
    conn.close()

    grouped = {}
    for log in logs:
        grouped.setdefault(log['exam_title'], []).append(log)

    return render_template('Pdashboard.html', grouped_logs=grouped)

@protector_bp.route('/log-issue', methods=['POST'])
def log_issue():
    data = request.get_json()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO logs (student_id, username, exam_title, issue, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data.get('student_id'),
        data.get('username'),
        data.get('exam_title'),
        data.get('issue'),
        data.get('time')
    ))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"}), 200

@protector_bp.route('/delete-log/<int:log_id>', methods=['POST'])
def delete_log(log_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('protector_bp.dashboard'))

@protector_bp.route('/download-logs/<exam_title>')
def download_exam_logs(exam_title):
    if 'admin' not in session:
        return redirect(url_for('protector_bp.login'))

    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM logs WHERE exam_title = ? ORDER BY timestamp DESC", (exam_title,)).fetchall()
    conn.close()

    rendered = render_template_string("""
    <html>
    <head>
    <style>
        h2, h3 { color: #000; }
        ul { padding-left: 20px; }
        li { margin-bottom: 4px; }
    </style>
    </head>
    <body>
    <h2>Proctor Logs for {{ exam_title }}</h2>
    <ul>
    {% for log in logs %}
      <li>{{ log.timestamp }} — {{ log.username }} — {{ log.issue }}</li>
    {% endfor %}
    </ul>
    </body>
    </html>
    """, logs=logs, exam_title=exam_title)

    pdf = BytesIO()
    pisa.CreatePDF(rendered, dest=pdf)
    pdf.seek(0)

    response = make_response(pdf.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={exam_title}_logs.pdf'
    return response

@protector_bp.route('/analyze-frame', methods=['POST'])
def analyze_frame():
    data = request.get_json()
    img_data = data['image'].split(',')[1]
    img_bytes = base64.b64decode(img_data)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    issue = None
    if len(faces) == 0:
        issue = "No face detected"
    elif len(faces) > 1:
        issue = "Multiple faces detected"

    if issue:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO logs (student_id, username, exam_title, issue, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('student_id'),
            data.get('username'),
            data.get('exam_title'),
            issue,
            datetime.now().strftime("%d-%m-%Y %H:%M")
        ))
        conn.commit()
        conn.close()

    return jsonify({"status": "analyzed", "faces": len(faces)})


@protector_bp.before_request
def clear_irrelevant_flashes():
    get_flashed_messages()

