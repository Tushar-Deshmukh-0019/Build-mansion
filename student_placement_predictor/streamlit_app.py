import streamlit as st
import requests
import psycopg2
import pandas as pd
import os
import matplotlib.pyplot as plt
import base64
from streamlit_option_menu import option_menu
from dotenv import load_dotenv

# ==========================================
# 1. PAGE CONFIG
# ==========================================
st.set_page_config(page_title="Student Placement Predictor", layout="wide", page_icon="🎓")

# ==========================================
# 2. LOAD ENV
# ==========================================
load_dotenv()

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
        .stApp {{ background: #0f1116; }}
        .stApp::before {{
            content:""; background-image:{bg}; background-size:cover;
            background-position:center; background-attachment:fixed;
            opacity:0.15; position:absolute; top:0; left:0; width:100%; height:100%; z-index:-1;
        }}
        .stButton>button {{
            background:linear-gradient(90deg,#834d9b 0%,#d04ed6 100%);
            color:white; border:none; border-radius:10px; font-weight:bold; width:100%;
        }}
        .skill-item {{
            background:rgba(255,255,255,0.04); border-left:3px solid #6366F1;
            border-radius:8px; padding:10px 14px; margin:6px 0;
            font-size:14px; color:#e2e8f0;
        }}
        .section-label {{
            font-size:11px; text-transform:uppercase; letter-spacing:1.5px;
            color:#6366F1; font-weight:600; margin-bottom:8px;
        }}
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
# 4. DB CONNECTION
# ==========================================
def get_connection():
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:mypassword123@127.0.0.1:5432/placement_db_student"
    )
    return psycopg2.connect(db_url)

# ==========================================
# 5. SESSION STATE
# ==========================================
for k, v in {"logged_in": False, "user_id": "", "user_name": ""}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================================
# 6. LOGIN / REGISTER
# ==========================================
FLASK_URL = os.getenv("FLASK_API_URL", "http://127.0.0.1:5000")

if not st.session_state.logged_in:
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown("""
            <div style="text-align:center;margin-bottom:20px;">
                <div style="font-size:52px;">🎓</div>
                <h2 style="color:white;margin:4px 0;">Joblib</h2>
                <p style="color:#a0a0b0;font-size:14px;">Student Placement Predictor</p>
            </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔑 Sign In", "📝 Create Account"])

        # ---- SIGN IN ----
        with tab_login:
            with st.container(border=True):
                login_email = st.text_input("📧 Email", placeholder="you@example.com",
                                            key="login_email")
                login_pwd   = st.text_input("🔒 Password", placeholder="Your password",
                                            type="password", key="login_pwd")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Sign In →", use_container_width=True, key="btn_login"):
                    if not login_email or not login_pwd:
                        st.error("Please enter your email and password.")
                    else:
                        try:
                            r = requests.post(
                                f"{FLASK_URL}/login",
                                json={"email": login_email, "password": login_pwd},
                                timeout=10
                            )
                            d = r.json()
                            if "error" in d:
                                st.error(f"❌ {d['error']}")
                            else:
                                st.session_state.logged_in = True
                                st.session_state.user_id   = d["user_id"]
                                st.session_state.user_name = d["name"]
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Could not reach server: {e}")

        # ---- CREATE ACCOUNT ----
        with tab_register:
            with st.container(border=True):
                reg_name  = st.text_input("👤 Full Name",     placeholder="Your full name",
                                          key="reg_name")
                reg_email = st.text_input("📧 Email Address", placeholder="you@example.com",
                                          key="reg_email")
                reg_pwd   = st.text_input("🔒 Password",      placeholder="Min 6 characters",
                                          type="password", key="reg_pwd")
                reg_pwd2  = st.text_input("🔒 Confirm Password", placeholder="Repeat password",
                                          type="password", key="reg_pwd2")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Create Account →", use_container_width=True, key="btn_register"):
                    if not reg_name or not reg_email or not reg_pwd or not reg_pwd2:
                        st.error("All fields are required.")
                    elif reg_pwd != reg_pwd2:
                        st.error("❌ Passwords do not match.")
                    else:
                        try:
                            r = requests.post(
                                f"{FLASK_URL}/register",
                                json={"name": reg_name,
                                      "email": reg_email,
                                      "password": reg_pwd},
                                timeout=10
                            )
                            d = r.json()
                            if "error" in d:
                                st.error(f"❌ {d['error']}")
                            else:
                                st.success(f"✅ {d['message']} Please sign in.")
                        except Exception as e:
                            st.error(f"❌ Could not reach server: {e}")

        st.markdown(
            "<p style='text-align:center;color:#444;font-size:12px;margin-top:16px;'>"
            "© 2026 Joblib · Student Placement Predictor</p>",
            unsafe_allow_html=True
        )
    st.stop()

# ==========================================
# 7. NAVIGATION
# ==========================================
page = option_menu(
    menu_title=None,
    options=["Home","Career Tools","Live Dashboard","Student Help","About"],
    icons=["house","tools","bar-chart-line","question-circle","info-circle"],
    default_index=0, orientation="horizontal",
    styles={
        "container":{"padding":"0!important","background-color":"transparent"},
        "icon":{"color":"red","font-size":"18px"},
        "nav-link":{"font-size":"16px","text-align":"center","margin":"0px",
                    "color":"","border-bottom":"3px solid transparent"},
        "nav-link-selected":{"background-color":"transparent","color":"#6366F1",
                             "border-bottom":"3px solid #6366F1","font-weight":"bold"},
    }
)

if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.user_id   = ""
    st.session_state.user_name = ""
    st.rerun()

# ==========================================
# 8. HOME
# ==========================================
if page == "Home":
    name_display = st.session_state.get("user_name", "")
    st.title(f"Welcome back, {name_display}! 👋" if name_display else "Welcome back! 👋")
    st.header("🎓 Joblib: Student Placement Predictor")
    st.image("placement_predictor.jpg", use_container_width=True)

# ==========================================
# 9. CAREER TOOLS
# ==========================================
elif page == "Career Tools":

    st.markdown("""
        <style>
        .skill-item { background:rgba(255,255,255,0.04); border-left:3px solid #6366F1;
            border-radius:8px; padding:10px 14px; margin:6px 0; font-size:14px; color:#e2e8f0; }
        .section-label { font-size:11px; text-transform:uppercase; letter-spacing:1.5px;
            color:#6366F1; font-weight:600; margin-bottom:8px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color:white;margin-bottom:4px;'>🎯 Career Analysis Engine</h2>",
                unsafe_allow_html=True)
    st.markdown("<p style='color:#a0a0b0;margin-bottom:24px;'>Fill in your complete profile "
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
            payload = {
                "user_id":     st.session_state.user_id,
                "age":         int(age),
                "gender":      gender,
                "stream":      stream,
                "internships": int(internships),
                "cgpa":        float(cgpa),
                "backlog":     int(backlog),
                "projects":    int(projects),
                "hackathons":  int(hackathons),
            }
            with st.spinner("Analysing your profile..."):
                try:
                    resp = requests.post(
                        os.getenv("FLASK_API_URL", "http://127.0.0.1:5000") + "/predict",
                        json=payload, timeout=10
                    )
                    if resp.status_code == 200:
                        d = resp.json()
                        if "error" in d:
                            st.error(f"❌ API Error: {d['error']}")
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
                                st.balloons()
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
                    else:
                        st.error(f"❌ Server returned status {resp.status_code}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to Flask API on port 5000.")
                except requests.exceptions.Timeout:
                    st.error("❌ Request timed out.")
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
# 10. LIVE DASHBOARD
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
    st.title("❓ Help Center")
    st.write("Contact placement cell for support.")

# ==========================================
# 12. ABOUT
# ==========================================
elif page == "About":
    st.title("🎓 About This App")
    st.write("This application uses machine learning to predict student placement outcomes.")
    st.info("Enter your details to get instant predictions and insights.")
    st.write("Built with ❤️ by the Student Placement Predictor Team.")
    st.write("Contact: joblib@gmail.com")
    st.write("© 2026 Student Placement Predictor. All rights reserved.")
    st.image("placement_predictor.jpg", use_container_width=True)
    st.markdown(
        "<div style='text-align:center;color:gray;font-size:12px;'>"
        "Data Source: collegePlace.csv | Model: Random Forest Classifier | Accuracy ~85%"
        "</div>", unsafe_allow_html=True)
