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
import warnings
warnings.filterwarnings("ignore", message="X does not have valid feature names")
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("[db.py] VERSION 10 LOADED — balanced model + SMTP OTP")

# ─────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────
# Hardcoded Neon URL — bypasses any env var whitespace issues entirely
_NEON_URL = "postgresql://neondb_owner:npg_IDEbu6zltO3S@ep-icy-cell-am35915d.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"

_RAW_URL = os.getenv("DATABASE_URL", _NEON_URL)
DATABASE_URL = "".join(_RAW_URL.split())  # strip ALL whitespace

# If stripping broke sslmode, fall back to hardcoded clean URL
if "sslmode" not in DATABASE_URL:
    DATABASE_URL = _NEON_URL

print(f"[db.py] DATABASE_URL after strip: '{DATABASE_URL[:60]}'")


def get_db():
    """Return a fresh psycopg2 connection. Always fresh — Neon drops idle connections."""
    url = DATABASE_URL
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
                conn.commit()
            except Exception as col_err:
                print(f"[db.py] Column add warning (safe to ignore): {col_err}")
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
                    print(f"[db.py] Renamed column {old_col} → {new_col}")
            except Exception as rename_err:
                print(f"[db.py] Column rename warning: {rename_err}")
                conn.rollback()

        conn.commit()
        print("[db.py] init_db() completed successfully")
    finally:
        conn.close()


# ─────────────────────────────────────────
# ML MODEL
# ─────────────────────────────────────────
def _load_or_retrain():
    import subprocess, sys
    import os
    
    # Check if model files exist
    model_exists = os.path.exists("model.sav")
    scaler_exists = os.path.exists("scaler.sav")
    print(f"[db.py] model.sav exists: {model_exists}, scaler.sav exists: {scaler_exists}")
    
    for attempt in range(2):
        try:
            print(f"[db.py] Attempt {attempt + 1}: Loading model files...")
            data   = joblib.load("model.sav")
            scaler = joblib.load("scaler.sav")
            print(f"[db.py] ✅ Model loaded successfully!")
            return data["model"], data["le_gender"], data["le_stream"], scaler
        except Exception as e:
            print(f"[db.py] ❌ Model load failed: {type(e).__name__}: {e}")
            if attempt == 0:
                print(f"[db.py] Attempting to retrain model...")
                
                # Check if training file exists
                if not os.path.exists("train_model.py"):
                    print(f"[db.py] ❌ train_model.py not found!")
                    raise RuntimeError("train_model.py not found, cannot retrain") from e
                
                if not os.path.exists("collegePlace.csv"):
                    print(f"[db.py] ❌ collegePlace.csv not found!")
                    raise RuntimeError("collegePlace.csv not found, cannot retrain") from e
                
                result = subprocess.run(
                    [sys.executable, "train_model.py"],
                    capture_output=True, text=True
                )
                
                print("[db.py] Training output (last 800 chars):")
                print(result.stdout[-800:] if result.stdout else "(no stdout)")
                
                if result.returncode != 0:
                    print("[db.py] Training stderr (last 400 chars):")
                    print(result.stderr[-400:] if result.stderr else "(no stderr)")
                    raise RuntimeError(f"Retraining failed with exit code {result.returncode}") from e
                
                print("[db.py] Retraining completed, retrying load...")
            else:
                print(f"[db.py] ❌ Failed to load model after retraining")
                raise RuntimeError(f"Model load failed after retrain: {e}") from e


try:
    model, le_gender, le_stream, scaler = _load_or_retrain()
    print(f"[db.py] Model initialization complete")
