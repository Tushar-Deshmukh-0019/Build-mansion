import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import base64
from streamlit_option_menu import option_menu
from dotenv import load_dotenv
from openai import OpenAI as _OpenAI

# ── Fix DATABASE_URL BEFORE importing db ──────────────────────────────
# Railway sometimes injects trailing whitespace into env vars which
# breaks psycopg2's sslmode parser ("require " is invalid).
# Strip ALL whitespace from the URL right here so db.py always gets a clean value.
load_dotenv()
_raw = os.environ.get("DATABASE_URL", "")
if _raw:
    os.environ["DATABASE_URL"] = "".join(_raw.split())

import db  # shared DB + business logic (no Flask HTTP calls needed)

# ==========================================
# 1. PAGE CONFIG
# ==========================================
st.set_page_config(page_title="Student Placement Predictor", layout="wide", page_icon="🎓")

# ==========================================
# 3. STYLING
# ==========================================
def set_design():
    try:
        with open("placement_predictor.jpg", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        bg = f'url("data:image/jpg;base64,{b64}")'
    except:
        bg = "none"
    st.markdown(f"""
        <style>
        /* ── Google Fonts ── */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        /* ── CSS Variables ── */
        :root {{
            --bg-base:      #0b0d17;
            --bg-card:      #12152a;
            --bg-input:     #1c2035;
            --bg-hover:     #1e2238;
            --accent:       #7c5cfc;
            --accent-light: #a78bfa;
            --accent-glow:  rgba(124,92,252,0.22);
            --text-primary: #eef0f8;
            --text-secondary:#9aa3bf;
            --text-muted:   #5a6380;
            --border:       rgba(124,92,252,0.22);
            --border-focus: rgba(124,92,252,0.65);
            --success:      #34d399;
            --error:        #f87171;
            --warning:      #fbbf24;
            --info:         #60a5fa;
            --radius-sm:    8px;
            --radius-md:    12px;
            --radius-lg:    16px;
        }}

        /* ── Base ── */
        html, body, [class*="css"] {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            font-size: 15px;
            letter-spacing: 0.01em;
        }}
        .stApp {{
            background: linear-gradient(160deg, #0b0d17 0%, #0e1022 60%, #0b0f1a 100%) !important;
        }}
        .stApp::before {{
            content:""; background-image:{bg}; background-size:cover;
            background-position:center; background-attachment:fixed;
            opacity:0.03; position:absolute; top:0; left:0; width:100%; height:100%; z-index:-1;
        }}

        /* ── Global text ── */
        html, body, [class*="css"] {{ color: var(--text-primary) !important; }}
        p, span, div, label {{ color: var(--text-primary); }}
        .stMarkdown p {{ color: var(--text-primary) !important; line-height: 1.7; }}

        /* ── Input labels ── */
        .stTextInput label, .stSelectbox label, .stSlider label,
        .stNumberInput label, .stToggle label, .stTextArea label,
        .stMultiSelect label {{
            color: var(--text-secondary) !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
            margin-bottom: 4px !important;
        }}

        /* ── Text & Textarea inputs ── */
        .stTextInput input,
        .stTextInput > div > div > input,
        div[data-testid="stTextInput"] input,
        .stTextArea textarea {{
            background: var(--bg-input) !important;
            color: var(--text-primary) !important;
            border: 1.5px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            font-size: 15px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            caret-color: var(--accent-light) !important;
            transition: border-color 0.2s, box-shadow 0.2s !important;
            padding: 10px 14px !important;
        }}
        .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
            color: var(--text-muted) !important;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: var(--border-focus) !important;
            box-shadow: 0 0 0 3px var(--accent-glow) !important;
            background: var(--bg-hover) !important;
            outline: none !important;
        }}

        /* ── Number inputs ── */
        .stNumberInput input,
        .stNumberInput > div > div > input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stNumberInputContainer"] input {{
            background: var(--bg-input) !important;
            color: var(--text-primary) !important;
            border: 1.5px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            font-size: 15px !important;
            font-family: 'JetBrains Mono', monospace !important;
            caret-color: var(--accent-light) !important;
            padding: 10px 14px !important;
        }}
        div[data-testid="stNumberInputContainer"] {{
            background: var(--bg-input) !important;
            border-radius: var(--radius-md) !important;
        }}
        div[data-testid="stNumberInputContainer"]:focus-within {{
            box-shadow: 0 0 0 3px var(--accent-glow) !important;
        }}

        /* ── Selectbox ── */
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {{
            background: var(--bg-input) !important;
            color: var(--text-primary) !important;
            border: 1.5px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            font-size: 15px !important;
        }}
        .stSelectbox div[data-baseweb="select"] span,
        .stMultiSelect div[data-baseweb="select"] span {{
            color: var(--text-primary) !important;
        }}
        /* Dropdown menu */
        [data-baseweb="popover"] ul,
        [data-baseweb="menu"] {{
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
        }}
        [data-baseweb="menu"] li {{
            color: var(--text-primary) !important;
            font-size: 14px !important;
        }}
        [data-baseweb="menu"] li:hover {{
            background: var(--bg-hover) !important;
        }}

        /* ── Buttons ── */
        .stButton > button {{
            background: linear-gradient(135deg, #7c5cfc 0%, #6366f1 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: var(--radius-md) !important;
            font-weight: 700 !important;
            font-size: 14px !important;
            letter-spacing: 0.04em !important;
            padding: 11px 22px !important;
            width: 100% !important;
            transition: all 0.22s ease !important;
            box-shadow: 0 4px 18px rgba(124,92,252,0.32) !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }}
        .stButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 24px rgba(124,92,252,0.48) !important;
            background: linear-gradient(135deg, #9171fd 0%, #7c5cfc 100%) !important;
        }}
        .stButton > button:active {{ transform: translateY(0px) !important; }}

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] {{
            background: transparent !important;
            border-bottom: 1px solid var(--border) !important;
            gap: 4px !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            color: var(--text-muted) !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
            padding: 10px 18px !important;
            border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
            transition: color 0.2s !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            color: var(--text-secondary) !important;
            background: rgba(124,92,252,0.06) !important;
        }}
        .stTabs [aria-selected="true"] {{
            color: var(--accent-light) !important;
            border-bottom: 2px solid var(--accent) !important;
            background: rgba(124,92,252,0.08) !important;
        }}

        /* ── Metrics ── */
        [data-testid="metric-container"] {{
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-lg) !important;
            padding: 18px !important;
        }}
        [data-testid="metric-container"] label {{
            color: var(--text-secondary) !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
        }}
        [data-testid="metric-container"] [data-testid="stMetricValue"] {{
            color: var(--text-primary) !important;
            font-size: 28px !important;
            font-weight: 800 !important;
            font-family: 'JetBrains Mono', monospace !important;
        }}
        [data-testid="metric-container"] [data-testid="stMetricDelta"] {{
            font-size: 13px !important;
            font-weight: 600 !important;
        }}

        /* ── Alerts ── */
        .stAlert {{ border-radius: var(--radius-md) !important; font-size: 14px !important; font-weight: 500 !important; }}
        .stSuccess {{ background: rgba(52,211,153,0.10) !important; border: 1px solid rgba(52,211,153,0.30) !important; color: #6ee7b7 !important; }}
        .stError   {{ background: rgba(248,113,113,0.10) !important; border: 1px solid rgba(248,113,113,0.30) !important; color: #fca5a5 !important; }}
        .stWarning {{ background: rgba(251,191,36,0.10) !important;  border: 1px solid rgba(251,191,36,0.30) !important;  color: #fde68a !important; }}
        .stInfo    {{ background: rgba(96,165,250,0.10) !important;  border: 1px solid rgba(96,165,250,0.30) !important;  color: #bfdbfe !important; }}

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {{
            background: rgba(9,11,22,0.98) !important;
            border-right: 1px solid var(--border) !important;
        }}
        [data-testid="stSidebar"] * {{ color: var(--text-primary) !important; }}

        /* ── Dataframe ── */
        .stDataFrame {{ border-radius: var(--radius-md); overflow: hidden; border: 1px solid var(--border) !important; }}
        .stDataFrame th {{ background: var(--bg-card) !important; color: var(--text-secondary) !important; font-size: 12px !important; font-weight: 700 !important; letter-spacing: 0.06em !important; text-transform: uppercase !important; }}
        .stDataFrame td {{ color: var(--text-primary) !important; font-size: 14px !important; }}

        /* ── Custom components ── */
        .skill-item {{
            background: rgba(124,92,252,0.08);
            border-left: 3px solid var(--accent);
            border-radius: var(--radius-md);
            padding: 12px 16px;
            margin: 8px 0;
            font-size: 14px;
            color: var(--text-primary);
            line-height: 1.7;
            font-weight: 500;
        }}
        .section-label {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 2.5px;
            color: var(--accent-light);
            font-weight: 800;
            margin-bottom: 12px;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}

        /* ── Headings ── */
        h1 {{
            color: var(--text-primary) !important;
            font-size: 30px !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            line-height: 1.2 !important;
        }}
        h2 {{
            color: var(--text-primary) !important;
            font-size: 22px !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }}
        h3 {{
            color: var(--text-primary) !important;
            font-size: 18px !important;
            font-weight: 600 !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }}

        /* ── Slider ── */
        .stSlider [data-testid="stTickBar"] {{ color: var(--text-muted) !important; }}
        .stSlider [data-testid="stTickBar"] > div {{ color: var(--text-secondary) !important; font-size: 12px !important; }}

        /* ── Toggle ── */
        .stToggle label span {{ color: var(--text-primary) !important; font-size: 14px !important; font-weight: 500 !important; }}

        /* ── Expander ── */
        .streamlit-expanderHeader {{
            color: var(--text-primary) !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            background: var(--bg-card) !important;
            border-radius: var(--radius-md) !important;
            border: 1px solid var(--border) !important;
        }}
        .streamlit-expanderContent {{
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-top: none !important;
        }}

        /* ── Chat input ── */
        .stChatInput textarea,
        div[data-testid="stChatInput"] textarea {{
            background: var(--bg-input) !important;
            color: var(--text-primary) !important;
            border: 1.5px solid var(--border-focus) !important;
            border-radius: var(--radius-md) !important;
            font-size: 15px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            caret-color: var(--accent-light) !important;
        }}
        .stChatInput textarea::placeholder {{
            color: var(--text-muted) !important;
        }}

        /* ── Chat messages ── */
        [data-testid="stChatMessage"] {{
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-lg) !important;
        }}
        [data-testid="stChatMessage"] p {{
            color: var(--text-primary) !important;
            font-size: 14px !important;
            line-height: 1.7 !important;
        }}

        /* ── Progress bar ── */
        .stProgress > div > div > div {{
            background: linear-gradient(90deg, var(--accent), var(--accent-light)) !important;
            border-radius: 99px !important;
        }}
        .stProgress > div > div {{
            background: rgba(255,255,255,0.06) !important;
            border-radius: 99px !important;
        }}

        /* ── Containers / Cards ── */
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {{
            border-radius: var(--radius-lg) !important;
        }}
        div[data-testid="stHorizontalBlock"] {{
            gap: 12px !important;
        }}

        /* ── Scrollbar ── */
        ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
        ::-webkit-scrollbar-track {{ background: rgba(255,255,255,0.02); }}
        ::-webkit-scrollbar-thumb {{ background: rgba(124,92,252,0.35); border-radius: 99px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: rgba(124,92,252,0.6); }}

        /* ── Option menu nav ── */
        nav[data-testid="stHorizontalBlock"] {{ gap: 0 !important; }}
        </style>""", unsafe_allow_html=True)
    try:
        with open("logo.png", "rb") as f:
            lb64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<img src="data:image/png;base64,{lb64}" '
            f'style="position:fixed;top:10px;left:20px;width:80px;z-index:1001;">',
            unsafe_allow_html=True)
    except:
        pass

