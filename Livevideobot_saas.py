import os
import sqlite3
from flask import Flask, request, redirect, session, render_template_string

app = Flask(__name__)
app.secret_key = "livevideobot_secret"

# =====================
# DATABASE SETUP
# =====================
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")
conn.commit()

# =====================
# UI TEMPLATE (FIXED PROPERLY)
# =====================
UI = """
<!DOCTYPE html>
<html>
<head>
<title>LiveVideoBot SaaS</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body {font-family: Arial; background:#0f172a; color:white; margin:0;}
.nav {background:#111827; padding:15px; display:flex; justify-content:space-between;}
.nav a {color:white; margin:0 10px; text-decoration:none;}
.container {max-width:420px; margin:auto; padding:20px;}
.card {background:#1f2937; padding:20px; border-radius:12px; margin-top:20px;}
input {width:100%; padding:12px; margin:8px 0; border-radius:8px; border:none;}
button {width:100%; padding:12px; background:#3b82f6; border:none; color:white; border-radius:8px;}
button:hover {background:#2563eb;}
h2 {text-align:center;}
</style>

</head>
<body>

<div class="nav">
<div>🚀 LiveVideoBot</div>
<div>
<a href="/">Home</a>
<a href="/login">Login</a>
<a href="/signup">Signup</a>
<a href="/dashboard">Dashboard</a>
</div>
</div>

<div class="container">
{{ content }}
</div>

</body>
</html>
"""

# =====================
# HOME
# =====================
@app.route("/")
def home():
    return render_template_string(UI, content="""
    <div class="card">
        <h2>Welcome 🚀</h2>
        <p>LiveVideoBot SaaS System is running.</p>
    </div>
    """)

# =====================
# SIGNUP
# =====================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            return redirect("/login")
        except:
            return "Username already exists"

    return render_template_string(UI, content="""
    <div class="card">
        <h2>Signup</h2>
        <form method="post">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button>Signup</button>
        </form>
    </div>
    """)

# =====================
# LOGIN
# =====================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()

        if user:
            session["user"] = username
            return redirect("/dashboard")

        return "Wrong login details"

    return render_template_string(UI, content="""
    <div class="card">
        <h2>Login</h2>
        <form method="post">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button>Login</button>
        </form>
    </div>
    """)

# =====================
# DASHBOARD
# =====================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    return render_template_string(UI, content=f"""
    <div class="card">
        <h2>Dashboard</h2>
        <p>Welcome <b>{session['user']}</b> 👋</p>
        <p>Status: System Working ✅</p>
    </div>
    """)

# =====================
# RUN
# =====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