except Exception as e:
    print(f"[db.py] FATAL: Could not initialize model: {e}")
    raise


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
# Primary:  Resend API (HTTPS port 443 — works on Railway/Render)
# Fallback: Gmail SMTP (port 587 — works locally, may be blocked on some clouds)
# ─────────────────────────────────────────
def _send_via_resend(to_email, otp):
    """Send OTP via Resend API (HTTPS). Preferred on cloud deployments."""
    import urllib.request
    import json as _json

    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        return False, "RESEND_API_KEY not set"

    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;
                background:#0b0d17;border-radius:12px;border:1px solid #2a2d45;">
        <h2 style="color:#a78bfa;margin-bottom:8px;">&#127891; Joblib</h2>
        <p style="color:#9aa3bf;font-size:14px;">Your one-time login code:</p>
        <div style="font-size:40px;font-weight:800;letter-spacing:10px;
                    color:#eef0f8;text-align:center;padding:24px 0;">{otp}</div>
        <p style="color:#5a6380;font-size:12px;text-align:center;">
            Valid for 10 minutes &middot; Do not share this code
        </p>
    </div>
    """

    payload = _json.dumps({
        "from":    "Joblib <onboarding@resend.dev>",
        "to":      [to_email],
        "subject": "Joblib — Your Login OTP",
        "text":    f"Your Joblib login OTP is: {otp}\n\nValid for 10 minutes. Do not share.",
        "html":    html_body,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "User-Agent":    "joblib-app/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read().decode())
            if data.get("id"):
                return True, "sent"
            return False, f"Unexpected response: {data}"
    except urllib.error.HTTPError as e:
        return False, f"Resend HTTP {e.code}: {e.read().decode()}"
    except Exception as e:
        return False, str(e)


def _send_via_smtp(to_email, otp):
    """Send OTP via Gmail SMTP.
    Uses port 465 (SSL) — Railway blocks 587 (STARTTLS) but allows 465."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()

    if not smtp_user or not smtp_pass:
        return False, "SMTP_USER or SMTP_PASS not set"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Joblib — Your Login OTP"
    msg["From"]    = f"Joblib <{smtp_user}>"
    msg["To"]      = to_email
    
    # Plain text version
    text_body = f"""
Joblib - Student Placement Predictor

Your one-time login code is:

{otp}

This code is valid for 10 minutes.
Do not share this code with anyone.

If you didn't request this code, please ignore this email.
"""
    
    # HTML version with better formatting
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #7c5cfc; margin-bottom: 10px;">🎓 Joblib</h2>
            <p style="color: #666; font-size: 16px; margin-bottom: 20px;">Student Placement Predictor</p>
            
            <p style="color: #333; font-size: 16px; margin-bottom: 20px;">Your one-time login code is:</p>
            
            <div style="background: linear-gradient(135deg, #7c5cfc 0%, #6366f1 100%); border-radius: 10px; padding: 30px; text-align: center; margin: 30px 0;">
                <div style="font-size: 48px; font-weight: bold; letter-spacing: 10px; color: #ffffff; font-family: 'Courier New', monospace;">
                    {otp}
                </div>
            </div>
            
            <p style="color: #999; font-size: 14px; text-align: center; margin-top: 20px;">
                ⏱️ Valid for 10 minutes · 🔒 Do not share this code
            </p>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            
            <p style="color: #999; font-size: 12px; text-align: center;">
                If you didn't request this code, please ignore this email.
            </p>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Try port 465 (SSL) first — works on Railway
    try:
        with smtplib.SMTP_SSL(smtp_host, 465, timeout=15) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True, "sent via SSL/465"
    except Exception as e465:
        pass  # fall through to 587

    # Try port 587 (STARTTLS) as fallback — works locally
    try:
        with smtplib.SMTP(smtp_host, 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True, "sent via STARTTLS/587"
    except Exception as e587:
        return False, f"SSL/465: {e465} | STARTTLS/587: {e587}"


def _send_email_otp(to_email, otp):
    """Try Resend first, fall back to SMTP."""
    ok, err = _send_via_resend(to_email, otp)
    if ok:
        return True, "sent"
    print(f"[db.py] Resend failed ({err}), trying SMTP fallback...")
    ok2, err2 = _send_via_smtp(to_email, otp)
    if ok2:
        return True, "sent"
    return False, f"Resend: {err} | SMTP: {err2}"


def api_send_otp(email):
    email = email.strip().lower()
    if not email or "@" not in email:
        return {"error": "Valid email required."}
    conn = get_db()
    try:
        c = conn.cursor()
        # Verify account exists before sending OTP
        c.execute("SELECT id FROM users WHERE email=%s", (email,))
        if not c.fetchone():
            return {"error": "No account found with this email. Please register first."}
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
            # Log the full error for debugging
            print(f"[db.py] OTP send failed for {email}: {err}")
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
# PREDICT
# ─────────────────────────────────────────
def api_predict(user_id, age, gender, stream, internships, cgpa, backlog,
                projects=0, hackathons=0, hostel=0, num_backlogs=0, project_domain="General"):
    """Run ML prediction, save to Neon DB, return result dict."""
    try:
        gender_enc = le_gender.transform([gender])[0]
        stream_enc = le_stream.transform([stream])[0]
    except Exception:
        return {"error": "Invalid category input"}

    # Use num_backlogs for more nuanced penalty
    backlog_penalty = num_backlogs * 0.15  # Each backlog reduces score by 15%
    academic_score = cgpa * (1 - backlog_penalty)
    high_cgpa      = 1 if cgpa >= 8.0 else 0
    at_risk        = 1 if (num_backlogs >= 2 and cgpa < 7.0) else 0
    intern_cgpa    = internships * cgpa / 10.0   # interaction feature

    x = np.array([[
        age, gender_enc, stream_enc, internships, cgpa,
        hostel, backlog, academic_score, high_cgpa, at_risk, intern_cgpa
    ]], dtype=float)

    x_scaled = scaler.transform(x)
    pred     = model.predict(x_scaled)[0]
    prob     = model.predict_proba(x_scaled)[0][1]

    # ── Business-rule overrides based on num_backlogs ──────────────────
    
    # Rule 1: Multiple backlogs + no internships → very unlikely placed
    if num_backlogs >= 2 and internships == 0:
        prob = min(prob, 0.15)
        pred = 0

    # Rule 2: 1 backlog + no internships → unlikely placed
    elif num_backlogs == 1 and internships == 0:
        prob = min(prob, 0.25)
        pred = 0

    # Rule 3: Multiple backlogs + only 1 internship + low projects → penalise
    elif num_backlogs >= 2 and internships <= 1 and projects < 2:
        prob = min(prob, 0.30)
        pred = 0

    # Rule 4: Zero internships + zero projects + zero hackathons → weak profile
    if internships == 0 and projects == 0 and hackathons == 0:
        prob = min(prob, 0.25)
        pred = 0

    # Rule 5: Zero internships + zero projects (regardless of CGPA)
    elif internships == 0 and projects == 0:
        prob = min(prob, 0.35)
        pred = 0 if prob < 0.5 else pred

    # ── Projects & hackathons boost ──
    boost = 0.0
    if projects   >= 3: boost += 0.03
    if projects   >= 5: boost += 0.02
    if hackathons >= 2: boost += 0.02
    if hackathons >= 4: boost += 0.02
    prob_adjusted = min(prob + boost, 0.99)

    # Re-evaluate prediction after boost
    pred = 1 if prob_adjusted >= 0.50 else 0

    # Profile score with backlog penalty
    score  = min(cgpa / 10.0 * 35, 35)
    score += min(internships / 5.0 * 20, 20)
    score += min(projects / 6.0 * 20, 20)
    score += min(hackathons / 5.0 * 15, 15)
    score += max(10 - (num_backlogs * 3), 0)  # -3 points per backlog
    score  = round(score, 1)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO predictions
                (user_id, age, gender, stream, internships, cgpa, backlog,
                 hostel, projects, hackathons, result, confidence, timestamp,
                 num_backlogs, project_domain, admin_notified)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (user_id, age, gender, stream, internships, cgpa, int(backlog),
              int(hostel), int(projects), int(hackathons),
              int(pred), float(prob_adjusted), timestamp,
              int(num_backlogs), project_domain, False))
        inserted_id = c.fetchone()[0]
        conn.commit()
        print(f"[db.py] Prediction saved — id={inserted_id}, user_id={user_id}, result={int(pred)}, domain={project_domain}")
        
        # Create admin notification
        _create_admin_notification(conn, inserted_id, user_id, stream, cgpa, 
                                   prob_adjusted, pred, project_domain, num_backlogs)
        
        # Fetch and save job recommendations
        if prob_adjusted >= 0.4:  # Only for students with reasonable confidence
            import job_fetcher
            jobs = job_fetcher.get_jobs_for_domain(project_domain, prob_adjusted, limit=5)
            job_fetcher.save_job_recommendations(conn, user_id, jobs)
        
    except Exception as e:
        conn.rollback()
        print(f"[db.py] DB write FAILED: {e}")
        return {"error": f"DB write failed: {e}"}
    finally:
        conn.close()

    return {
        "placement":     int(pred),
        "confidence":    float(prob_adjusted),
        "label":         "Placed" if pred == 1 else "Not Placed",
        "profile_score": score,
        "skills":        suggest_skills(stream, cgpa, internships, projects, hackathons),
        "prediction_id": inserted_id,
    }


