import streamlit as st
import requests
import psycopg2
import pandas as pd
import random
import matplotlib.pyplot as plt
import base64
from streamlit_option_menu import option_menu

# ==========================================
# 1. PAGE CONFIGURATION (MUST BE FIRST)
# ==========================================
st.set_page_config(
    page_title="Student Placement Predictor",
    layout="wide",
    page_icon="🎓"
)

# ==========================================
# 2. UI STYLING & BACKGROUND
# ==========================================
def set_design():
    try:
        with open("placement_predictor.jpg", "rb") as f:
            img_data = f.read()
        b64_encoded = base64.b64encode(img_data).decode()
        bg_style = f'url("data:image/jpg;base64,{b64_encoded}")'
    except:
        bg_style = "none"

    style = f"""
        <style>
        .stApp {{ background: #0f1116; }}
        .stApp::before {{
            content: "";
            background-image: {bg_style};
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            opacity: 0.15; 
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
        }}
        [data-testid="stVerticalBlock"] > div:has(div.stMetric), 
        .stForm, [data-testid="stHeader"], .stExpander, .stTabs {{
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(12px);
            border-radius: 20px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .stButton>button {{
            background: linear-gradient(90deg, #834d9b 0%, #d04ed6 100%);
            color: white; border: none; border-radius: 10px; font-weight: bold; width: 100%;
        }}
        </style>
    """
    st.markdown(style, unsafe_allow_html=True)

    # Logo
    try:
        with open("logo.png", "rb") as f:
            logo_data = f.read()
        logo_b64 = base64.b64encode(logo_data).decode()
        st.markdown(f'<img src="data:image/png;base64,{logo_b64}" style="position: fixed; top: 10px; left: 20px; width: 80px; z-index: 1001;">', unsafe_allow_html=True)
    except:
        pass

set_design()

# ==========================================
# 3. DATABASE CONNECTION
# ==========================================
def get_connection():
    return psycopg2.connect(
        host="127.0.0.1",
        database="placement_db_student",
        user="postgres",
        password="mypassword123",
        port="5432"
    )

# ==========================================
# 4. SESSION STATE & LOGIN
# ==========================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "otp_sent" not in st.session_state: st.session_state.otp_sent = False
if "otp" not in st.session_state: st.session_state.otp = ""
if "user_id" not in st.session_state: st.session_state.user_id = ""

if not st.session_state.logged_in:
    st.title("🔐 Secure Student Login")
    with st.container():
        mobile = st.text_input("Mobile Number", placeholder="Enter 10-digit number", disabled=st.session_state.otp_sent)
        if not st.session_state.otp_sent:
            if st.button("Send OTP"):
                if len(mobile) >= 10:
                    st.session_state.otp = str(random.randint(1000, 9999))
                    st.session_state.otp_sent = True
                    st.session_state.user_id = mobile
                    st.rerun()
                else: st.error("Please enter a valid 10-digit number.")
        else:
            st.info(f"✨ Demo Mode: Your Login OTP is **{st.session_state.otp}**")
            entered_otp = st.text_input("Enter 4-Digit OTP")
            c1, c2 = st.columns(2)
            if c1.button("Verify & Login"):
                if entered_otp == st.session_state.otp:
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("Incorrect OTP.")
            if c2.button("Edit Number"):
                st.session_state.otp_sent = False
                st.rerun()
    st.stop()

from streamlit_option_menu import option_menu

# ==========================================
# 5. MAIN NAVIGATION (TOP HORIZONTAL)
# ==========================================

# Use option_menu to create the horizontal bar
page = option_menu(
    menu_title=None, # No title needed for top bar
    options=["Home", "Career Tools", "Opportunities", "Student Help", "About"], 
    icons=['house', 'tools', 'briefcase', 'question-circle', 'info-circle'], 
    menu_icon="cast", 
    default_index=0, 
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        "icon": {"color": "white", "font-size": "18px"}, 
        "nav-link": {
            "font-size": "16px", 
            "text-align": "center", 
            "margin": "0px", 
            "color": "white",
            "border-bottom": "3px solid transparent" # Default no underline
        },
        "nav-link-selected": {
            "background-color": "transparent", # No box background
            "color": "#6366F1", # Your Purple color from the image
            "border-bottom": "3px solid #6366F1", # THE PURPLE UNDERLINE
            "font-weight": "bold"
        },
    }
)

