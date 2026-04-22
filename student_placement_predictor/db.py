"""
db.py — Shared database + business logic layer.

Used by both:
  - streamlit_app.py  (direct function calls, no HTTP)
  - flask_app.py      (wraps these functions in Flask routes)

Database: PostgreSQL via psycopg2 (Neon serverless).
Each function opens a fresh connection and closes it when done.
This is required for Neon — idle connections are dropped server-side.
"""

import os
import joblib
import random
import numpy as np
import bcrypt
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:mypassword123@127.0.0.1:5432/placement_db_student"
).strip()


def get_db():
    """Return a fresh psycopg2 connection. Always fresh — Neon drops idle connections."""
    # Strip all whitespace (trailing spaces in env vars break sslmode parsing)
    url = DATABASE_URL.strip()
    # Also strip any whitespace around the sslmode value itself
    url = url.replace("sslmode=require ", "sslmode=require")
    if "neon.tech" in url and "sslmode" not in url:
        url += "?sslmode=require"
    return psycopg2.connect(url, connect_timeout=10)


def init_db():
    """Create all tables if they don't exist. Safe to call on every startup."""
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255),
                age INTEGER,
                gender VARCHAR(50),
                stream VARCHAR(100),
                internships INTEGER,
                cgpa DOUBLE PRECISION,
                backlog INTEGER,
                hostel INTEGER DEFAULT 0,
                projects INTEGER DEFAULT 0,
                hackathons INTEGER DEFAULT 0,
                result INTEGER,
                confidence DOUBLE PRECISION,
                timestamp TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS otp_store (
                email TEXT PRIMARY KEY,
                otp TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
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

        # Add missing columns to existing tables
        for col_def in [
            "projects INTEGER DEFAULT 0",
            "hackathons INTEGER DEFAULT 0",
            "hostel INTEGER DEFAULT 0",
        ]:
            try:
                c.execute(f"ALTER TABLE predictions ADD COLUMN IF NOT EXISTS {col_def}")
            except Exception:
                conn.rollback()

        # Rename old column names if they exist (one-time migration)
        old_to_new = [
            ("user_email",       "user_id"),
            ("placement_result", "result"),
            ("readiness_score",  "confidence"),
            ("predicted_at",     "timestamp"),
        ]
        for old_col, new_col in old_to_new:
            try:
                c.execute(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name='predictions' AND column_name=%s",
                    (old_col,)
                )
                if c.fetchone():
                    c.execute(
                        f"ALTER TABLE predictions RENAME COLUMN {old_col} TO {new_col}"
                    )
                    conn.commit()
            except Exception:
                conn.rollback()

        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────
# ML MODEL
# ─────────────────────────────────────────
def _load_or_retrain():
    import subprocess, sys
    for attempt in range(2):
        try:
            data   = joblib.load("model.sav")
            scaler = joblib.load("scaler.sav")
            return data["model"], data["le_gender"], data["le_stream"], scaler
        except Exception as e:
            if attempt == 0:
                print(f"[db.py] Model load failed ({e}). Retraining...")
                result = subprocess.run(
                    [sys.executable, "train_model.py"],
                    capture_output=True, text=True
                )
                print(result.stdout[-800:] if result.stdout else "")
                if result.returncode != 0:
                    print(result.stderr[-400:] if result.stderr else "")
                    raise RuntimeError("Retraining failed") from e
            else:
                raise


model, le_gender, le_stream, scaler = _load_or_retrain()


# ─────────────────────────────────────────
# SKILL SUGGESTIONS
# ─────────────────────────────────────────
def suggest_skills(stream, cgpa, internships, projects, hackathons):
    s = []
    if stream in ["Computer Science", "Information Technology"]:
        if internships < 2:
            s.append("Do more internships — aim for at least 2 before placements")
        if projects < 3:
            s.append(f"Build more projects — you have {projects}, aim for 3+ on GitHub")
        if hackathons < 2:
            s.append("Participate in hackathons — great for teamwork & problem-solving")
        s.append("Master DSA + System Design — core for tech interviews")
        if projects >= 3:
            s.append("Deploy your projects and write case studies for your portfolio")
    elif stream == "Mechanical":
        s.append("Learn CAD tools (SolidWorks / AutoCAD)")
        if projects < 2:
            s.append("Build hands-on mechanical projects for your portfolio")
        s.append("Pursue industry internships in manufacturing or automotive")
    elif stream == "Electrical":
        s.append("Learn PLC & Embedded Systems")
        if projects < 2:
            s.append("Build circuit/embedded projects to showcase skills")
        s.append("Go deep into transformer architecture and power systems")
    elif stream == "Electronics And Communication":
        s.append("Learn VLSI Design and Signal Processing")
        if projects < 2:
            s.append("Build IoT or embedded systems projects")
        if hackathons < 1:
            s.append("Join hardware hackathons to gain practical exposure")
    elif stream == "Civil":
        s.append("Learn AutoCAD and structural analysis tools")
        if projects < 2:
            s.append("Document site/design projects in a portfolio")
        s.append("Pursue site internships for practical exposure")
    if cgpa < 7:
        s.append("Improve academic performance — maintain CGPA above 7.5")
        s.append("Most companies apply a CGPA cutoff of 7.0 or above")
    if hackathons >= 3:
        s.append("Great hackathon record! Highlight wins/rankings on your resume")
    return s


# ─────────────────────────────────────────
# AUTH — REGISTER
# ─────────────────────────────────────────
def api_register(name, email, password):
    name  = name.strip()
    email = email.strip().lower()
    if not name or not email or not password:
        return {"error": "Name, email and password are required."}
    if "@" not in email or "." not in email:
        return {"error": "Enter a valid email address."}
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email = %s", (email,))
        if c.fetchone():
            return {"error": "An account with this email already exists."}
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (%s,%s,%s,%s)",
            (name, email, pw_hash, created)
        )
        conn.commit()
        return {"success": True, "message": f"Account created for {name}."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


# ─────────────────────────────────────────
# AUTH — LOGIN
# ─────────────────────────────────────────
def api_login(email, password):
    email = email.strip().lower()
    if not email or not password:
        return {"error": "Email and password are required."}
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("SELECT id, name, password_hash FROM users WHERE email = %s", (email,))
        row = c.fetchone()
        if not row:
            return {"error": "No account found with this email."}
        user_id, name, pw_hash = row
        if not bcrypt.checkpw(password.encode(), pw_hash.encode()):
            return {"error": "Incorrect password."}
        return {"success": True, "user_id": str(user_id), "name": name, "email": email}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


# ─────────────────────────────────────────
# OTP — SEND
# ─────────────────────────────────────────
def _send_email_otp(to_email, otp):
    import urllib.request, json as _json
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        return False, "RESEND_API_KEY not set"
    try:
        payload = _json.dumps({
            "from":    "Joblib <onboarding@resend.dev>",
            "to":      [to_email],
            "subject": "Joblib — Your Login OTP",
            "text":    f"Your Joblib login OTP is: {otp}\n\nValid for 10 minutes. Do not share."
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15):
            return True, "sent"
    except Exception as e:
        return False, str(e)


def api_send_otp(email):
    email = email.strip().lower()
    if not email or "@" not in email:
        return {"error": "Valid email required."}
    conn = get_db()
    try:
        c = conn.cursor()
        otp = str(random.randint(100000, 999999))
        ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO otp_store (email, otp, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE
                SET otp=EXCLUDED.otp, created_at=EXCLUDED.created_at
        """, (email, otp, ts))
        conn.commit()
        ok, err = _send_email_otp(email, otp)
        if not ok:
            return {"error": f"Email failed: {err}"}
        return {"success": True, "via": "email"}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


# ─────────────────────────────────────────
# OTP — VERIFY
# ─────────────────────────────────────────
def api_verify_otp(email, otp):
    email = email.strip().lower()
    otp   = otp.strip()
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("SELECT otp, created_at FROM otp_store WHERE email=%s", (email,))
        row = c.fetchone()
        if not row:
            return {"error": "No OTP found. Please request a new one."}
        stored_otp, created_at = row
        if otp != stored_otp:
            return {"error": "Incorrect OTP."}
        created = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - created).seconds > 600:
            return {"error": "OTP expired. Please request a new one."}
        c.execute("SELECT id, name FROM users WHERE email=%s", (email,))
        user = c.fetchone()
        if not user:
            return {"error": "No account found with this email. Please register first."}
        c.execute("DELETE FROM otp_store WHERE email=%s", (email,))
        conn.commit()
        return {"success": True, "user_id": str(user[0]), "name": user[1], "email": email}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


# ─────────────────────────────────────────
# PREDICT
# ─────────────────────────────────────────
def api_predict(user_id, age, gender, stream, internships, cgpa, backlog,
                projects=0, hackathons=0, hostel=0):
    """Run ML prediction, save to Neon DB, return result dict."""
    try:
        gender_enc = le_gender.transform([gender])[0]
        stream_enc = le_stream.transform([stream])[0]
    except Exception:
        return {"error": "Invalid category input"}

    academic_score = cgpa * (1 - 0.15 * backlog)
    high_cgpa      = 1 if cgpa >= 8.0 else 0
    at_risk        = 1 if (backlog == 1 and cgpa < 7.0) else 0

    x = np.array([[
        age, gender_enc, stream_enc, internships, cgpa,
        hostel, backlog, academic_score, high_cgpa, at_risk
    ]], dtype=float)

    x_scaled      = scaler.transform(x)
    pred          = model.predict(x_scaled)[0]
    prob          = model.predict_proba(x_scaled)[0][1]

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

    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO predictions
                (user_id, age, gender, stream, internships, cgpa, backlog,
                 hostel, projects, hackathons, result, confidence, timestamp)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (user_id, age, gender, stream, internships, cgpa, int(backlog),
              int(hostel), int(projects), int(hackathons),
              int(pred), float(prob_adjusted), timestamp))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {"error": f"DB write failed: {e}"}
    finally:
        conn.close()

    return {
        "placement":     int(pred),
        "confidence":    float(prob_adjusted),
        "label":         "Placed" if pred == 1 else "Not Placed",
        "profile_score": score,
        "skills":        suggest_skills(stream, cgpa, internships, projects, hackathons),
    }


# ─────────────────────────────────────────
# SUPPORT QUERIES
# ─────────────────────────────────────────
def api_submit_query(user_id, user_name, user_email, subject, message):
    subject = subject.strip()
    message = message.strip()
    if not subject or not message:
        return {"error": "Subject and message are required."}
    conn = get_db()
    try:
        c = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO support_queries
                (user_id, user_name, user_email, subject, message, status, created_at)
            VALUES (%s,%s,%s,%s,%s,'open',%s)
        """, (user_id, user_name, user_email, subject, message, ts))
        conn.commit()
        return {"success": True, "message": "Query submitted successfully."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


def api_get_queries(admin_key):
    expected = os.getenv("ADMIN_SECRET", "joblib_admin_2026")
    if admin_key != expected:
        return {"error": "Unauthorized"}
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM support_queries ORDER BY id DESC")
        rows = c.fetchall()
        cols = ["id", "user_id", "user_name", "user_email", "subject",
                "message", "status", "admin_reply", "created_at", "replied_at"]
        return {"queries": [dict(zip(cols, r)) for r in rows]}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


def api_reply_query(admin_key, query_id, reply):
    expected = os.getenv("ADMIN_SECRET", "joblib_admin_2026")
    if admin_key != expected:
        return {"error": "Unauthorized"}
    reply = reply.strip()
    if not reply:
        return {"error": "Reply cannot be empty."}
    conn = get_db()
    try:
        c = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            UPDATE support_queries
            SET admin_reply=%s, status='resolved', replied_at=%s
            WHERE id=%s
        """, (reply, ts, query_id))
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


# ─────────────────────────────────────────
# INIT on import
# ─────────────────────────────────────────
try:
    init_db()
except Exception as _e:
    print(f"[db.py] WARNING: Could not init DB on import: {_e}")