def _create_admin_notification(conn, prediction_id, user_id, stream, cgpa, 
                               confidence, result, project_domain, num_backlogs):
    """Create admin notification for student prediction"""
    try:
        c = conn.cursor()
        
        # Get user details
        c.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
        user_row = c.fetchone()
        if not user_row:
            return
        
        user_name, user_email = user_row
        
        # Determine notification type
        if confidence >= 0.7:
            message = f"🎉 High confidence prediction! Student {user_name} ({stream}) has {confidence*100:.1f}% placement probability. Domain: {project_domain}"
            status = "high_confidence"
        elif confidence < 0.5:
            message = f"⚠️ Low confidence alert! Student {user_name} ({stream}) needs guidance. Only {confidence*100:.1f}% placement probability. {num_backlogs} backlogs. Domain: {project_domain}"
            status = "needs_guidance"
        else:
            message = f"📊 Moderate prediction for {user_name} ({stream}). {confidence*100:.1f}% placement probability. Domain: {project_domain}"
            status = "moderate"
        
        c.execute("""
            INSERT INTO admin_notifications
                (prediction_id, user_id, user_name, user_email, stream, cgpa, 
                 confidence, result, project_domain, message, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (prediction_id, user_id, user_name, user_email, stream, cgpa,
              confidence, result, project_domain, message, status))
        
        conn.commit()
        print(f"[db.py] Admin notification created for user {user_id}")
        
    except Exception as e:
        print(f"[db.py] Failed to create admin notification: {e}")
        conn.rollback()


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
# ADMIN GUIDANCE
# ─────────────────────────────────────────
def api_get_admin_notifications(admin_key):
    """Get all admin notifications"""
    expected = os.getenv("ADMIN_SECRET", "joblib_admin_2026")
    if admin_key != expected:
        return {"error": "Unauthorized"}
    
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT id, prediction_id, user_id, user_name, user_email, stream, 
                   cgpa, confidence, result, project_domain, message, status, created_at,
                   admin_reply, replied_at
            FROM admin_notifications
            ORDER BY created_at DESC
            LIMIT 50
        """)
        rows = c.fetchall()
        
        notifications = []
        for row in rows:
            notifications.append({
                "id": row[0],
                "prediction_id": row[1],
                "user_id": row[2],
                "user_name": row[3],
                "user_email": row[4],
                "stream": row[5],
                "cgpa": row[6],
                "confidence": row[7],
                "result": row[8],
                "project_domain": row[9],
                "message": row[10],
                "status": row[11],
                "created_at": str(row[12]),
                "admin_reply": row[13],
                "replied_at": str(row[14]) if row[14] else None
            })
        
        return {"notifications": notifications}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


