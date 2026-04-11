import streamlit as st
import requests
import sqlite3
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Placement System", layout="wide")

# ---------------- DB CONNECTION ----------------
conn = sqlite3.connect("placement.db", check_same_thread=False)

# ---------------- UI ----------------
st.title("🎓 Joblib: student  placement pridiction ")

# ---------------- QR LOGIN ----------------
st.sidebar.header(" QR Login")

user_id = st.sidebar.text_input("Enter QR User ID (scan simulation)")

if not user_id:
    st.warning("Please login using QR ID to continue")
    st.stop()

# ---------------- MENU ----------------
page = st.sidebar.radio("Menu", ["Predict", "Dashboard"])

# ---------------- PREDICT PAGE ----------------
if page == "Predict":

    age = st.slider("Age", 18, 30)
    gender = st.selectbox("Gender", ["Male", "Female"])
    stream = st.selectbox("Stream", [
        "Computer Science",
        "IT",
        "Mechanical Engineering",
        "Civil Engineering",
        "Electrical Engineering"
    ])
    internships = st.slider("Internships", 0, 10)
    cgpa = st.slider("CGPA", 1, 10)
    backlog = st.radio("Backlog", ["No", "Yes"])

    backlog = 1 if backlog == "Yes" else 0

    if st.button("Predict"):

        payload = {
            "user_id": user_id,
            "age": age,
            "gender": gender,
            "stream": stream,
            "internships": internships,
            "cgpa": cgpa,
            "backlog": backlog
        }

        try:
            res = requests.post("http://127.0.0.1:5000/predict", json=payload)
            output = res.json()

            if "placement" in output:

                if output["placement"] == 1:
                    st.success("🎉 Student will be placed")
                else:
                    st.error("❌ Not likely to be placed")

                st.write("Confidence:", round(output["confidence"] * 100, 2), "%")

            else:
                st.error(output.get("error", "Unknown error"))

        except Exception:
            st.error("❌ Flask backend not running. Start flask_app.py first.")

# ---------------- DASHBOARD ----------------
elif page == "Dashboard":

    df = pd.read_sql("SELECT * FROM predictions", conn)

    st.subheader("📊 Live Dashboard")

    st.metric("Total Predictions", len(df))

    if len(df) > 0:

        col1, col2 = st.columns(2)

        with col1:
            fig1 = px.histogram(df, x="result", title="Placement Distribution")
            st.plotly_chart(fig1)

        with col2:
            fig2 = px.scatter(df, x="cgpa", y="confidence", color="result")
            st.plotly_chart(fig2)

        st.dataframe(df)