# Small Logout button in the sidebar since the top is now full
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# ==========================================
# 6. PAGE LOGIC (Update names to match options)
# ==========================================
if page == "Home":
    st.title("")
    # ... home code ...

elif page == "Career Tools": # This was "Predict"
    st.title(" Placement Analysis")
    # ... predict code ...

elif page == "Opportunities": # This was "Dashboard"
    st.title("📊 Placement Dashboard")
    # ... dashboard code ...

elif page == "Student Help":
    st.write("How can we help you today?")

elif page == "About":
    st.title("ℹ️ About This Project")


# ==========================================
# 6. PAGE LOGIC
# ==========================================
if page == "Home":
    st.title("Welcome back, Admin!")
    st.header("🎓 Joblib: Student Placement Predictor")
    st.image("placement_predictor.jpg", use_container_width=True)

elif page == "Career Tools":
    st.title("🎯 Placement Analysis")
    l_col, r_col = st.columns([1.2, 1], gap="large")

    with l_col:
        st.subheader("📋 Profile Input")
        with st.container(border=True):
            cgpa = st.slider("Current CGPA", 0.0, 10.0, 7.5, step=0.1)
            internships = st.select_slider("Total Internships", options=[0, 1, 2, 3, 4, 5])
            stream = st.selectbox("Stream", ["Computer Science", "IT", "Mechanical Engineering", "Civil Engineering", "Electrical Engineering"])
            age = st.number_input("Age", 18, 30, 21)
            gender = st.selectbox("Gender", ["Male", "Female"])
            backlog = 1 if st.toggle("Active Backlogs?") else 0
            analyze_btn = st.button("RUN ANALYSIS NOW")
elif page == "Dashboard":
    st.title("📈 Global Analytics")
    try:
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM predictions", conn)
        conn.close()
        st.metric("Total Predictions Saved", len(df))
        if not df.empty:
            c1, c2 = st.columns(2)
            fig1, ax1 = plt.subplots(facecolor='none')
            df['result'].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax1, colors=['#00d2ff', '#ff4b4b'])
            ax1.set_title("Success Rate", color="white")
            c1.pyplot(fig1)
            
            fig2, ax2 = plt.subplots(facecolor='none')
            ax2.scatter(df['cgpa'], df['confidence'], color='#00d2ff', alpha=0.5)
            ax2.set_xlabel("CGPA", color="white")
            ax2.set_ylabel("Confidence", color="white")
            ax2.set_title("CGPA vs Confidence", color="white")
            ax2.tick_params(colors='white')
            c2.pyplot(fig2)
            
            st.dataframe(df.tail(10), use_container_width=True)
    except Exception as e: 
        st.error(f"Database error: {e}")



elif page == "Opportunities":
    st.title("📈 Global Analytics")
    try:
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM predictions", conn)
        conn.close()
        st.metric("Total Predictions Saved", len(df))
        st.dataframe(df.tail(10), use_container_width=True)
    except: st.error("Database connection failed.")

elif page == "Student Help":
    st.title("❓ Help Center")
    st.write("Contact placement cell for support.")

elif page == "About":
    st.title("🎓 About This App ")
    st.write("This application uses machine learning to predict student placement outcomes based on academic performance and other factors..")
    st.info("Enter your details to get instant predictions and insights that can help you prepare better for placements.")
    st.write("Built with ❤️ by the Student Placement Predictor Team.")
    st.write("For any queries or feedback, please contact us at joblib@gmail.com")
    st.info("This is a demo application. The predictions are based on a trained model and should be used for informational purposes only.")
    st.write("© 2026 Student Placement Predictor. All rights reserved.")
    st.image("placement_predictor.jpg", use_container_width=True)
    st.markdown("<div style='text-align: center; color: gray; font-size: 12px;'>Data Source: collegePlace.csv | Model: Random Forest Classifier</div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; color: gray; font-size: 12px;'>Note: The model's accuracy is around 85% based on the test set. Always use predictions as a guide, not a guarantee.</div>", unsafe_allow_html=True)
    
   
