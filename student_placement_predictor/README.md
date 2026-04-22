---
title: Joblib Student Placement Predictor
emoji: 🎓
colorFrom: indigo
colorTo: purple
sdk: streamlit
sdk_version: 1.45.0
python_version: "3.11"
app_file: streamlit_app.py
pinned: false
license: mit
---

# 🎓 Joblib — Student Placement Predictor

An AI-powered web app that predicts engineering student placement outcomes using a trained Random Forest model, with a personalised AI Career Mentor powered by Groq (Llama 3.3 70B).

## Features

- **Placement Prediction** — ML model trained on real placement data (CGPA, stream, internships, projects, hackathons, backlogs)
- **AI Career Mentor** — Chat with an AI mentor that knows your profile and gives personalised advice
- **Live Dashboard** — Real-time analytics across all predictions
- **Email OTP Auth** — Secure login via one-time passwords sent to your inbox
- **Student Help** — Submit support queries, get admin replies
- **Admin Portal** — Manage queries and view platform stats

## Environment Variables (set in HF Spaces Secrets)

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (e.g. from [Neon](https://neon.tech)) |
| `GROK_API_KEY` | Groq API key from [console.groq.com](https://console.groq.com/keys) |
| `SMTP_USER` | Gmail address for sending OTP emails |
| `SMTP_PASS` | Gmail App Password (not your regular password) |
| `ADMIN_SECRET` | Secret key for the Admin Portal |

## Getting a Free PostgreSQL Database

1. Sign up at [neon.tech](https://neon.tech) — free, no credit card
2. Create a project → copy the connection string
3. Add it as `DATABASE_URL` in HF Spaces Secrets

## Tech Stack

- **Frontend**: Streamlit
- **ML Model**: Random Forest (scikit-learn)
- **Database**: PostgreSQL (Neon)
- **AI Mentor**: Groq API (Llama 3.3 70B)
- **Auth**: Email OTP via Gmail SMTP
