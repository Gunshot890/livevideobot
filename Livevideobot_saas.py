from flask import Flask, request, render_template_string
from telethon import TelegramClient
import os
import asyncio

app = Flask(__name__)

# TELEGRAM SETTINGS
API_ID = 39563890
API_HASH = "9b82271589c270de7b3a3af4ec955cdd"
PHONE = "+2349072506376"

# Telegram target username/user ID
TARGET = "@RashidBinHumaid6"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

UI = """
<!DOCTYPE html>
<html>
<head>
<title>LiveVideoBot</title>
<style>
body { background:#0f172a; color:white; text-align:center; font-family:Arial; }
.box { margin-top:100px; }
</style>
</head>
<body>
<div class="box">
<h1>🚀 LiveVideoBot Upload</h1>
<form method="post" enctype="multipart/form-data">
<input type="file" name="file" required><br><br>
<button type="submit">Upload & Send</button>
</form>
<p>{{msg}}</p>
</div>
</body>
</html>
"""

async def send_to_telegram(filepath):
    client = TelegramClient("session", API_ID, API_HASH)
    await client.start(phone=PHONE)
    await client.send_file(TARGET, filepath)
    await client.disconnect()

@app.route("/", methods=["GET", "POST"])
def home():
    msg = ""
    
    if request.method == "POST":
        file = request.files["file"]

        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            asyncio.run(send_to_telegram(filepath))
            msg = "File sent to Telegram successfully ✅"

    return render_template_string(UI, msg=msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
