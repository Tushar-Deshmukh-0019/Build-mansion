from flask import Flask, request, jsonify
import pickle
import numpy as np
import psycopg2
import os
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

        x = np.array([[age, gender, stream, internships, cgpa, backlog]], dtype=object)
        try:
            x[:, 1] = le_gender.transform(x[:, 1])
            x[:, 2] = le_stream.transform(x[:, 2])
        except Exception:
            return jsonify({"error": "Invalid category input"})

        x        = x.astype(float)
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
