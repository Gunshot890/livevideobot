from flask import Flask, request, render_template_string, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon import types
import os
import subprocess
import asyncio
import threading
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "super-secret-key-change-this")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///users.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- FREE TIER ENFORCEMENT CONFIGURATIONS ---
app.config['MAX_CONTENT_LENGTH'] = 150 * 1024 * 1024  
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'jpg', 'jpeg', 'png', 'gif'}

FREE_VIDEO_LIMIT = 5       
FREE_VOICE_LIMIT = 3       

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SUPPORT_TELEGRAM_USERNAME = os.getenv("SUPPORT_TELEGRAM_USERNAME", "YourSupportUsername")

# ElevenLabs Free Tier Default Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM" # Rachel (Premium Default Voice)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    telegram_session = db.Column(db.Text, nullable=True)
    
    video_count = db.Column(db.Integer, default=0, nullable=False)
    voice_count = db.Column(db.Integer, default=0, nullable=False)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ======================
# FLUID USER INTERFACE STYLE SHEETS
# ======================
BASE_STYLE = """
<style>
    body { background:#0f172a; color:white; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align:center; margin:0; padding:0; }
    .box { max-width: 450px; margin: 50px auto; padding: 25px; background: #1e293b; border-radius: 12px; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
    .container { max-width: 1100px; margin: 40px auto; display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; padding: 0 15px; }
    .card { flex: 1; min-width: 320px; max-width: 460px; padding: 25px; background: #1e293b; border-radius: 12px; border: 1px solid #334155; text-align: left; }
    input, button, select, textarea { width: 100%; padding: 12px; margin: 10px 0; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: white; box-sizing: border-box; font-size: 14px; }
    button { background: linear-gradient(135deg, #3b82f6, #2563eb); font-weight: bold; cursor: pointer; border: none; transition: background 0.2s; }
    button:hover { background: linear-gradient(135deg, #2563eb, #1d4ed8); }
    .btn-support { background: linear-gradient(135deg, #0ea5e9, #0284c7); text-decoration: none; display: block; text-align: center; color: white; font-weight: bold; padding: 12px; margin-top: 15px; border-radius: 6px; font-size: 14px; }
    .btn-upgrade { background: linear-gradient(135deg, #e11d48, #be123c); color:white; text-decoration:none; display:block; text-align:center; padding:12px; border-radius:6px; font-weight:bold; margin-top:10px; font-size:14px; }
    a { color: #3b82f6; text-decoration: none; }
    .nav { background: #1e293b; padding: 15px 30px; text-align: right; border-bottom: 1px solid #334155; font-size: 14px; }
    .nav a { margin-left: 20px; color: #94a3b8; font-weight: 500; }
    h3 { margin-top: 0; color: #f8fafc; }
    p { color: #94a3b8; line-height: 1.5; font-size: 14px; }
    .status-msg { margin-top: 15px; font-weight: 500; color: #34d399; text-align: center; }
    .error-msg { margin-top: 15px; font-weight: 500; color: #f87171; text-align: center; }
    .badge-warn { background: #7c2d12; color: #fdba74; padding: 8px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-bottom: 15px; display: block; text-align: center;}
    .badge-premium { background: #1e3a8a; color: #93c5fd; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-left: 5px; }
    .badge-free { background: #334155; color: #cbd5e1; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-left: 5px; }
    .progress-item { background:#0f172a; padding:12px; border-radius:8px; border:1px solid #334155; margin-bottom:12px; }
</style>
<script>
    function toggleInputFields() {
        var mode = document.getElementById("media_type").value;
        var fileLabel = document.getElementById("file_label");
        var fileInput = document.getElementById("file_input");
        var textLabel = document.getElementById("text_label");
        var textInput = document.getElementById("text_input");
        
        if (mode === "voice_gen") {
            fileLabel.style.display = "none";
            fileInput.style.display = "none";
            fileInput.removeAttribute("required");
            textLabel.style.display = "block";
            textInput.style.display = "block";
            textInput.setAttribute("required", "true");
        } else {
            fileLabel.style.display = "block";
            fileInput.style.display = "block";
            fileInput.setAttribute("required", "true");
            textLabel.style.display = "none";
            textInput.style.display = "none";
            textInput.removeAttribute("required");
        }
    }
</script>
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
    <span>User: <b>{{ current_user.username }}</b>
        {% if current_user.is_premium %}
            <span class="badge-premium">PREMIUM PRO</span>
        {% else %}
            <span class="badge-free">FREE TRIAL</span>
        {% endif %}
    </span>
    {% if current_user.username == 'admin' %}
        <a href="/admin-panel" style="color:#60a5fa; font-weight:bold;">⚙️ Admin Panel</a>
    {% endif %}
    <a href="/logout">Logout</a>
</div>

<div class="container">
    <div class="card">
        {% if not current_user.telegram_session %}
            <h3>🔗 Connect Telegram Session</h3>
            <span class="badge-warn">⚠️ Configuration Warning: Establish direct Telegram linkage to dispatch jobs.</span>
            
            {% if not session_step or session_step == 'phone' %}
                <form method="POST" action="/connect-telegram">
                    <input type="text" name="phone_number" placeholder="Phone Number (+123...)" required>
                    <button type="submit">Send Verification Request</button>
                </form>
            {% elif session_step == 'code' %}
                <form method="POST" action="/verify-code">
                    <input type="text" name="auth_code" placeholder="Enter Login Code" required>
                    <button type="submit">Verify & Link Account</button>
                </form>
            {% endif %}
        {% else %}
            <h3>📤 Command Input Terminal</h3>
            <form method="post" enctype="multipart/form-data" action="/">
                <input type="text" name="target" placeholder="Target @username or Chat ID" required>
                
                <select name="media_type" id="media_type" onchange="toggleInputFields()">
                    <option value="auto_detect">✨ Circle Video / Live Image Engine</option>
                    <option value="view_once">👀 Self-Destruct View-Once Media</option>
                    <option value="spoiler">🤫 Blurred Spoiler Concealment</option>
                    <option value="voice_gen">🎙️ AI Audio Text-To-Speech Note</option>
                </select>
                
                <label id="file_label" style="font-size:12px; color:#94a3b8;">Select Source Media:</label>
                <input type="file" name="file" id="file_input" required>

                <label id="text_label" style="font-size:12px; color:#94a3b8; display:none;">Enter Text for AI Voice Note:</label>
                <textarea name="voice_text" id="text_input" rows="3" placeholder="Type what the AI voice should say..." style="display:none;"></textarea>
                
                <button type="submit" style="margin-top:15px;">Execute Order</button>
            </form>
        {% endif %}
        
        {% if msg %}
            <p class="{% if '❌' in msg %}error-msg{% else %}status-msg{% endif %}">{{ msg }}</p>
        {% endif %}
    </div>

    <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div>
            <h3>📊 Allocation Threshold Monitors</h3>
            <p>Upgrade parameters apply automatically across individual feature engines.</p>
            
            <div class="progress-item">
                <span style="font-size:12px; color:#94a3b8; display:block;">Video Tools Output Queue:</span>
                <b style="font-size:16px;">{{ current_user.video_count }}</b>
                <span style="color:#64748b;">/ {% if current_user.is_premium %}Unlimited Pro{% else %}{{ max_videos }} Allowed Max{% endif %}</span>
                {% if not current_user.is_premium %}
                    <div style="background:#475569; height:5px; border-radius:3px; margin-top:8px; overflow:hidden;">
                        <div style="background:#3b82f6; height:100%; width: {{ video_percent }}%;"></div>
                    </div>
                {% endif %}
            </div>

            <div class="progress-item">
                <span style="font-size:12px; color:#94a3b8; display:block;">AI Voice Note Generations:</span>
                <b style="font-size:16px;">{{ current_user.voice_count }}</b>
                <span style="color:#64748b;">/ {% if current_user.is_premium %}Unlimited Pro{% else %}{{ max_voices }} Generations Max{% endif %}</span>
                {% if not current_user.is_premium %}
                    <div style="background:#475569; height:5px; border-radius:3px; margin-top:8px; overflow:hidden;">
                        <div style="background:#e11d48; height:100%; width: {{ voice_percent }}%;"></div>
                    </div>
                {% endif %}
            </div>

            {% if not current_user.is_premium %}
                <div style="border: 1px dashed #e2e8f0; padding:15px; border-radius:8px; background:#ef444410; margin-top:15px;">
                    <h4 style="margin:0 0 5px 0; color:#f43f5e;">⚡ System Restrictions Found</h4>
                    <p style="font-size:11px; margin:0 0 10px 0;">Purchase standard membership privileges to expand execution clusters cleanly.</p>
                    <a href="https://t.me/{{ support_username }}?text=Hey%20bro%20I%20want%20to%20upgrade%20my%20account" target="_blank" class="btn-upgrade">🔓 Buy Premium Pro Account</a>
                </div>
            {% endif %}
        </div>
        <a href="https://t.me/{{ support_username }}" target="_blank" class="btn-support">💬 Telegram Live Desk</a>
    </div>
</div>
"""

