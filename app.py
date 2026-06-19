from flask import Flask, request, render_template_string
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import asyncio

app = Flask(__name__)

# ======================
# GET FROM RENDER VARIABLES
# ======================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

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
    font-family:Arial;
}
.box {
    margin-top:100px;
}
input, button {
    padding:10px;
    margin:10px;
}
</style>
</head>
<body>
<div class="box">
<h1>📤 Upload Dashboard</h1>

<form method="post" enctype="multipart/form-data">
<input type="text" name="username" placeholder="@username" required><br>
<input type="file" name="file" required><br>
<button type="submit">Send</button>
</form>

<p>{{msg}}</p>
</div>
</body>
</html>
"""

async def send_to_telegram(filepath, target):
    client = TelegramClient(
        StringSession(SESSION_STRING),
        API_ID,
        API_HASH
    )

    await client.connect()

    await client.send_file(
        target,
        filepath,
        supports_streaming=True
    )

    await client.disconnect()

@app.route("/", methods=["GET", "POST"])
def home():
    msg = ""

    if request.method == "POST":
        file = request.files["file"]
        username = request.form["username"]

        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                send_to_telegram(filepath, username)
            )

            msg = "✅ Sent successfully"

    return render_template_string(UI, msg=msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
