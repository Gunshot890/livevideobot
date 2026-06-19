from flask import Flask, request, render_template_string
from telethon import TelegramClient
from telethon.sessions import StringSession
import os

app = Flask(__name__)

# =====================
# RENDER ENV VARIABLES
# =====================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION")
TARGET = os.environ.get("TARGET")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =====================
# TELEGRAM CLIENT
# =====================
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
client.connect()

# =====================
# UI
# =====================
UI = """
<!DOCTYPE html>
<html>
<head>
<title>LiveVideoBot</title>
<style>
body { background:#0f172a; color:white; text-align:center; font-family:Arial; }
.box { margin-top:100px; }
input, button { padding:10px; margin:10px; }
</style>
</head>
<body>

<div class="box">
<h1>🚀 LiveVideoBot Upload</h1>

<form method="post" enctype="multipart/form-data">
<input type="file" name="file" required><br>
<button type="submit">Upload & Send</button>
</form>

<p>{{msg}}</p>
</div>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    msg = ""

    if request.method == "POST":
        file = request.files["file"]

        if file:
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)

            try:
                client.send_file(TARGET, path)
                msg = "✅ Sent to Telegram successfully"
            except Exception as e:
                msg = f"❌ Error: {str(e)}"

    return render_template_string(UI, msg=msg)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