ADMIN_UI = BASE_STYLE + """
<div class="nav"><a href="/">⬅️ Return to Console</a></div>
<div class="box" style="max-width: 650px; text-align: left;">
    <h2>⚙️ Configuration System Admin Overrides</h2>
    <table style="width:100%; border-collapse: collapse; margin-top:15px; font-size:13px;">
        <thead>
            <tr style="border-bottom: 2px solid #475569; text-align: left; color:#94a3b8;">
                <th>Username</th>
                <th>Videos Sent</th>
                <th>Voices Generated</th>
                <th>Access Tier</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for u in all_users %}
                <tr style="border-bottom: 1px solid #334155; height:40px;">
                    <td><b>{{ u.username }}</b></td>
                    <td>{{ u.video_count }}</td>
                    <td>{{ u.voice_count }}</td>
                    <td>{% if u.is_premium %}<b style="color:#4ade80;">PRO</b>{% else %}FREE{% endif %}</td>
                    <td>
                        {% if u.username != 'admin' %}
                            <form method="POST" style="margin:0;">
                                <input type="hidden" name="user_id" value="{{ u.id }}">
                                {% if u.is_premium %}
                                    <button type="submit" name="action" value="demote" style="padding:4px; font-size:11px; background:#ef4444; margin:0;">Revoke</button>
                                {% else %}
                                    <button type="submit" name="action" value="promote" style="padding:4px; font-size:11px; background:#22c55e; margin:0;">Approve</button>
                                {% endif %}
                            </form>
                        {% endif %}
                    </td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
"""