def api_reply_notification(admin_key, notification_id, reply_message):
    """Reply to a student notification"""
    expected = os.getenv("ADMIN_SECRET", "joblib_admin_2026")
    if admin_key != expected:
        return {"error": "Unauthorized"}
    
    reply_message = reply_message.strip()
    if not reply_message:
        return {"error": "Reply cannot be empty"}
    
    conn = get_db()
    try:
        c = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        c.execute("""
            UPDATE admin_notifications
            SET admin_reply = %s, replied_at = %s
            WHERE id = %s
        """, (reply_message, ts, notification_id))
        
        conn.commit()
        return {"success": True, "message": "Reply sent successfully"}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


def api_send_admin_guidance(admin_key, user_id, user_name, user_email, message, guidance_type):
    """Send guidance message from admin to student"""
    expected = os.getenv("ADMIN_SECRET", "joblib_admin_2026")
    if admin_key != expected:
        return {"error": "Unauthorized"}
    
    if not message.strip():
        return {"error": "Message cannot be empty"}
    
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO admin_guidance
                (user_id, user_name, user_email, admin_message, guidance_type, read_by_student)
            VALUES (%s, %s, %s, %s, %s, FALSE)
        """, (user_id, user_name, user_email, message.strip(), guidance_type))
        conn.commit()
        return {"success": True, "message": "Guidance sent successfully"}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


def api_get_student_guidance(user_id):
    """Get guidance messages for a student"""
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT id, admin_message, guidance_type, created_at, read_by_student
            FROM admin_guidance
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        rows = c.fetchall()
        
        guidance_messages = []
        for row in rows:
            guidance_messages.append({
                "id": row[0],
                "message": row[1],
                "type": row[2],
                "created_at": str(row[3]),
                "read": row[4]
            })
        
        # Mark as read
        c.execute("""
            UPDATE admin_guidance
            SET read_by_student = TRUE
            WHERE user_id = %s AND read_by_student = FALSE
        """, (user_id,))
        conn.commit()
        
        return {"guidance": guidance_messages}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


def api_get_job_recommendations(user_id):
    """Get job recommendations for a student"""
    import job_fetcher
    conn = get_db()
    try:
        jobs = job_fetcher.get_user_job_recommendations(conn, user_id, limit=10)
        return {"jobs": jobs}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()
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
