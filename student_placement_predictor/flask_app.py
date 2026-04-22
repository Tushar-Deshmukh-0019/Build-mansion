from flask import Flask, request, jsonify
import pickle
import numpy as np
import psycopg2
import os
import bcrypt
from datetime import datetime
from flask_cors import CORS
import smtplib, random
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)

# ---------------- LOAD MODEL ----------------
import joblib as _joblib
data      = _joblib.load("model.sav")
model     = data["model"]
le_gender = data["le_gender"]
le_stream = data["le_stream"]
scaler    = _joblib.load("scaler.sav")

# ---------------- DATABASE ----------------
# Reads DATABASE_URL from environment (Render sets this automatically).
# Falls back to local postgres for development.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:mypassword123@127.0.0.1:5432/placement_db_student"
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

conn = get_db()
c    = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    age INTEGER,
    gender TEXT,
    stream TEXT,
    internships INTEGER,
    cgpa REAL,
    backlog INTEGER,
    projects INTEGER DEFAULT 0,
    hackathons INTEGER DEFAULT 0,
    result INTEGER,
    confidence REAL,
    timestamp TEXT
)
""")
conn.commit()

# Users table for email/password auth
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT
)
""")
conn.commit()

# OTP store table
c.execute("""
CREATE TABLE IF NOT EXISTS otp_store (
    email TEXT PRIMARY KEY,
    otp TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")
conn.commit()

# Support queries table
c.execute("""
CREATE TABLE IF NOT EXISTS support_queries (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    user_name TEXT,
    user_email TEXT,
    subject TEXT,
    message TEXT,
    status TEXT DEFAULT 'open',
    admin_reply TEXT DEFAULT '',
    created_at TEXT,
    replied_at TEXT DEFAULT ''
)
""")
conn.commit()

for col_def in ["projects INTEGER DEFAULT 0", "hackathons INTEGER DEFAULT 0"]:
    try:
        c.execute(f"ALTER TABLE predictions ADD COLUMN IF NOT EXISTS {col_def}")
        conn.commit()
    except Exception:
        conn.rollback()

# ---------------- SKILL SUGGESTION ----------------
def suggest_skills(stream, cgpa, internships, projects, hackathons):
    suggestions = []
    if stream in ["Computer Science", "Information Technology"]:
        if internships < 2:
            suggestions.append("Do more internships — aim for at least 2 before placements")
        if projects < 3:
            suggestions.append(f"Build more projects — you have {projects}, aim for 3+ on GitHub")
        if hackathons < 2:
            suggestions.append("Participate in hackathons — great for teamwork & problem-solving")
        suggestions.append("Master DSA + System Design — core for tech interviews")
        if projects >= 3:
            suggestions.append("Deploy your projects and write case studies for your portfolio")
    elif stream == "Mechanical":
        suggestions.append("Learn CAD tools (SolidWorks / AutoCAD)")
        if projects < 2:
            suggestions.append("Build hands-on mechanical projects for your portfolio")
        suggestions.append("Pursue industry internships in manufacturing or automotive")
    elif stream == "Electrical":
        suggestions.append("Learn PLC & Embedded Systems")
        if projects < 2:
            suggestions.append("Build circuit/embedded projects to showcase skills")
        suggestions.append("Go deep into transformer architecture and power systems")
    elif stream == "Electronics And Communication":
        suggestions.append("Learn VLSI Design and Signal Processing")
        if projects < 2:
            suggestions.append("Build IoT or embedded systems projects")
        if hackathons < 1:
            suggestions.append("Join hardware hackathons to gain practical exposure")
    elif stream == "Civil":
        suggestions.append("Learn AutoCAD and structural analysis tools")
        if projects < 2:
            suggestions.append("Document site/design projects in a portfolio")
        suggestions.append("Pursue site internships for practical exposure")
    if cgpa < 7:
        suggestions.append("Improve academic performance — maintain CGPA above 7.5")
        suggestions.append("Most companies apply a CGPA cutoff of 7.0 or above")
    if hackathons >= 3:
        suggestions.append("Great hackathon record! Highlight wins/rankings on your resume")
    return suggestions

# ---------------- HEALTH CHECK ----------------
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

# ---------------- REGISTER ----------------
@app.route('/register', methods=['POST'])
def register():
    try:
        global conn, c
        try:
            conn.isolation_level
        except Exception:
            conn = get_db(); c = conn.cursor()

        data  = request.json
        name  = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        pwd   = data.get("password", "")

        if not name or not email or not pwd:
            return jsonify({"error": "Name, email and password are required."})
        if len(pwd) < 1:
            return jsonify({"error": "Password is required."})
        if "@" not in email or "." not in email:
            return jsonify({"error": "Enter a valid email address."})

        # Check duplicate
        c.execute("SELECT id FROM users WHERE email = %s", (email,))
        if c.fetchone():
            return jsonify({"error": "An account with this email already exists."})

        pw_hash   = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        created   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (%s,%s,%s,%s)",
            (name, email, pw_hash, created)
        )
        conn.commit()
        return jsonify({"success": True, "message": f"Account created for {name}."})
    except Exception as e:
        return jsonify({"error": str(e)})

# ---------------- LOGIN ----------------
@app.route('/login', methods=['POST'])
def login():
    try:
        global conn, c
        try:
            conn.isolation_level
        except Exception:
            conn = get_db(); c = conn.cursor()

        data  = request.json
        email = data.get("email", "").strip().lower()
        pwd   = data.get("password", "")

        if not email or not pwd:
            return jsonify({"error": "Email and password are required."})

        c.execute("SELECT id, name, password_hash FROM users WHERE email = %s", (email,))
        row = c.fetchone()
        if not row:
            return jsonify({"error": "No account found with this email."})

        user_id, name, pw_hash = row
        if not bcrypt.checkpw(pwd.encode(), pw_hash.encode()):
            return jsonify({"error": "Incorrect password."})

        return jsonify({"success": True, "user_id": str(user_id),
                        "name": name, "email": email})
    except Exception as e:
        return jsonify({"error": str(e)})

# ---------------- PREDICT ----------------
@app.route('/predict', methods=['POST'])
def predict():
    try:
        req         = request.json
        user_id     = req["user_id"]
        age         = req["age"]
        gender      = req["gender"]
        stream      = req["stream"]
        internships = req["internships"]
        cgpa        = req["cgpa"]
        backlog     = req["backlog"]
        projects    = req.get("projects", 0)
        hackathons  = req.get("hackathons", 0)

        # ── ML FEATURES (must match train_model.py FEATURES list) ──
        # CSV columns used: Age, Gender, Stream, Internships, CGPA,
        #                   Hostel, HistoryOfBacklogs
        # Engineered:       academic_score, high_cgpa, at_risk
        # Projects & Hackathons are NOT model inputs — used only for
        # profile score and skill suggestions below.
        try:
            gender_enc = le_gender.transform([gender])[0]
            stream_enc  = le_stream.transform([stream])[0]
        except Exception:
            return jsonify({"error": "Invalid category input"})

        hostel = req.get("hostel", 0)   # optional; default 0

        academic_score = cgpa * (1 - 0.15 * backlog)
        high_cgpa      = 1 if cgpa >= 8.0 else 0
        at_risk        = 1 if (backlog == 1 and cgpa < 7.0) else 0

        x = np.array([[
            age, gender_enc, stream_enc, internships, cgpa,
            hostel, backlog,
            academic_score, high_cgpa, at_risk
        ]], dtype=float)

        x_scaled = scaler.transform(x)

        pred = model.predict(x_scaled)[0]
        prob = model.predict_proba(x_scaled)[0][1]

        boost = 0.0
        if projects   >= 3: boost += 0.03
        if projects   >= 5: boost += 0.02
        if hackathons >= 2: boost += 0.02
        if hackathons >= 4: boost += 0.02
        prob_adjusted = min(prob + boost, 0.99)

        score  = min(cgpa / 10.0 * 35, 35)
        score += min(internships / 5.0 * 20, 20)
        score += min(projects / 6.0 * 20, 20)
        score += min(hackathons / 5.0 * 15, 15)
        score += 10 if backlog == 0 else 0
        score  = round(score, 1)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Reconnect if connection dropped (Render idles connections)
        global conn, c
        try:
            conn.isolation_level
        except Exception:
            conn = get_db()
            c    = conn.cursor()

        c.execute("""
            INSERT INTO predictions
                (user_id, age, gender, stream, internships, cgpa, backlog,
                 projects, hackathons, result, confidence, timestamp)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (user_id, age, gender, stream, internships, cgpa, backlog,
              projects, hackathons, int(pred), float(prob_adjusted), timestamp))
        conn.commit()

        return jsonify({
            "placement":     int(pred),
            "confidence":    float(prob_adjusted),
            "label":         "Placed" if pred == 1 else "Not Placed",
            "profile_score": score,
            "skills":        suggest_skills(stream, cgpa, internships, projects, hackathons)
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# ---------------- EMAIL OTP ----------------
def send_email_otp(to_email, otp):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    if not smtp_user or not smtp_pass:
        return False, "SMTP_NOT_CONFIGURED"
    try:
        msg = MIMEText(
            f"Your Joblib login OTP is: {otp}\n\nValid for 10 minutes. Do not share.",
            "plain"
        )
        msg["Subject"] = "Joblib — Your Login OTP"
        msg["From"]    = smtp_user
        msg["To"]      = to_email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, str(e)

@app.route('/send_otp', methods=['POST'])
def send_otp_route():
    try:
        global conn, c
        try: conn.isolation_level
        except Exception: conn = get_db(); c = conn.cursor()
        email = request.json.get("email", "").strip().lower()
        if not email or "@" not in email:
            return jsonify({"error": "Valid email required."})
        otp = str(random.randint(100000, 999999))
        ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO otp_store (email, otp, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET otp=EXCLUDED.otp, created_at=EXCLUDED.created_at
        """, (email, otp, ts))
        conn.commit()

        # Send email in background thread so API returns immediately
        import threading
        def send_async():
            send_email_otp(email, otp)
        threading.Thread(target=send_async, daemon=True).start()

        return jsonify({"success": True, "via": "email"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/verify_otp', methods=['POST'])
def verify_otp_route():
    try:
        global conn, c
        try: conn.isolation_level
        except Exception: conn = get_db(); c = conn.cursor()
        email = request.json.get("email", "").strip().lower()
        otp   = request.json.get("otp",   "").strip()
        c.execute("SELECT otp, created_at FROM otp_store WHERE email=%s", (email,))
        row = c.fetchone()
        if not row:
            return jsonify({"error": "No OTP found. Please request a new one."})
        stored_otp, created_at = row
        if otp != stored_otp:
            return jsonify({"error": "Incorrect OTP."})
        # Check 10-min expiry
        from datetime import datetime as dt
        created = dt.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        if (dt.now() - created).seconds > 600:
            return jsonify({"error": "OTP expired. Please request a new one."})
        # Get user info
        c.execute("SELECT id, name FROM users WHERE email=%s", (email,))
        user = c.fetchone()
        if not user:
            return jsonify({"error": "No account found with this email. Please register first."})
        c.execute("DELETE FROM otp_store WHERE email=%s", (email,))
        conn.commit()
        return jsonify({"success": True, "user_id": str(user[0]), "name": user[1], "email": email})
    except Exception as e:
        return jsonify({"error": str(e)})

# ---------------- SUPPORT QUERIES ----------------
@app.route('/submit_query', methods=['POST'])
def submit_query():
    try:
        global conn, c
        try: conn.isolation_level
        except Exception: conn = get_db(); c = conn.cursor()
        d        = request.json
        user_id  = d.get("user_id", "")
        name     = d.get("user_name", "")
        email    = d.get("user_email", "")
        subject  = d.get("subject", "").strip()
        message  = d.get("message", "").strip()
        if not subject or not message:
            return jsonify({"error": "Subject and message are required."})
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO support_queries
                (user_id, user_name, user_email, subject, message, status, created_at)
            VALUES (%s,%s,%s,%s,%s,'open',%s)
        """, (user_id, name, email, subject, message, ts))
        conn.commit()
        return jsonify({"success": True, "message": "Query submitted successfully."})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/get_queries', methods=['GET'])
def get_queries():
    try:
        global conn, c
        try: conn.isolation_level
        except Exception: conn = get_db(); c = conn.cursor()
        admin_key = request.headers.get("X-Admin-Key", "")
        if admin_key != os.getenv("ADMIN_SECRET", "joblib_admin_2026"):
            return jsonify({"error": "Unauthorized"}), 401
        c.execute("SELECT * FROM support_queries ORDER BY id DESC")
        rows = c.fetchall()
        cols = ["id","user_id","user_name","user_email","subject",
                "message","status","admin_reply","created_at","replied_at"]
        return jsonify({"queries": [dict(zip(cols, r)) for r in rows]})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/reply_query', methods=['POST'])
def reply_query():
    try:
        global conn, c
        try: conn.isolation_level
        except Exception: conn = get_db(); c = conn.cursor()
        admin_key = request.headers.get("X-Admin-Key", "")
        if admin_key != os.getenv("ADMIN_SECRET", "joblib_admin_2026"):
            return jsonify({"error": "Unauthorized"}), 401
        d        = request.json
        query_id = d.get("query_id")
        reply    = d.get("reply", "").strip()
        if not reply:
            return jsonify({"error": "Reply cannot be empty."})
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            UPDATE support_queries
            SET admin_reply=%s, status='resolved', replied_at=%s
            WHERE id=%s
        """, (reply, ts, query_id))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
