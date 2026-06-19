from flask import Flask, request, render_template_string, session, redirect
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import asyncio

app = Flask(__name__)
app.secret_key = "secret"

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

UI = """
<!DOCTYPE html>
<html>
<body style="background:#0f172a;color:white;text-align:center;">
<h2>Upload Dashboard</h2>

<form method="post" action="/send" enctype="multipart/form-data">
<input name="target" placeholder="@username" required><br><br>
<input type="file" name="file" required><br><br>
<button>Send</button>
</form>

<p>{{msg}}</p>

</body>
</html>
"""

def send_file_to_telegram(target, path):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

  async def send_to_telegram(filepath):
    client = TelegramClient("session", API_ID, API_HASH)
    await client.start(phone=PHONE)

    await client.send_file(
        TARGET,
        filepath,
        supports_streaming=True
    )

    await client.disconnect()

    loop.run_until_complete(runner())
    loop.close()

@app.route("/", methods=["GET"])
def home():
    return render_template_string(UI, msg="")

@app.route("/send", methods=["POST"])
def send():
    file = request.files["file"]
    target = request.form.get("target")

    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    try:
        send_file_to_telegram(target, path)
        msg = "Sent successfully ✅"
    except Exception as e:
        msg = str(e)

    return render_template_string(UI, msg=msg)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