set_design()

# ==========================================
# 4. DB CONNECTION  (via db.py — PostgreSQL)
# ==========================================
def get_connection():
    """Return a psycopg2 connection for pd.read_sql calls."""
    return db.get_db()

# ==========================================
# 5. SESSION STATE
# ==========================================
for k, v in {"logged_in": False, "user_id": "", "user_name": "",
             "user_email": "", "otp_sent": False, "otp_demo": "",
             "otp_via": "", "otp_email": "", "reg_done": False,
             "admin_authenticated": False, "reg_otp_sent": False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================================
# 6. LOGIN / REGISTER  (Email OTP flow — direct db.py calls)
# ==========================================
ADMIN_KEY = os.getenv("ADMIN_SECRET", "joblib_admin_2026")

if not st.session_state.logged_in:
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown("""
            <div style="text-align:center;margin-bottom:28px;">
                <div style="font-size:56px;">🎓</div>
                <h1 style="color:#eef0f8;margin:6px 0;font-size:32px;font-weight:800;font-family:'Plus Jakarta Sans',sans-serif;">Jobsync</h1>
                <p style="color:#9aa3bf;font-size:15px;margin:0;">Student Placement Predictor</p>
            </div>
        """, unsafe_allow_html=True)

        tab_login, tab_otp, tab_register = st.tabs(["🔑 Sign In", "📧 Login with OTP", "📝 Create Account"])

        # ══════════════════════════════════════════
        # SIGN IN — Email + Password
        # ══════════════════════════════════════════
        with tab_login:
            with st.container(border=True):
                st.markdown("<p style='color:#9aa3bf;font-size:13px;margin-bottom:16px;'>"
                            "Sign in with your email and password.</p>",
                            unsafe_allow_html=True)
                login_email = st.text_input("Email Address", placeholder="you@example.com", key="login_email")
                login_pwd   = st.text_input("Password", placeholder="Your password", type="password", key="login_pwd")

                if st.button("🔑 Sign In", use_container_width=True, key="btn_signin"):
                    email_val = login_email.strip().lower()
                    pwd_val   = login_pwd
                    if not email_val or not pwd_val:
                        st.error("❌ Please enter your email and password.")
                    else:
                        with st.spinner("Signing in..."):
                            d = db.api_login(email_val, pwd_val)
                            if "error" in d:
                                st.error(f"❌ {d['error']}")
                            else:
                                st.session_state.logged_in  = True
                                st.session_state.user_id    = d["user_id"]
                                st.session_state.user_name  = d["name"]
                                st.session_state.user_email = email_val
                                st.rerun()

        # ══════════════════════════════════════════
        # SIGN IN — Email OTP
        # ══════════════════════════════════════════
        with tab_otp:
            with st.container(border=True):
                st.markdown("<p style='color:#9aa3bf;font-size:13px;margin-bottom:16px;'>"
                            "We'll send a 6-digit code to your registered email.</p>",
                            unsafe_allow_html=True)

                otp_email = st.text_input("Email Address", placeholder="you@example.com", key="otp_email_input")

                if not st.session_state.otp_sent:
                    if st.button("📧 Send OTP", use_container_width=True, key="btn_send_otp"):
                        email_val = otp_email.strip().lower()
                        if not email_val or "@" not in email_val:
                            st.error("❌ Enter a valid email address.")
                        else:
                            with st.spinner("Sending OTP to your email..."):
                                d = db.api_send_otp(email_val)
                                if "error" in d:
                                    st.error(f"❌ {d['error']}")
                                else:
                                    st.session_state.otp_sent  = True
                                    st.session_state.otp_email = email_val
                                    st.success("✅ OTP sent! Check your inbox (and spam folder).")
                                    st.rerun()
                else:
                    st.success(f"✅ OTP sent to **{st.session_state.get('otp_email', otp_email)}**")
                    entered_otp = st.text_input("Enter 6-digit OTP", placeholder="123456",
                                                max_chars=6, key="entered_otp")
                    col_v, col_r = st.columns(2)
                    with col_v:
                        if st.button("✅ Verify OTP", use_container_width=True, key="btn_verify_otp"):
                            if not entered_otp.strip():
                                st.error("❌ Please enter the OTP.")
                            else:
                                with st.spinner("Verifying..."):
                                    d = db.api_verify_otp(
                                        st.session_state.get("otp_email", otp_email),
                                        entered_otp.strip()
                                    )
                                    if "error" in d:
                                        st.error(f"❌ {d['error']}")
                                    else:
                                        st.session_state.logged_in  = True
                                        st.session_state.user_id    = d["user_id"]
                                        st.session_state.user_name  = d["name"]
                                        st.session_state.user_email = d["email"]
                                        st.session_state.otp_sent   = False
                                        st.session_state.otp_email  = ""
                                        st.rerun()
                    with col_r:
                        if st.button("🔄 Resend OTP", use_container_width=True, key="btn_resend_otp"):
                            with st.spinner("Resending..."):
                                d = db.api_send_otp(st.session_state.get("otp_email", otp_email))
                                if "error" in d:
                                    st.error(f"❌ {d['error']}")
                                else:
                                    st.success("✅ New OTP sent!")

        # ══════════════════════════════════════════
        # CREATE ACCOUNT
        # ══════════════════════════════════════════
        with tab_register:
            with st.container(border=True):
                st.markdown("<p style='color:#9aa3bf;font-size:13px;margin-bottom:16px;'>"
                            "Create your account to get started.</p>",
                            unsafe_allow_html=True)

                reg_name  = st.text_input("Full Name",        placeholder="Your full name",   key="reg_name")
                reg_email = st.text_input("Email Address",    placeholder="you@example.com",  key="reg_email")
                reg_pwd   = st.text_input("Password",         placeholder="Min 6 characters", type="password", key="reg_pwd")
                reg_pwd2  = st.text_input("Confirm Password", placeholder="Repeat password",  type="password", key="reg_pwd2")

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Create Account →", use_container_width=True, key="btn_register"):
                    name_val  = reg_name.strip()
                    email_val = reg_email.strip().lower()
                    pwd_val   = reg_pwd
                    pwd2_val  = reg_pwd2

                    if not name_val or not email_val or not pwd_val or not pwd2_val:
                        st.error("❌ All fields are required.")
                    elif "@" not in email_val or "." not in email_val:
                        st.error("❌ Enter a valid email address.")
                    elif len(pwd_val) < 6:
                        st.error("❌ Password must be at least 6 characters.")
                    elif pwd_val != pwd2_val:
                        st.error("❌ Passwords do not match.")
                    else:
                        with st.spinner("Creating account..."):
                            d = db.api_register(name_val, email_val, pwd_val)
                            if "error" in d:
                                st.error(f"❌ {d['error']}")
                            else:
                                st.success("✅ Account created! You can now sign in.")

        st.markdown("""
            <p style='text-align:center;color:#475569;font-size:12px;margin-top:20px;'>
                © 2026 Jobsync · Student Placement Predictor
            </p>
        """, unsafe_allow_html=True)
    st.stop()

# ==========================================
# 7. NAVIGATION
# ==========================================
page = option_menu(
    menu_title=None,
    options=["Home","Career Tools","AI Mentor","Live Dashboard","Student Help","Admin Portal","About"],
    icons=["house","tools","robot","bar-chart-line","question-circle","shield-lock","info-circle"],
    default_index=0, orientation="horizontal",
    styles={
        "container":{"padding":"0!important","background-color":"transparent"},
        "icon":{"color":"#a78bfa","font-size":"16px"},
        "nav-link":{"font-size":"13px","text-align":"center","margin":"0px",
                    "color":"#9aa3bf","border-bottom":"3px solid transparent",
                    "font-weight":"600","letter-spacing":"0.02em"},
        "nav-link-selected":{"background-color":"transparent","color":"#eef0f8",
                             "border-bottom":"3px solid #7c5cfc","font-weight":"800"},
    }
)

if st.sidebar.button("🚪 Logout"):
    for k in ["logged_in","user_id","user_name","user_email","otp_sent","otp_email","otp_demo","otp_via"]:
        st.session_state[k] = False if k == "logged_in" else ""
    # Clear the OTP input widget value too
    if "otp_email_input" in st.session_state:
        del st.session_state["otp_email_input"]
    st.rerun()

# ==========================================
# 8. HOME
# ==========================================
if page == "Home":
    name_display = st.session_state.get("user_name", "")
    st.title(f"Welcome back, {name_display}! 👋" if name_display else "Welcome back! 👋")
    st.header("🎓 Jobsync: Student Placement Predictor")
    st.image("placement_predictor.jpg", use_container_width=True)

# ==========================================
# 9. CAREER TOOLS
# ==========================================
elif page == "Career Tools":

    st.markdown("""
        <style>
        .skill-item { background:rgba(124,58,237,0.08); border-left:3px solid #7c3aed;
            border-radius:10px; padding:12px 16px; margin:8px 0; font-size:14px; color:#dde3f0; }
        .section-label { font-size:10px; text-transform:uppercase; letter-spacing:2px;
            color:#a78bfa; font-weight:800; margin-bottom:12px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color:#eef0f8;margin-bottom:4px;'>🎯 Career Analysis Engine</h2>",
                unsafe_allow_html=True)
    st.markdown("<p style='color:#9aa3bf;margin-bottom:24px;'>Fill in your complete profile "
                "for an AI-powered placement prediction with personalised insights.</p>",
                unsafe_allow_html=True)

    l_col, r_col = st.columns([1.1, 1], gap="large")

    with l_col:
        st.markdown('<div class="section-label">📚 Academic Profile</div>',
                    unsafe_allow_html=True)
        with st.container(border=True):
            cgpa = st.slider("CGPA", 0.0, 10.0, 7.5, step=0.1,
                             help="Your current cumulative GPA out of 10")
            col_a, col_b = st.columns(2)
            with col_a:
                age    = st.number_input("Age", 18, 30, 21)
                gender = st.selectbox("Gender", ["Male", "Female"])
            with col_b:
                stream = st.selectbox("Stream", [
                    "Computer Science", "Information Technology",
                    "Mechanical", "Civil", "Electrical",
                    "Electronics And Communication"
                ])
                backlog = 1 if st.toggle("Active Backlogs?") else 0

        st.markdown('<div class="section-label" style="margin-top:16px;">💼 Experience & Activities</div>',
                    unsafe_allow_html=True)
        with st.container(border=True):
            internships = st.select_slider(
                "Internships Completed", options=[0,1,2,3,4,5], value=1,
                help="Number of internships done so far"
            )
            col_c, col_d = st.columns(2)
            with col_c:
                projects = st.number_input(
                    "Projects Built", 0, 20, 2,
                    help="Total personal/academic projects (GitHub, college, freelance)"
                )
            with col_d:
                hackathons = st.number_input(
                    "Hackathons Participated", 0, 20, 1,
                    help="Number of hackathons you have participated in"
                )

        # Live profile strength bar
        preview_score  = min(cgpa/10.0*35, 35)
        preview_score += min(internships/5.0*20, 20)
        preview_score += min(projects/6.0*20, 20)
        preview_score += min(hackathons/5.0*15, 15)
        preview_score += 10 if backlog == 0 else 0
        preview_score  = round(preview_score, 1)

        bar_color = "#22c55e" if preview_score >= 70 else "#f59e0b" if preview_score >= 45 else "#f43f5e"
        st.markdown(f"""
            <div style="margin-top:14px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                    <span style="color:#a0a0b0;font-size:13px;">Profile Strength</span>
                    <span style="color:{bar_color};font-weight:700;font-size:14px;">{preview_score}/100</span>
                </div>
                <div style="background:rgba(255,255,255,0.08);border-radius:8px;height:10px;overflow:hidden;">
                    <div style="width:{preview_score}%;background:{bar_color};height:100%;border-radius:8px;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🚀 RUN ANALYSIS NOW", use_container_width=True)

    with r_col:
        if analyze_btn:
            with st.spinner("Analysing your profile..."):
                try:
                    d = db.api_predict(
                        user_id     = st.session_state.user_id,
                        age         = int(age),
                        gender      = gender,
                        stream      = stream,
                        internships = int(internships),
                        cgpa        = float(cgpa),
                        backlog     = int(backlog),
                        projects    = int(projects),
                        hackathons  = int(hackathons),
                    )
                    if "error" in d:
                        st.error(f"❌ {d['error']}")
                    else:
                        placement     = d["placement"]
                        confidence    = d["confidence"]
                        profile_score = d.get("profile_score", preview_score)
                        skills        = d.get("skills", [])

                        if placement == 1:
                            st.markdown("""
                                <div style="background:linear-gradient(135deg,rgba(34,197,94,0.2),rgba(16,185,129,0.1));
                                    border:1px solid rgba(34,197,94,0.5);border-radius:16px;
                                    padding:20px;text-align:center;margin-bottom:16px;">
                                    <div style="font-size:40px;">🎉</div>
                                    <div style="font-size:24px;font-weight:800;color:#4ade80;">LIKELY PLACED</div>
                                    <div style="color:#86efac;font-size:14px;margin-top:4px;">
                                        Strong placement prospects based on your profile</div>
                                </div>""", unsafe_allow_html=True)
                        else:
                            st.markdown("""
                                <div style="background:linear-gradient(135deg,rgba(244,63,94,0.2),rgba(239,68,68,0.1));
                                    border:1px solid rgba(244,63,94,0.5);border-radius:16px;
                                    padding:20px;text-align:center;margin-bottom:16px;">
                                    <div style="font-size:40px;">⚠️</div>
                                    <div style="font-size:24px;font-weight:800;color:#f87171;">NEEDS IMPROVEMENT</div>
                                    <div style="color:#fca5a5;font-size:14px;margin-top:4px;">
                                        Work on the suggestions below to boost your chances</div>
                                </div>""", unsafe_allow_html=True)

                        # Metric cards
                        m1, m2 = st.columns(2)
                        conf_color = "#4ade80" if confidence >= 0.65 else "#f59e0b" if confidence >= 0.45 else "#f87171"
                        sc_color   = "#4ade80" if profile_score >= 70 else "#f59e0b" if profile_score >= 45 else "#f87171"
                        m1.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);border-radius:14px;
                                padding:16px;text-align:center;border:1px solid rgba(255,255,255,0.1);">
                                <div style="font-size:11px;color:#a0a0b0;text-transform:uppercase;letter-spacing:1px;">AI Confidence</div>
                                <div style="font-size:32px;font-weight:800;color:{conf_color};">{confidence*100:.1f}%</div>
                            </div>""", unsafe_allow_html=True)
                        m2.markdown(f"""
                            <div style="background:rgba(255,255,255,0.05);border-radius:14px;
                                padding:16px;text-align:center;border:1px solid rgba(255,255,255,0.1);">
                                <div style="font-size:11px;color:#a0a0b0;text-transform:uppercase;letter-spacing:1px;">Profile Score</div>
                                <div style="font-size:32px;font-weight:800;color:{sc_color};">{profile_score}<span style="font-size:16px;color:#a0a0b0;">/100</span></div>
                            </div>""", unsafe_allow_html=True)

                        # Score breakdown
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown('<div class="section-label">📊 Score Breakdown</div>',
                                    unsafe_allow_html=True)
                        breakdown = {
                            "CGPA":        (min(cgpa/10.0*35,35),       35,  "#6366F1"),
                            "Internships": (min(internships/5.0*20,20), 20,  "#8b5cf6"),
                            "Projects":    (min(projects/6.0*20,20),    20,  "#a78bfa"),
                            "Hackathons":  (min(hackathons/5.0*15,15),  15,  "#c4b5fd"),
                            "No Backlog":  (10 if backlog==0 else 0,    10,  "#22c55e"),
                        }
                        for lbl_b, (earned, total_b, clr) in breakdown.items():
                            pct = earned / total_b * 100
                            st.markdown(f"""
                                <div style="margin-bottom:10px;">
                                    <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                                        <span style="color:#cbd5e1;font-size:13px;">{lbl_b}</span>
                                        <span style="color:{clr};font-size:13px;font-weight:600;">{earned:.1f}/{total_b}</span>
                                    </div>
                                    <div style="background:rgba(255,255,255,0.08);border-radius:6px;height:8px;overflow:hidden;">
                                        <div style="width:{pct:.0f}%;background:{clr};height:100%;border-radius:6px;"></div>
                                    </div>
                                </div>""", unsafe_allow_html=True)

                        # Skill suggestions
                        if skills:
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.markdown('<div class="section-label">💡 Personalised Suggestions</div>',
                                        unsafe_allow_html=True)
                            for skill in skills:
                                st.markdown(f'<div class="skill-item">✅ {skill}</div>',
                                            unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"❌ Unexpected error: {e}")
        else:
            st.markdown("""
                <div style="background:rgba(255,255,255,0.03);border:1px dashed rgba(99,102,241,0.4);
                    border-radius:18px;padding:48px 24px;text-align:center;margin-top:8px;">
                    <div style="font-size:48px;margin-bottom:12px;">🎓</div>
                    <div style="color:#a0a0b0;font-size:15px;line-height:1.7;">
                        Fill in your academic profile and experience<br>
                        then click <strong style="color:#6366F1;">RUN ANALYSIS NOW</strong><br>
                        to get your AI-powered placement prediction.
                    </div>
                </div>""", unsafe_allow_html=True)

# ==========================================
# 10. AI MENTOR
# ==========================================
elif page == "AI Mentor":
    st.markdown("<h2 style='color:#eef0f8;margin-bottom:4px;'>🤖 AI Career Mentor</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#9aa3bf;margin-bottom:16px;'>Your personal mentor tracks your placement history and answers your questions with personalised advice.</p>", unsafe_allow_html=True)

    # ── Load this student's latest prediction from DB ──────────────────
    student_profile = None
    prediction_history = []
    try:
        conn = get_connection()
        hist_df = pd.read_sql(
            "SELECT * FROM predictions WHERE user_id = %s ORDER BY id DESC",
            conn,
            params=(st.session_state.user_id,)
        )
        conn.close()
        if not hist_df.empty:
            prediction_history = hist_df.to_dict("records")
            latest = hist_df.iloc[0]
            student_profile = {
                "cgpa":        float(latest["cgpa"]),
                "stream":      latest["stream"],
                "internships": int(latest["internships"]),
                "projects":    int(latest.get("projects", 0)),
                "hackathons":  int(latest.get("hackathons", 0)),
                "backlog":     int(latest["backlog"]),
                "result":      int(latest["result"]),
                "confidence":  float(latest["confidence"]),
                "timestamp":   str(latest["timestamp"]),
            }
    except Exception as e:
        st.warning(f"Could not load your history: {e}")

    # ── Profile snapshot card ───────────────────────────────────────────
    if student_profile:
        p = student_profile
        placed_label = "✅ Placed" if p["result"] == 1 else "⚠️ Not Placed"
        placed_color = "#22c55e"  if p["result"] == 1 else "#f43f5e"
        conf_pct     = round(p["confidence"] * 100, 1)

        # Trend arrow — compare last two predictions
        trend_html = ""
        if len(prediction_history) >= 2:
            prev_conf = float(prediction_history[1]["confidence"])
            delta     = p["confidence"] - prev_conf
            if delta > 0.01:
                trend_html = "<span style='color:#22c55e;font-size:13px;'>▲ Improving</span>"
            elif delta < -0.01:
                trend_html = "<span style='color:#f43f5e;font-size:13px;'>▼ Declining</span>"
            else:
                trend_html = "<span style='color:#f59e0b;font-size:13px;'>→ Stable</span>"

        st.markdown(f"""
            <div style='background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.3);
                border-radius:16px;padding:18px 24px;margin-bottom:20px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;'>
                    <div>
                        <div style='color:#a0a0b0;font-size:11px;text-transform:uppercase;letter-spacing:1px;'>Latest Prediction</div>
                        <div style='color:white;font-size:18px;font-weight:700;margin-top:2px;'>{p["stream"]} · CGPA {p["cgpa"]}</div>
                        <div style='color:#a0a0b0;font-size:12px;margin-top:2px;'>Last run: {p["timestamp"]}</div>
                    </div>
                    <div style='text-align:center;'>
                        <div style='font-size:28px;font-weight:800;color:{placed_color};'>{placed_label}</div>
                        <div style='color:#a0a0b0;font-size:13px;'>Confidence: <b style='color:white;'>{conf_pct}%</b> &nbsp;{trend_html}</div>
                    </div>
                    <div style='display:flex;gap:16px;flex-wrap:wrap;'>
                        <div style='text-align:center;'>
                            <div style='color:#6366F1;font-size:20px;font-weight:700;'>{p["internships"]}</div>
                            <div style='color:#a0a0b0;font-size:11px;'>Internships</div>
                        </div>
                        <div style='text-align:center;'>
                            <div style='color:#6366F1;font-size:20px;font-weight:700;'>{p["projects"]}</div>
                            <div style='color:#a0a0b0;font-size:11px;'>Projects</div>
                        </div>
                        <div style='text-align:center;'>
                            <div style='color:#6366F1;font-size:20px;font-weight:700;'>{p["hackathons"]}</div>
                            <div style='color:#a0a0b0;font-size:11px;'>Hackathons</div>
                        </div>
                        <div style='text-align:center;'>
                            <div style='color:{"#f43f5e" if p["backlog"] else "#22c55e"};font-size:20px;font-weight:700;'>{"Yes" if p["backlog"] else "No"}</div>
                            <div style='color:#a0a0b0;font-size:11px;'>Backlog</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Prediction trend chart if multiple runs
        if len(prediction_history) > 1:
            with st.expander("📈 View My Prediction History"):
                hist_plot = pd.DataFrame(prediction_history)[["timestamp","confidence","result"]].copy()
                hist_plot["confidence"] = (hist_plot["confidence"] * 100).round(1)
                hist_plot["timestamp"]  = pd.to_datetime(hist_plot["timestamp"])
                hist_plot = hist_plot.sort_values("timestamp")

                fig, ax = plt.subplots(figsize=(8, 3), facecolor="none")
                ax.plot(hist_plot["timestamp"], hist_plot["confidence"],
                        color="#6366F1", linewidth=2.5, marker="o", markersize=6)
                ax.fill_between(hist_plot["timestamp"], hist_plot["confidence"],
                                alpha=0.15, color="#6366F1")
                ax.set_facecolor("none")
                fig.patch.set_alpha(0)
                ax.tick_params(colors="white", labelsize=9)
                for spine in ax.spines.values():
                    spine.set_edgecolor((1,1,1,0.1))
                ax.set_ylabel("Confidence %", color="white", fontsize=10)
                ax.set_ylim(0, 105)
                plt.xticks(rotation=20, ha="right")
                st.pyplot(fig); plt.close(fig)
    else:
        st.info("💡 Run a prediction in **Career Tools** first — the mentor will then track your profile and give personalised advice.")

    st.markdown("---")

    # ── Mentor Chat ─────────────────────────────────────────────────────
    st.markdown("### 💬 Ask Your Mentor")
    st.markdown("<p style='color:#9aa3bf;font-size:13px;margin-bottom:16px;'>Ask anything about your placement preparation — the mentor knows your profile.</p>", unsafe_allow_html=True)

    # Quick question chips
    st.markdown("<div style='color:#9aa3bf;font-size:12px;margin-bottom:8px;'>Quick questions:</div>", unsafe_allow_html=True)
    chip_cols = st.columns(4)
    quick_questions = [
        "What should I do now?",
        "How can I improve my score?",
        "Am I ready for placements?",
        "What skills should I learn?",
    ]
    chip_clicked = None
    for i, q in enumerate(quick_questions):
        if chip_cols[i].button(q, key=f"chip_{i}", use_container_width=True):
            chip_clicked = q

    # Chat history in session state
    if "mentor_chat" not in st.session_state:
        st.session_state.mentor_chat = []

    # Input box
    user_question = st.chat_input("Type your question here...")
    if chip_clicked:
        user_question = chip_clicked

    # ── Gemini-powered mentor ────────────────────────────────────────────
    def mentor_answer(question: str, profile: dict, history: list) -> str:
        grok_key = os.getenv("GROK_API_KEY", "")

        # Build profile context string
        if profile:
            cgpa        = profile["cgpa"]
            stream      = profile["stream"]
            internships = profile["internships"]
            projects    = profile["projects"]
            hackathons  = profile["hackathons"]
            backlog     = profile["backlog"]
            result      = profile["result"]
            confidence  = profile["confidence"]
            score  = min(cgpa/10.0*30, 30)
            score += min(internships/3.0*25, 25)
            score += min(projects/5.0*25, 25)
            score += min(hackathons/3.0*10, 10)
            score += 10 if not backlog else 0
            score  = round(score, 1)
            trend = ""
            if len(history) >= 2:
                delta = float(history[0]["confidence"]) - float(history[1]["confidence"])
                trend = "improving" if delta > 0.01 else "declining" if delta < -0.01 else "stable"
            profile_ctx = f"""
Student Profile:
- Name: {st.session_state.get("user_name", "Student")}
- Stream: {stream}
- CGPA: {cgpa}/10
- Internships: {internships}
- Projects: {projects}
- Hackathons: {hackathons}
- Active Backlogs: {"Yes" if backlog else "No"}
- ML Placement Prediction: {"Placed" if result == 1 else "Not Placed"}
- Model Confidence: {round(confidence * 100, 1)}%
- Readiness Score: {score}/100
- Trend (across runs): {trend if trend else "only 1 run so far"}
- Total prediction runs: {len(history)}
"""
        else:
            score = 0
            profile_ctx = "The student has not run a placement prediction yet. Encourage them to go to Career Tools first."

        system_prompt = f"""You are an expert AI Career Mentor for engineering students in India, embedded in the Jobsync Student Placement Predictor app.

{profile_ctx}

Your role:
- Give concise, actionable, personalised career advice based on the student's profile above
- Be warm, encouraging, and direct — like a senior mentor who genuinely cares
- Use bullet points and bold text (markdown) for clarity
- Keep responses under 250 words unless the question genuinely needs more detail
- Focus on placement preparation: CGPA, internships, projects, hackathons, DSA, resume, interviews
- Reference the student's actual numbers when giving advice
- If the student has no profile yet, gently ask them to run a prediction first

Do NOT:
- Give generic advice that ignores the student's actual profile
- Be overly verbose or repeat yourself
- Mention that you are Grok or any AI model name
"""

        if grok_key and grok_key != "your_grok_api_key_here":
            try:
                client = _OpenAI(
                    api_key=grok_key,
                    base_url="https://api.groq.com/openai/v1"
                )
                # Build conversation history for context (last 3 exchanges = 6 messages)
                messages = [{"role": "system", "content": system_prompt}]
                for msg in st.session_state.mentor_chat[-6:]:
                    role = "user" if msg["role"] == "user" else "assistant"
                    messages.append({"role": role, "content": msg["text"]})
                messages.append({"role": "user", "content": question})

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    max_tokens=400,
                    temperature=0.7,
                )
                return response.choices[0].message.content
            except Exception as e:
                return (f"⚠️ AI Mentor is temporarily unavailable ({str(e)[:80]}).\n\n"
                        f"Based on your profile — **{profile.get('stream','N/A')}**, CGPA **{profile.get('cgpa','N/A')}**, "
                        f"readiness score **{score}/100** — please check your GROK_API_KEY in the .env file.")
        else:
            return ("⚠️ **Groq API key not configured.**\n\n"
                    "To enable the AI Mentor:\n"
                    "1. Get a free API key from [Groq Console](https://console.groq.com/keys)\n"
                    "2. Add it to your `.env` file: `GROK_API_KEY=gsk_your_key_here`\n"
                    "3. Restart the app")

    # ── Process question and update chat ────────────────────────────────
    if user_question:
        st.session_state.mentor_chat.append({"role": "user", "text": user_question})
        with st.spinner("🤖 Mentor is thinking..."):
            answer = mentor_answer(user_question, student_profile, prediction_history)
        st.session_state.mentor_chat.append({"role": "mentor", "text": answer})

    # ── Render chat history ──────────────────────────────────────────────
    def render_mentor_text(text: str) -> str:
        """Convert markdown bold/newlines to HTML for chat bubbles."""
        import re
        html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = html.replace("\n", "<br>")
        return html

    if st.session_state.mentor_chat:
        for msg in st.session_state.mentor_chat:
            if msg["role"] == "user":
                st.markdown(f"""
                    <div style='display:flex;justify-content:flex-end;margin:10px 0;'>
                        <div style='background:linear-gradient(135deg,rgba(124,58,237,0.35),rgba(99,102,241,0.25));
                            border:1px solid rgba(124,58,237,0.4);
                            border-radius:18px 18px 4px 18px;
                            padding:12px 18px;max-width:75%;color:#f0f4ff;font-size:14px;
                            font-family:Inter,sans-serif;line-height:1.6;'>
                            {msg["text"]}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style='display:flex;justify-content:flex-start;margin:10px 0;gap:10px;align-items:flex-start;'>
                        <div style='font-size:26px;margin-top:4px;'>🤖</div>
                        <div style='background:rgba(255,255,255,0.04);
                            border:1px solid rgba(139,92,246,0.2);
                            border-radius:4px 18px 18px 18px;
                            padding:14px 18px;max-width:82%;
                            color:#dde3f0;font-size:14px;
                            font-family:Inter,sans-serif;line-height:1.75;'>
                            {render_mentor_text(msg["text"])}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        if st.button("🗑️ Clear Chat", key="clear_chat"):
            st.session_state.mentor_chat = []
            st.rerun()
    else:
        st.markdown("""
            <div style='background:rgba(255,255,255,0.03);border:1px dashed rgba(99,102,241,0.3);
                border-radius:16px;padding:40px;text-align:center;margin-top:8px;'>
                <div style='font-size:40px;margin-bottom:12px;'>🤖</div>
                <div style='color:#a0a0b0;font-size:15px;line-height:1.8;'>
                    Ask me anything about your placement journey.<br>
                    Use the quick questions above or type your own below.
                </div>
            </div>
        """, unsafe_allow_html=True)

# ==========================================
# 11. LIVE DASHBOARD
# ==========================================
elif page == "Live Dashboard":
    st.title("📊 Live Placement Dashboard")
    st.caption("Refreshed live from the database on every page load.")

    try:
        conn = get_connection()
        df   = pd.read_sql("SELECT * FROM predictions ORDER BY id DESC", conn)
        conn.close()
    except Exception as e:
        st.error(f"❌ Database error: {e}")
        st.stop()

    if df.empty:
        st.warning("No data yet. Run some analyses first!")
        st.stop()

    df["timestamp"]    = pd.to_datetime(df["timestamp"])
    df["result_label"] = df["result"].map({1:"Placed", 0:"Not Placed"})

    total      = len(df)
    placed     = int(df["result"].sum())
    not_placed = total - placed
    avg_cgpa   = df["cgpa"].mean()
    avg_conf   = df["confidence"].mean()

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("📋 Total Predictions", total)
    k2.metric("✅ Placed",            placed)
    k3.metric("❌ Not Placed",        not_placed)
    k4.metric("📈 Avg CGPA",          f"{avg_cgpa:.2f}")
    k5.metric("🎯 Avg Confidence",    f"{avg_conf*100:.1f}%")
    st.markdown("---")

    SPINE_COLOR = (1, 1, 1, 0.15)
    PLACED_CLR  = "#6366F1"
    NOTPLC_CLR  = "#f43f5e"
    BAR_COLORS  = {"Placed": PLACED_CLR, "Not Placed": NOTPLC_CLR}

    def style_ax(ax, fig):
        ax.set_facecolor("none")
        fig.patch.set_alpha(0)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor(SPINE_COLOR)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🥧 Placement Outcome")
        counts = df["result_label"].value_counts()
        fig, ax = plt.subplots(figsize=(5,4), facecolor="none")
        ax.pie(counts, labels=counts.index, autopct="%1.1f%%",
               colors=[PLACED_CLR, NOTPLC_CLR], startangle=140,
               textprops={"color":"white","fontsize":12})
        fig.patch.set_alpha(0)
        st.pyplot(fig); plt.close(fig)

    with c2:
        st.subheader("📊 Placements by Stream")
        sc = df.groupby(["stream","result_label"]).size().unstack(fill_value=0)
        fig2, ax2 = plt.subplots(figsize=(6,4), facecolor="none")
        sc.plot(kind="bar", ax=ax2,
                color=[BAR_COLORS.get(col,"#888") for col in sc.columns],
                edgecolor="none", width=0.65)
        style_ax(ax2, fig2)
        ax2.set_xlabel("Stream", color="white", fontsize=9)
        ax2.set_ylabel("Count",  color="white", fontsize=9)
        ax2.set_xticklabels(sc.index, rotation=30, ha="right", color="white")
        ax2.legend(facecolor="#1e1e2e", labelcolor="white", fontsize=9)
        st.pyplot(fig2); plt.close(fig2)

    st.markdown("---")

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("📉 CGPA Distribution by Outcome")
        fig3, ax3 = plt.subplots(figsize=(5,4), facecolor="none")
        for lbl, clr in [("Placed", PLACED_CLR), ("Not Placed", NOTPLC_CLR)]:
            ax3.hist(df[df["result_label"]==lbl]["cgpa"], bins=15,
                     alpha=0.7, color=clr, label=lbl, edgecolor="none")
        style_ax(ax3, fig3)
        ax3.set_xlabel("CGPA",  color="white")
        ax3.set_ylabel("Count", color="white")
        ax3.legend(facecolor="#1e1e2e", labelcolor="white")
        st.pyplot(fig3); plt.close(fig3)

    with c4:
        st.subheader("🎯 Confidence Score Distribution")
        fig4, ax4 = plt.subplots(figsize=(5,4), facecolor="none")
        ax4.hist(df["confidence"]*100, bins=20, color=PLACED_CLR, edgecolor="none", alpha=0.85)
        style_ax(ax4, fig4)
        ax4.set_xlabel("Confidence (%)", color="white")
        ax4.set_ylabel("Count",          color="white")
        st.pyplot(fig4); plt.close(fig4)

    st.markdown("---")

    c5, c6 = st.columns(2)
    with c5:
        st.subheader("👥 Placement by Gender")
        gd = df.groupby(["gender","result_label"]).size().unstack(fill_value=0)
        fig5, ax5 = plt.subplots(figsize=(5,4), facecolor="none")
        gd.plot(kind="bar", ax=ax5,
                color=[BAR_COLORS.get(col,"#888") for col in gd.columns],
                edgecolor="none", width=0.5)
        style_ax(ax5, fig5)
        ax5.set_xlabel("Gender", color="white")
        ax5.set_ylabel("Count",  color="white")
        ax5.set_xticklabels(gd.index, rotation=0, color="white")
        ax5.legend(facecolor="#1e1e2e", labelcolor="white", fontsize=9)
        st.pyplot(fig5); plt.close(fig5)

    with c6:
        st.subheader("🚫 Backlog Impact on Placement")
        bd = df.groupby(["backlog","result_label"]).size().unstack(fill_value=0)
        bd.index = bd.index.map({0:"No Backlog", 1:"Has Backlog"})
        fig6, ax6 = plt.subplots(figsize=(5,4), facecolor="none")
        bd.plot(kind="bar", ax=ax6,
                color=[BAR_COLORS.get(col,"#888") for col in bd.columns],
                edgecolor="none", width=0.5)
        style_ax(ax6, fig6)
        ax6.set_xlabel("Backlog Status", color="white")
        ax6.set_ylabel("Count",          color="white")
        ax6.set_xticklabels(bd.index, rotation=0, color="white")
        ax6.legend(facecolor="#1e1e2e", labelcolor="white", fontsize=9)
        st.pyplot(fig6); plt.close(fig6)

    st.markdown("---")

    c7, c8 = st.columns(2)
    with c7:
        st.subheader("🔵 CGPA vs Confidence Score")
        fig7, ax7 = plt.subplots(figsize=(5,4), facecolor="none")
        for lbl, clr in [("Placed", PLACED_CLR), ("Not Placed", NOTPLC_CLR)]:
            sub = df[df["result_label"]==lbl]
            ax7.scatter(sub["cgpa"], sub["confidence"]*100,
                        alpha=0.6, color=clr, label=lbl, s=40, edgecolors="none")
        style_ax(ax7, fig7)
        ax7.set_xlabel("CGPA",           color="white")
        ax7.set_ylabel("Confidence (%)", color="white")
        ax7.legend(facecolor="#1e1e2e", labelcolor="white", fontsize=9)
        st.pyplot(fig7); plt.close(fig7)

    with c8:
        st.subheader("💼 Internships vs Placement Rate")
        ir = (df.groupby("internships")["result"]
                .agg(["sum","count"])
                .rename(columns={"sum":"placed","count":"total"}))
        ir["rate"] = (ir["placed"] / ir["total"] * 100).round(1)
        fig8, ax8 = plt.subplots(figsize=(5,4), facecolor="none")
        bars = ax8.bar(ir.index.astype(str), ir["rate"],
                       color=PLACED_CLR, edgecolor="none", width=0.5)
        for bar, val in zip(bars, ir["rate"]):
            ax8.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                     f"{val}%", ha="center", va="bottom", color="white", fontsize=9)
        style_ax(ax8, fig8)
        ax8.set_xlabel("Number of Internships", color="white")
        ax8.set_ylabel("Placement Rate (%)",    color="white")
        ax8.set_ylim(0, 115)
        st.pyplot(fig8); plt.close(fig8)

    st.markdown("---")

    st.subheader("🧠 Key Insights")
    placed_cgpa     = df[df["result"]==1]["cgpa"].mean() if placed > 0 else 0
    not_placed_cgpa = df[df["result"]==0]["cgpa"].mean() if not_placed > 0 else 0
    top_stream      = df[df["result"]==1]["stream"].value_counts().idxmax() if placed > 0 else "N/A"
    bl_total        = len(df[df["backlog"]==1])
    bl_placed       = len(df[(df["backlog"]==1) & (df["result"]==1)])
    backlog_rate    = bl_placed / max(bl_total, 1) * 100

    i1,i2,i3,i4 = st.columns(4)
    i1.metric("Avg CGPA (Placed)",     f"{placed_cgpa:.2f}")
    i2.metric("Avg CGPA (Not Placed)", f"{not_placed_cgpa:.2f}")
    i3.metric("Top Placed Stream",     top_stream)
    i4.metric("Backlog Placed Rate",   f"{backlog_rate:.1f}%")

    st.markdown("---")

    st.subheader("🗂️ Recent Predictions (Last 15)")
    cols_to_show = [c for c in ["user_id","age","gender","stream","internships",
                                 "cgpa","backlog","projects","hackathons",
                                 "result_label","confidence","timestamp"] if c in df.columns]
    disp = df.head(15)[cols_to_show].copy()
    disp["confidence"] = (disp["confidence"]*100).round(1).astype(str) + "%"
    st.dataframe(disp, use_container_width=True, hide_index=True)

# ==========================================
# 11. STUDENT HELP
# ==========================================
elif page == "Student Help":
    st.title("❓ Student Help Center")
    st.markdown("""
        <p style='color:#a0a0b0;margin-bottom:24px;'>
        Having trouble with login or need assistance? Submit your query below and our team will respond promptly.
        </p>
    """, unsafe_allow_html=True)

    tab_submit, tab_my_queries = st.tabs(["📝 Submit New Query", "📋 My Queries"])

    with tab_submit:
        with st.container(border=True):
            st.markdown('<div class="section-label">Submit Your Query</div>', unsafe_allow_html=True)
            
            query_subject = st.selectbox(
                "Subject",
                ["Login Issue", "OTP Not Received", "Prediction Error", 
                 "Account Registration", "Profile Update", "General Query", "Other"]
            )
            
            query_message = st.text_area(
                "Describe your issue in detail",
                placeholder="Please provide as much detail as possible so we can help you better...",
                height=150
            )
            
            if st.button("🚀 Submit Query", use_container_width=True):
                if not query_message.strip():
                    st.error("❌ Please describe your issue before submitting.")
                else:
                    data = db.api_submit_query(
                        user_id    = st.session_state.user_id,
                        user_name  = st.session_state.user_name,
                        user_email = st.session_state.user_email,
                        subject    = query_subject,
                        message    = query_message.strip(),
                    )
                    if "error" in data:
                        st.error(f"❌ {data['error']}")
                    else:
                        st.success("✅ Query submitted successfully! Our team will respond soon.")

    with tab_my_queries:
        st.markdown('<div class="section-label">Your Previous Queries</div>', unsafe_allow_html=True)
        
        try:
            conn = get_connection()
            user_queries_df = pd.read_sql(
                "SELECT * FROM support_queries WHERE user_id = %s ORDER BY id DESC",
                conn,
                params=(st.session_state.user_id,)
            )
            conn.close()
            
            if user_queries_df.empty:
                st.info("📭 You haven't submitted any queries yet.")
            else:
                for _, row in user_queries_df.iterrows():
                    status_color = "#22c55e" if row["status"] == "resolved" else "#f59e0b"
                    status_icon = "✅" if row["status"] == "resolved" else "⏳"
                    
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{row['subject']}**")
                        with col2:
                            st.markdown(f"<span style='color:{status_color};font-weight:600;'>{status_icon} {row['status'].upper()}</span>", unsafe_allow_html=True)
                        
                        st.markdown(f"<p style='color:#9aa3bf;font-size:13px;'>Submitted: {row['created_at']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='color:#eef0f8;'><b>Your Query:</b> {row['message']}</p>", unsafe_allow_html=True)
                        
                        if row["status"] == "resolved" and row["admin_reply"]:
                            st.markdown(f"""
                                <div style='background:rgba(34,197,94,0.1);border-left:3px solid #22c55e;
                                    padding:12px;border-radius:8px;margin-top:8px;'>
                                    <p style='color:#22c55e;font-weight:600;margin:0 0 6px 0;'>Admin Reply:</p>
                                    <p style='color:#e2e8f0;margin:0;'>{row['admin_reply']}</p>
                                    <p style='color:#a0a0b0;font-size:12px;margin:6px 0 0 0;'>Replied: {row['replied_at']}</p>
                                </div>
                            """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"❌ Failed to load queries: {e}")

# ==========================================
# 12. ADMIN PORTAL
# ==========================================
elif page == "Admin Portal":
    st.title("🛡️ Admin Portal")
    st.markdown("<p style='color:#9aa3bf;'>Manage student support queries and monitor platform activity.</p>", unsafe_allow_html=True)

    # Admin authentication
    if not st.session_state.admin_authenticated:
        with st.container(border=True):
            st.markdown("### 🔐 Admin Login")
            admin_key_input = st.text_input(
                "Enter Admin Secret Key",
                type="password",
                placeholder="Admin key required",
                key="admin_key_field"
            )
            if st.button("🔓 Authenticate", use_container_width=True):
                entered = st.session_state.get("admin_key_field", "").strip()
                expected = ADMIN_KEY.strip()
                if entered == expected:
                    st.session_state.admin_authenticated = True
                    st.success("✅ Admin access granted!")
                    st.rerun()
                else:
                    st.error(f"❌ Invalid admin key.")
        st.stop()

    # Admin is authenticated
    st.success("✅ Logged in as Admin")
    if st.button("🚪 Admin Logout"):
        st.session_state.admin_authenticated = False
        st.rerun()

    st.markdown("---")

    # Tabs for admin
    tab_queries, tab_stats = st.tabs(["📬 Support Queries", "📊 Platform Stats"])

    with tab_queries:
        st.markdown('<div class="section-label">All Student Queries</div>', unsafe_allow_html=True)

        # Filter controls
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_status = st.selectbox("Filter by Status", ["All", "open", "resolved"])
        with col_f2:
            filter_subject = st.selectbox("Filter by Subject", [
                "All", "Login Issue", "OTP Not Received", "Prediction Error",
                "Account Registration", "Profile Update", "General Query", "Other"
            ])

        try:
            data = db.api_get_queries(ADMIN_KEY)

            if "error" in data:
                st.error(f"❌ {data['error']}")
            else:
                queries = data.get("queries", [])

                # Apply filters
                if filter_status != "All":
                    queries = [q for q in queries if q["status"] == filter_status]
                if filter_subject != "All":
                    queries = [q for q in queries if q["subject"] == filter_subject]

                open_count     = sum(1 for q in data.get("queries", []) if q["status"] == "open")
                resolved_count = sum(1 for q in data.get("queries", []) if q["status"] == "resolved")

                m1, m2, m3 = st.columns(3)
                m1.metric("📬 Total Queries", len(data.get("queries", [])))
                m2.metric("⏳ Open",           open_count)
                m3.metric("✅ Resolved",        resolved_count)

                st.markdown("---")

                if not queries:
                    st.info("📭 No queries match the selected filters.")
                else:
                    for q in queries:
                        status_color = "#22c55e" if q["status"] == "resolved" else "#f59e0b"
                        status_icon  = "✅" if q["status"] == "resolved" else "⏳"

                        with st.container(border=True):
                            c1, c2, c3 = st.columns([2, 1, 1])
                            with c1:
                                st.markdown(f"**#{q['id']} — {q['subject']}**")
                            with c2:
                                st.markdown(f"<span style='color:{status_color};font-weight:600;'>{status_icon} {q['status'].upper()}</span>", unsafe_allow_html=True)
                            with c3:
                                st.markdown(f"<span style='color:#9aa3bf;font-size:12px;'>{q['created_at']}</span>", unsafe_allow_html=True)

                            st.markdown(f"👤 **{q['user_name']}** | 📧 {q['user_email']}")
                            st.markdown(f"<p style='color:#eef0f8;background:rgba(255,255,255,0.04);padding:10px;border-radius:8px;'>{q['message']}</p>", unsafe_allow_html=True)

                            if q["status"] == "resolved" and q["admin_reply"]:
                                st.markdown(f"""
                                    <div style='background:rgba(34,197,94,0.1);border-left:3px solid #22c55e;
                                        padding:10px;border-radius:8px;margin-top:6px;'>
                                        <b style='color:#22c55e;'>Your Reply:</b>
                                        <p style='color:#e2e8f0;margin:4px 0 0 0;'>{q['admin_reply']}</p>
                                    </div>
                                """, unsafe_allow_html=True)
                            else:
                                reply_text = st.text_area(
                                    f"Reply to Query #{q['id']}",
                                    placeholder="Type your reply here...",
                                    key=f"reply_{q['id']}",
                                    height=100
                                )
                                if st.button(f"📤 Send Reply to #{q['id']}", key=f"btn_reply_{q['id']}"):
                                    if not reply_text.strip():
                                        st.error("Reply cannot be empty.")
                                    else:
                                        rd = db.api_reply_query(ADMIN_KEY, q["id"], reply_text.strip())
                                        if "error" in rd:
                                            st.error(f"❌ {rd['error']}")
                                        else:
                                            st.success(f"✅ Reply sent for Query #{q['id']}!")
                                            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to load queries: {e}")

    with tab_stats:
        st.markdown('<div class="section-label">Platform Overview</div>', unsafe_allow_html=True)
        try:
            conn = get_connection()
            total_users = pd.read_sql("SELECT COUNT(*) as cnt FROM users", conn).iloc[0]["cnt"]
            total_preds = pd.read_sql("SELECT COUNT(*) as cnt FROM predictions", conn).iloc[0]["cnt"]
            placed_preds = pd.read_sql("SELECT COUNT(*) as cnt FROM predictions WHERE result=1", conn).iloc[0]["cnt"]
            recent_users = pd.read_sql("SELECT name, email, created_at FROM users ORDER BY id DESC LIMIT 10", conn)
            conn.close()

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("👥 Total Users",       int(total_users))
            s2.metric("🔮 Total Predictions", int(total_preds))
            s3.metric("✅ Placed",             int(placed_preds))
            s4.metric("📈 Placement Rate",     f"{placed_preds/max(total_preds,1)*100:.1f}%")

            st.markdown("---")
            st.subheader("🆕 Recent Registrations")
            if recent_users.empty:
                st.info("No users registered yet.")
            else:
                st.dataframe(recent_users, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"❌ Database error: {e}")
    st.title("🎓 About This App")
    st.write("This application uses machine learning to predict student placement outcomes.")
    st.info("Enter your details to get instant predictions and insights.")
    st.write("Built with ❤️ by the Student Placement Predictor Team.")
    st.write("Contact: jobsync@gmail.com")
    st.write("© 2026 Student Placement Predictor. All rights reserved.")
    st.image("placement_predictor.jpg", use_container_width=True)
    st.markdown(
        "<div style='text-align:center;color:gray;font-size:12px;'>"
        "Data Source: collegePlace.csv | Model: Random Forest Classifier | Accuracy ~85%"
        "</div>", unsafe_allow_html=True)

# ==========================================
# 13. ABOUT
# ==========================================
elif page == "About":
    st.title("🎓 About This App")
    st.write("This application uses machine learning to predict student placement outcomes.")
    st.info("Enter your details to get instant predictions and insights.")
    st.write("Built with ❤️ by the Student Placement Predictor Team.")
    st.write("Contact: jobsync@gmail.com")
    st.write("© 2026 Student Placement Predictor. All rights reserved.")
    st.image("placement_predictor.jpg", use_container_width=True)
    st.markdown(
        "<div style='text-align:center;color:gray;font-size:12px;'>"
        "Data Source: collegePlace.csv | Model: Random Forest Classifier | Accuracy ~85%"
        "</div>", unsafe_allow_html=True)
