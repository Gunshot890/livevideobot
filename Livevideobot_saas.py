from flask import Flask, render_template_string, request, redirect, session
import os

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this"

# -------------------------
# UI TEMPLATE (IMPORTANT FIX: content|safe)
# -------------------------
UI = """
<!DOCTYPE html>
<html>
<head>
    <title>LiveVideoBot</title>
    <style>
        body { font-family: Arial; background:#0f172a; color:white; text-align:center; }
        .nav { padding:20px; display:flex; justify-content:space-between; }
        .card { background:#1e293b; padding:20px; margin:20px auto; width:300px; border-radius:10px; }
        input { width:90%; padding:10px; margin:5px; }
        button { padding:10px 15px; margin-top:10px; cursor:pointer; }
        a { color:white; margin:10px; text-decoration:none; }
    </style>
</head>

<body>

<div class="nav">
    <h2>🚀 LiveVideoBot</h2>
    <div>
        <a href="/">Home</a>
        <a href="/login">Login</a>
        <a href="/signup">Signup</a>
        <a href="/dashboard">Dashboard</a>
    </div>
</div>

{{ content|safe }}

</body>
</html>
"""

# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    return render_template_string(UI, content="""
    <h1>Welcome to LiveVideoBot 🚀</h1>
    <p>System is running correctly</p>
    """)

# -------------------------
# LOGIN
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # simple login (you can upgrade later)
        if username and password:
            session["user"] = username
            return redirect("/dashboard")

    return render_template_string(UI, content="""
    <div class="card">
        <h2>Login</h2>

        <form method="post">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
    """)

# -------------------------
# SIGNUP (simple placeholder)
# -------------------------
@app.route("/signup")
def signup():
    return render_template_string(UI, content="""
    <div class="card">
        <h2>Signup</h2>
        <p>Signup system coming soon 🚀</p>
    </div>
    """)

# -------------------------
# DASHBOARD (FIXED)
# -------------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    return render_template_string(UI, content=f"""
    <div class="card">
        <h2>Dashboard</h2>
        <p>Welcome <b>{session['user']}</b> 👋</p>
        <p>Your system is now working ✅</p>

        <form action="/logout">
            <button type="submit">Logout</button>
        </form>
    </div>
    """)

# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# -------------------------
# RUN (IMPORTANT FIX)
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
