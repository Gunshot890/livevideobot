<input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button>Create Account</button>
        </form>
    </div>
    """)

# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username,password))
        user = c.fetchone()

        if user:
            session["user"] = username
            return redirect("/dashboard")

        return "Wrong login details"

    return render_template_string(BASE, content="""
    <div class="card">
        <h2>Login</h2>
        <form method="post">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button>Login</button>
        </form>
    </div>
    """)

# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    return render_template_string(BASE, content=f"""
    <div class="card">
        <h2>Dashboard</h2>
        <p>Welcome <b>{session['user']}</b></p>
        <p>Status: System Running ✅</p>

        <button onclick="alert('Next step: Telegram integration')">
            Start Bot
        </button>
</div>
    """)

# =========================
# RUN
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
