from flask import Flask, request, jsonify
import pickle
import numpy as np
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ---------------- LOAD MODEL ----------------
data = pickle.load(open("model.sav", "rb"))
model = data["model"]
le_gender = data["le_gender"]
le_stream = data["le_stream"]

scaler = pickle.load(open("scaler.sav", "rb"))

# ---------------- DATABASE ----------------
conn = sqlite3.connect("placement.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

# ---------------- API ----------------
@app.route('/predict', methods=['POST'])
def predict():

    req = request.json

    user_id = req["user_id"]
    age = req["age"]
    gender = req["gender"]
    stream = req["stream"]
    internships = req["internships"]
    cgpa = req["cgpa"]
    backlog = req["backlog"]

    # ---------------- PREPROCESS ----------------
    x = np.array([[age, gender, stream, internships, cgpa, backlog]])

    x[:, 1] = le_gender.transform(x[:, 1])
    x[:, 2] = le_stream.transform(x[:, 2])

    x = x.astype(int)
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
    ) VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        user_id, age, gender, stream,
        internships, cgpa, backlog,
        int(pred), float(prob), timestamp
    ))

    conn.commit()

    return jsonify({
        "placement": int(pred),
        "confidence": float(prob)
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)