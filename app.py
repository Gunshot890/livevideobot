from flask import Flask, request, render_template_string, redirect, session
from telethon import TelegramClient
from telethon.sessions import StringSession
import os

app = Flask(__name__)
app.secret_key = "secret123"

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
client.connect()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- UI ----------------
UI = """
<!DOCTYPE html>
<html>
<head>
<title>LiveVideo SaaS</title>
</head>
<body style="background:#0f172a;color:white;text-align:center;font-family:Arial">

<h2>🚀 LiveVideo SaaS Dashboard</h2>

{% if not user %}
<form method="post" action="/login">
<input name="username" placeholder="Username"><br><br>
<button>Login</button>
</form>
{% else %}

<p>Welcome {{user}}</p>

<form method="post" action="/send" enctype="multipart/form-data">
<input name="target" placeholder="@telegramusername" required><br><br>
<input type="file" name="file" required><br><br>
<button>Upload & Send</button>
</form>

<a href="/logout">Logout</a>

{% endif %}

<p>{{msg}}</p>

</body>
</html>
"""

# ---------------- HOME ----------------
@app.route("/", methods=["GET"])
def home():
    return render_template_string(UI, user=session.get("user"))

# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    session["user"] = request.form.get("username")
    return redirect("/")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- SEND FILE ----------------
@app.route("/send", methods=["POST"])
def send():
    if "user" not in session:
        return redirect("/")

    file = request.files["file"]
    target = request.form.get("target")

    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    try:
        client.send_file(target, path)
        msg = "Sent successfully ✅"
    except Exception as e:
        msg = f"Error: {str(e)}"

    return render_template_string(UI, user=session.get("user"), msg=msg)

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
