from flask import Flask, request, jsonify
import pickle
import numpy as np
import psycopg2
from datetime import datetime

from flask_cors import CORS 

app = Flask(__name__)
CORS(app)  # <--- ADD THIS HERE (Right after app = Flask)

# ---------------- LOAD MODEL ----------------
# (Leave everything else below exactly as it was)

# ---------------- LOAD MODEL ----------------
data = pickle.load(open("model.sav", "rb"))
model = data["model"]
le_gender = data["le_gender"]
le_stream = data["le_stream"]

scaler = pickle.load(open("scaler.sav", "rb"))

# ---------------- DATABASE ----------------
import psycopg2

# Change 'localhost' to '127.0.0.1'
conn = psycopg2.connect(
    host="127.0.0.1",  
    database="placement_db_student",
    user="postgres",
    password="mypassword123",
    port="5432"
)
c = conn.cursor()

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
    result INTEGER,
    confidence REAL,
    timestamp TEXT
)
""")
conn.commit()

# ---------------- SKILL SUGGESTION ----------------
def suggest_skills(stream, cgpa, internships):
    suggestions = []

    if stream in ["Computer Science", "IT"]:
        if internships < 2:
            suggestions.append("Do more internships")
        suggestions.append("Learn DSA + System Design")
        suggestions.append("Build real-world projects")
        suggestions.append("participate in hackathons that build your confidence, teamwork, and logical thinking")
    

    elif stream == "Mechanical Engineering":
        suggestions.append("Learn CAD tools")
        suggestions.append("Industry internships")

    elif stream == "Electrical Engineering":
        suggestions.append("Learn PLC & Embedded Systems")
        suggestions.append("go deep into the structure and architecture of transformers")


    if cgpa < 7:
        suggestions.append("Improve academic performance")
        suggestions.append("maintain CGPA above 7.5 almost all companies apply the criteria")


        

    return suggestions

# ---------------- API ----------------
@app.route('/predict', methods=['POST'])
def predict():
    try:
        req = request.json

        user_id = req["user_id"]
        age = req["age"]
        gender = req["gender"]
        stream = req["stream"]
        internships = req["internships"]
        cgpa = req["cgpa"]
        backlog = req["backlog"]

        # ---------------- PREPROCESS ----------------
        x = np.array([[age, gender, stream, internships, cgpa, backlog]], dtype=object)

        try:
            x[:, 1] = le_gender.transform(x[:, 1])
            x[:, 2] = le_stream.transform(x[:, 2])
        except Exception:
            return jsonify({"error": "Invalid category input"})

        x = x.astype(float)  # ✅ FIXED
        x_scaled = scaler.transform(x)

        # ---------------- PREDICT ----------------
        pred = model.predict(x_scaled)[0]
        prob = model.predict_proba(x_scaled)[0][1]

        # ---------------- SAVE DB ----------------
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute("""
        INSERT INTO predictions (
            user_id, age, gender, stream, internships, cgpa, backlog,
            result, confidence, timestamp
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            user_id, age, gender, stream,
            internships, cgpa, backlog,
            int(pred), float(prob), timestamp
        ))
        conn.commit()

        return jsonify({
            "placement": int(pred),
            "confidence": float(prob),
            "label": "Placed" if pred == 1 else "Not Placed",
            "skills": suggest_skills(stream, cgpa, internships)
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

