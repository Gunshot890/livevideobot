from flask import Flask, request, render_template_string
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import subprocess
import asyncio

app = Flask(__name__)

# ======================
# CONFIGURATION FROM ENVIRONMENT VARIABLES
# ======================
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

UI = """
<!DOCTYPE html>
<html>
<head>
    <title>TeleLiveVideo</title>
    <style>
        body {
            background:#0f172a;
            color:white;
            text-align:center;
            font-family:Arial, sans-serif;
        }
        .box {
            margin-top:100px;
        }
        input, button, select {
            padding:10px;
            margin:10px;
            border-radius: 5px;
            border: 1px solid #334155;
            background: #1e293b;
            color: white;
        }
        button {
            background-color: #3b82f6;
            color: white;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            background-color: #2563eb;
        }
    </style>
</head>
<body>
<div class="box">
    <h1>📤 Upload Dashboard</h1>

    <form method="post" enctype="multipart/form-data">
        <input type="text" name="username" placeholder="@username or chat_id" required><br>
        <select name="media_type">
            <option value="video_note">Round Video Note (Live Video Circle)</option>
            <option value="auto">Standard Media (Auto-detect)</option>
        </select><br>
        <input type="file" name="file" required><br>
        <button type="submit">Send Media</button>
    </form>

    <p>{{msg}}</p>
</div>
</body>
</html>
"""

def convert_to_square_video(input_path, output_path):
    """
    Uses ffmpeg to crop any video from the center into a 1:1 square 
    and encodes it properly for Telegram Video Notes.
    """
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-vf', "crop='ih:ih:(iw-ih)/2:0' if(gt(iw,ih), crop='iw:iw:0:(ih-iw)/2')",
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', '25',
        '-c:a', 'aac', '-b:a', '128k',
        output_path
    ]
    
    process = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode != 0:
        raise Exception(f"FFmpeg conversion failed: {process.stderr.decode('utf-8')}")

async def send_to_telegram(filepath, target, media_type):
    client = TelegramClient(
        StringSession(SESSION_STRING),
        API_ID,
        API_HASH
    )

    await client.connect()

    if media_type == "video_note":
        processed_path = os.path.join(UPLOAD_FOLDER, "processed_note.mp4")
        try:
            convert_to_square_video(filepath, processed_path)
            await client.send_file(
                target,
                processed_path,
                video_note=True
            )
        finally:
            if os.path.exists(processed_path):
                os.remove(processed_path)
    else:
        await client.send_file(
            target,
            filepath,
            supports_streaming=True
        )

    await client.disconnect()

# Changed back to standard synchronous route definition to prevent crash
@app.route("/", methods=["GET", "POST"])
def home():
    msg = ""

    if request.method == "POST":
        file = request.files.get("file")
        username = request.form.get("username")
        media_type = request.form.get("media_type", "video_note")

        if file and username:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            try:
                # Safely run the async function using an isolated event loop setup
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send_to_telegram(filepath, username, media_type))
                loop.close()
                
                msg = "✅ Sent successfully as requested!"
            except Exception as e:
                msg = f"❌ Error: {str(e)}"
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)

    return render_template_string(UI, msg=msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
