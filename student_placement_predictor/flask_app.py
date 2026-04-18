from flask import Flask, request, jsonify
import pickle
import numpy as np
import psycopg2
import os
import bcrypt
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ---------------- LOAD MODEL ----------------
data      = pickle.load(open("model.sav", "rb"))
model     = data["model"]
le_gender = data["le_gender"]
le_stream = data["le_stream"]
scaler    = pickle.load(open("scaler.sav", "rb"))

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
        if len(pwd) < 6:
            return jsonify({"error": "Password must be at least 6 characters."})
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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