def process_and_downscale_video(input_path, output_path):
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-threads', '1', '-i', input_path,
        '-vf', "scale=w='if(gte(iw,ih),-1,400)':h='if(lte(iw,ih),-1,400)',crop=400:400,format=yuv420p",
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28', '-r', '24',
        '-c:a', 'aac', '-b:a', '64k', '-ac', '1', output_path
    ]
    subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def convert_audio_to_native_voice_note(input_path, output_path):
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-c:a', 'libopus', '-b:a', '32k', '-vbr', 'on', '-ar', '48000', '-ac', '1',
        output_path
    ]
    subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def generate_voice_file(text):
    if not ELEVENLABS_API_KEY:
        raise Exception("ElevenLabs Secret API Key is not configured on Render environment.")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {"text": text, "model_id": "eleven_monolingual_v1", "voice_settings": {"stability": 0.75, "similarity_boost": 0.85}}
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"API Rejection: {response.text}")
        
    temp_mp3 = os.path.join(UPLOAD_FOLDER, f"voice_{os.getpid()}.mp3")
    with open(temp_mp3, "wb") as f:
        f.write(response.content)
        
    final_ogg = os.path.join(UPLOAD_FOLDER, f"audio_{os.getpid()}_{threading.get_ident()}.ogg")
    convert_audio_to_native_voice_note(temp_mp3, final_ogg)
    if os.path.exists(temp_mp3): os.remove(temp_mp3)
    return final_ogg

async def send_to_telegram_async(filepath, target, media_type, session_str, voice_text=None):
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()
    
    if media_type == "voice_gen" and voice_text:
        ogg_voice_path = None
        try:
            ogg_voice_path = generate_voice_file(voice_text)
            await client.send_file(target, ogg_voice_path, voice_note=True)
        finally:
            if ogg_voice_path and os.path.exists(ogg_voice_path): os.remove(ogg_voice_path)
    else:
        ext = filepath.rsplit('.', 1)[1].lower() if filepath else ""
        is_image = ext in {'jpg', 'jpeg', 'png', 'gif'}
        
        if media_type == "auto_detect" and filepath:
            if is_image:
                await client.send_file(target, filepath, ttl=5)
            else:
                processed_path = os.path.join(UPLOAD_FOLDER, f"proc_{os.getpid()}_{threading.get_ident()}.mp4")
                try:
                    process_and_downscale_video(filepath, processed_path)
                    await client.send_file(target, processed_path, video_note=True)
                finally:
                    if os.path.exists(processed_path): os.remove(processed_path)
        elif media_type == "view_once" and filepath:
            await client.send_file(target, filepath, ttl=5)
        elif media_type == "spoiler" and filepath:
            await client.send_file(target, filepath, attributes=[types.DocumentAttributeHasStickers()] if not is_image else [], spoiler=True)

    await client.disconnect()

