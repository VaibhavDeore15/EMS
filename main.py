from flask import Flask, render_template
from std.app import std_bp
from teacher.app import teacher_bp
from protector.app import protector_bp
import sqlite3

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'super_secret'


conn = sqlite3.connect("main.db")
cur = conn.cursor()

# Users table (for both students and teachers)
cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    branch TEXT NOT NULL,
    email TEXT
)
''')

# Exams table
cur.execute('''
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    duration INTEGER,
    branch TEXT,
    created_by TEXT,
    status TEXT NOT NULL
)
''')

# Questions table
cur.execute('''
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER,
    question_text TEXT,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    correct_option TEXT,
    FOREIGN KEY (exam_id) REFERENCES exams (id)
)
''')

# Student answers
cur.execute('''
CREATE TABLE IF NOT EXISTS student_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    exam_id INTEGER,
    question_id INTEGER,
    selected_option TEXT
)
''')

# Results
cur.execute('''
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    exam_name TEXT,
    date TEXT,
    score INTEGER,
    total INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')

# Proctor logs
cur.execute('''
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    username TEXT,
    exam_title TEXT,
    issue TEXT,
    timestamp TEXT
)
''')

# Student queries
cur.execute('''
CREATE TABLE IF NOT EXISTS querie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    submitted_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')

conn.commit()
conn.close()


# Register Blueprints
app.register_blueprint(std_bp, url_prefix='/std')
app.register_blueprint(teacher_bp, url_prefix='/teacher')
app.register_blueprint(protector_bp, url_prefix='/protector')

@app.route('/')
def index():
    return render_template('main_home.html')

if __name__ == "__main__":
    app.run(debug=True)
