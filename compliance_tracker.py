import streamlit as st
import pandas as pd
import sqlite3
from twilio.rest import Client
from datetime import datetime, timedelta

# Database connection
conn = sqlite3.connect("compliance_tracker.db")
cursor = conn.cursor()

# Twilio Credentials from Streamlit Secrets
TWILIO_ACCOUNT_SID = st.secrets["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]
TWILIO_PHONE_NUMBER = st.secrets["TWILIO_PHONE_NUMBER"]
RECIPIENT_PHONE_NUMBER = st.secrets["RECIPIENT_PHONE_NUMBER"]

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Function to send SMS
def send_sms(message):
    try:
        client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=RECIPIENT_PHONE_NUMBER,
        )
        st.success("SMS sent successfully!")
    except Exception as e:
        st.error(f"Failed to send SMS: {e}")

# Authentication system
USERNAME = "admin"
PASSWORD = "123"

def authenticate():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username == USERNAME and password == PASSWORD:
            st.session_state.logged_in = True
            st.sidebar.success("Login successful!")
        else:
            st.sidebar.error("Invalid credentials.")

# Compliance score
def calculate_compliance_score():
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    total_milestones = len(milestones)
    completed = milestones[milestones['status'] == "Completed"]
    return (len(completed) / total_milestones * 100) if total_milestones > 0 else 0

# Fetch overdue milestones
def check_overdue_milestones():
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    overdue = milestones[(milestones['due_date'] < datetime.now().strftime("%Y-%m-%d")) & (milestones['status'] != "Completed")]
    return overdue

# Fetch upcoming milestones
def get_upcoming_milestones():
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    current_date = datetime.now().strftime("%Y-%m-%d")
    upcoming = milestones[(milestones['due_date'] >= current_date) & 
                          (milestones['due_date'] <= (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")) & 
                          (milestones['status'] != "Completed")]
    return upcoming

# Dashboard for users
def user_dashboard():
    st.title("User Dashboard")
    st.subheader("Milestones Overview")
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    st.dataframe(milestones)
    
    st.subheader("Compliance Score")
    score = calculate_compliance_score()
    st.write(f"Compliance Score: {score:.2f}%")

# Add new milestone (Admin only)
def add_milestone():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        authenticate()
        return

    st.title("Add New Milestone")
    title = st.text_input("Milestone Title")
    due_date = st.date_input("Due Date")
    if st.button("Add Milestone"):
        cursor.execute("INSERT INTO milestones (title, due_date) VALUES (?, ?)", (title, due_date))
        conn.commit()
        st.success(f"Milestone '{title}' added successfully!")

# Send SMS notifications (Admin only)
def notifications():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        authenticate()
        return

    st.title("Send SMS Notifications")
    milestones = get_upcoming_milestones()

    if milestones.empty:
        st.write("No upcoming milestones!")
    else:
        st.dataframe(milestones)
        if st.button("Send Bulk SMS for Upcoming Milestones"):
            for _, milestone in milestones.iterrows():
                message = f"Reminder: Milestone '{milestone['title']}' is due on {milestone['due_date']}."
                send_sms(message)

# Navigation menu
def main():
    st.sidebar.title("Navigation")
    menu = ["Dashboard-user", "Add Milestone-admin", "Send SMS Notifications-admin"]
    choice = st.sidebar.radio("Menu", menu)

    if choice == "Dashboard-user":
        user_dashboard()
    elif choice == "Add Milestone-admin":
        add_milestone()
    elif choice == "Send SMS Notifications-admin":
        notifications()

if _name_ == "_main_":
    main()