def run_telegram_thread(filepath, target, media_type, session_str, voice_text=None):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_to_telegram_async(filepath, target, media_type, session_str, voice_text))
        loop.close()
    except Exception as e:
        print(f"Runtime processing error: {e}")
    finally:
        if filepath and os.path.exists(filepath): os.remove(filepath)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username").strip().lower()
        password = request.form.get("password")
        if username == 'admin' or User.query.filter_by(username=username).first():
            return "❌ Account Generation Rejection."
        hashed_pwd = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, password_hash=hashed_pwd)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template_string(SIGNUP_UI)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip().lower()
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        return "Authentication Fault."
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

    v_percent = min(100, int((current_user.video_count / FREE_VIDEO_LIMIT) * 100))
    a_percent = min(100, int((current_user.voice_count / FREE_VOICE_LIMIT) * 100))

    if request.method == "POST":
        target = request.form.get("target")
        media_type = request.form.get("media_type")
        voice_text = request.form.get("voice_text")
        file = request.files.get("file")
        
        user = User.query.get(current_user.id)

        if not current_user.telegram_session:
            msg = "❌ Error: Please authorize your account identity first."
        
        elif media_type == "voice_gen":
            if not current_user.is_premium and user.voice_count >= FREE_VOICE_LIMIT:
                msg = "❌ Limit Reached: Buy Premium Pro to unlock unlimited audio note creations!"
            else:
                user.voice_count += 1
                db.session.commit()
                threading.Thread(target=run_telegram_thread, args=(None, target, media_type, current_user.telegram_session, voice_text)).start()
                msg = "✅ AI Voice note generation triggered!"
                
        elif file and target:
            if not current_user.is_premium and user.video_count >= FREE_VIDEO_LIMIT:
                msg = "❌ Limit Reached: Buy Premium Pro to unlock unlimited video processing!"
            elif not allowed_file(file.filename):
                msg = "❌ Error: File extension invalid."
            else:
                user.video_count += 1
                db.session.commit()
                
                filepath = os.path.join(UPLOAD_FOLDER, f"job_{os.getpid()}_{file.filename}")
                file.save(filepath)
                threading.Thread(target=run_telegram_thread, args=(filepath, target, media_type, current_user.telegram_session, None)).start()
                msg = "✅ Video job handed off successfully!"

    return render_template_string(DASHBOARD_UI, current_user=current_user, msg=msg, session_step=step, support_username=SUPPORT_TELEGRAM_USERNAME, max_videos=FREE_VIDEO_LIMIT, max_voices=FREE_VOICE_LIMIT, video_percent=v_percent, voice_percent=a_percent)

@app.route("/admin-panel", methods=["GET", "POST"])
@login_required
def admin_panel():
    if current_user.username != 'admin': return "🔒 Forbidden.", 403
    if request.method == "POST":
        target_user = User.query.get(int(request.form.get("user_id")))
        action = request.form.get("action")
        if target_user and target_user.username != 'admin':
            target_user.is_premium = (action == "promote")
            db.session.commit()
    return render_template_string(ADMIN_UI, all_users=User.query.all())

async def request_code_async(phone):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    send_code_obj = await client.send_code_request(phone)
    return send_code_obj.phone_code_hash, client.session.save()

@app.route("/connect-telegram", methods=["POST"])
@login_required
def connect_telegram():
    phone = request.form.get("phone_number")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        phone_code_hash, partial_session = loop.run_until_complete(request_code_async(phone))
        loop.close()
        session.update({'auth_phone': phone, 'auth_hash': phone_code_hash, 'partial_session': partial_session, 'session_step': 'code', 'dash_msg': "✅ Verification digits generated!"})
    except Exception as e: session['dash_msg'] = f"❌ Error: {str(e)}"
    return redirect(url_for('dashboard'))

async def verify_code_async(partial_session, phone, phone_hash, code):
    client = TelegramClient(StringSession(partial_session), API_ID, API_HASH)
    await client.connect()
    await client.sign_in(phone=phone, code=code, phone_code_hash=phone_hash)
    final_session = client.session.save()
    await client.disconnect()
    return final_session

@app.route("/verify-code", methods=["POST"])
@login_required
def verify_code():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        final_session = loop.run_until_complete(verify_code_async(session.get('partial_session'), session.get('auth_phone'), session.get('auth_hash'), request.form.get("auth_code")))
        loop.close()
        
        user = User.query.get(current_user.id)
        user.telegram_session = final_session
        db.session.commit()
        session.pop('session_step', None)
        session['dash_msg'] = "🎉 Telegram identity linked successfully!"
    except Exception as e:
        session.update({'dash_msg': f"❌ Access Denied: {str(e)}", 'session_step': 'phone'})
    return redirect(url_for('dashboard'))

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password_hash=generate_password_hash('AdminPass2026!', method='scrypt'), is_premium=True))
        db.session.commit()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
