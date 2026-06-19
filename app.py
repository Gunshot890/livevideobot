from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import subprocess
import asyncio

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "super-secret-key-change-this")
# Use SQLite locally, or PostgreSQL in production on Render
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///users.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ======================
# DATABASE MODELS
# ======================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    # Allows each user to save their own Telegram credentials safely
    telegram_api_id = db.Column(db.Integer, nullable=True)
    telegram_api_hash = db.Column(db.String(100), nullable=True)
    telegram_session = db.Column(db.Text, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ======================
# TEMPLATES (UI)
# ======================
BASE_STYLE = """
<style>
    body { background:#0f172a; color:white; font-family:Arial, sans-serif; text-align:center; margin:0; padding:0; }
    .box { max-width: 450px; margin: 80px auto; padding: 20px; background: #1e293b; border-radius: 8px; border: 1px solid #334155; }
    input, button, select { width: 90%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #475569; background: #0f172a; color: white; }
    button { background-color: #3b82f6; font-weight: bold; cursor: pointer; border: none; }
    button:hover { background-color: #2563eb; }
    a { color: #3b82f6; text-decoration: none; }
    .nav { background: #1e293b; padding: 15px; text-align: right; border-bottom: 1px solid #334155; }
    .nav a { margin-right: 20px; color: #94a3b8; }
    .nav a:hover { color: white; }
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
    <span>Welcome, <b>{{ current_user.username }}</b></span> | 
    <a href="/logout">Logout</a>
</div>
<div class="box">
    <h1>📤 Live Video Dashboard</h1>
    <form method="post" enctype="multipart/form-data">
        <input type="text" name="target" placeholder="@username or Chat ID" required><br>
        <select name="media_type">
            <option value="video_note">Round Video Note (Live Video Circle)</option>
            <option value="auto">Standard Media (Auto-Detect)</option>
        </select><br>
        <input type="file" name="file" required><br>
        <button type="submit">Send Message</button>
    </form>
    {% if msg %}<p>{{ msg }}</p>{% endif %}
</div>
"""

# ======================
# CORE LOGIC & UTILITIES
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

async def send_to_telegram(filepath, target, media_type, api_id, api_hash, session_str):
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()
    if media_type == "video_note":
        processed_path = os.path.join(UPLOAD_FOLDER, f"proc_{os.getpid()}.mp4")
        try:
            convert_to_square_video_low_mem(filepath, processed_path)
            await client.send_file(target, processed_path, video_note=True)
        finally:
            if os.path.exists(processed_path):
                os.remove(processed_path)
    else:
        await client.send_file(target, filepath, supports_streaming=True)
    await client.disconnect()

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
            username=username, 
            password_hash=hashed_pwd,
            telegram_api_id=int(os.getenv("API_ID", 0)),       # Defaulting to global fallback env variables
            telegram_api_hash=os.getenv("API_HASH", ""),
            telegram_session=os.getenv("SESSION_STRING", "")
        )
        db.session.add(new_user)
        db.session.commit()
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
            filepath = os.path.join(UPLOAD_FOLDER, f"{os.getpid()}_{file.filename}")
            file.save(filepath)
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    send_to_telegram(
                        filepath, target, media_type,
                        current_user.telegram_api_id,
                        current_user.telegram_api_hash,
                        current_user.telegram_session
                    )
                )
                loop.close()
                msg = "✅ Media successfully processed and transmitted!"
            except Exception as e:
                msg = f"❌ Error context: {str(e)}"
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)

    return render_template_string(DASHBOARD_UI, current_user=current_user, msg=msg)

# Initialize database contexts safely
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
