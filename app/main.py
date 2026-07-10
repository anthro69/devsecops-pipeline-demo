from flask import Flask, request, render_template_string, redirect
import sqlite3
import subprocess
import hashlib
import os

app = Flask(__name__)
SECRET_KEY = "hardcoded_secret_123"
ADMIN_PASSWORD = "admin123"
DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    conn.execute("INSERT OR IGNORE INTO users VALUES (1, 'admin', 'admin123', 'admin')")
    conn.execute("INSERT OR IGNORE INTO users VALUES (2, 'user', 'password', 'user')")
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template_string("<h1>Welcome</h1><a href='/login'>Login</a>")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conn = sqlite3.connect(DB_PATH)
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        result = conn.execute(query).fetchone()
        conn.close()
        if result:
            return redirect(f"/dashboard?user={username}")
        error = "Invalid credentials"
    return render_template_string("""
        <form method='POST'>
            <input name='username'><input name='password' type='password'>
            <button type='submit'>Login</button>
        </form>
        <p>{{ error }}</p>
    """, error=error)

@app.route("/dashboard")
def dashboard():
    user = request.args.get("user", "guest")
    return render_template_string(f"<h1>Welcome {user}!</h1>")

@app.route("/search")
def search():
    query = request.args.get("q", "")
    return render_template_string(f"<p>Results for: {query}</p>")

@app.route("/ping")
def ping():
    host = request.args.get("host", "localhost")
    result = subprocess.check_output(f"ping -c 1 {host}", shell=True)
    return result.decode()

@app.route("/file")
def read_file():
    filename = request.args.get("name", "")
    path = os.path.join("/var/app/files", filename)
    with open(path, "r") as f:
        return f.read()

@app.route("/hash")
def make_hash():
    data = request.args.get("data", "")
    return hashlib.md5(data.encode()).hexdigest()

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0")