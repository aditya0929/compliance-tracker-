
import streamlit as st
import pandas as pd
import sqlite3
from twilio.rest import Client
from datetime import datetime, timedelta

conn = sqlite3.connect("compliance_tracker.db")

cursor = conn.cursor()


TWILIO_ACCOUNT_SID = st.secrets["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]
TWILIO_PHONE_NUMBER = st.secrets["TWILIO_PHONE_NUMBER"]
RECIPIENT_PHONE_NUMBER = st.secrets["RECIPIENT_PHONE_NUMBER"]

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Notifications section
def notifications():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        authenticate()  # Prompt for login if not logged in
        return  # Stop the execution of notifications if not logged in

    st.title("Send SMS Notifications")

    # Pre-fill phone number from session state
    admin_phone_number = st.text_input(
        "Specify Phone Number to send alert with country code (eg - +9153833541)",
        key="admin_phone_number",
        value=st.session_state.get("user_phone_number", "")
    )

    if admin_phone_number:
        st.session_state["user_phone_number"] = admin_phone_number

    if not admin_phone_number:
        st.warning("Please enter a valid phone number.")
        return

    # Fetch upcoming milestones from the database
    upcoming_milestones = get_upcoming_milestones()
    if not upcoming_milestones:
        st.write("No upcoming milestones to notify!")
    else:
        st.write("Upcoming Milestones for Notification:")

        # Convert the list of milestones into a DataFrame
        upcoming_milestones_df = pd.DataFrame(
            upcoming_milestones,
            columns=["serial number", "id", "title", "status", "due_date"]
        )
        st.dataframe(upcoming_milestones_df)

        # Send SMS for upcoming milestones
        for _, milestone in upcoming_milestones_df.iterrows():
            button_key = f"send_sms_button_{milestone['id']}"
            if st.button(f"Send SMS for '{milestone['title']}'", key=button_key):
                due_date = (
                    milestone["due_date"].strftime("%Y-%m-%d")
                    if isinstance(milestone["due_date"], datetime)
                    else milestone["due_date"]
                )
                message = (
                    f"Reminder: Milestone '{milestone['title']}' is due on {due_date}.\n"
                    f"Current Status: {milestone['status']}."
                )
                send_sms(message, admin_phone_number)

def send_sms(message, phone_number):
    try:
        client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        st.success("SMS sent successfully!")
    except Exception as e:
        st.error(f"Failed to send SMS: {e}")


# Simple authentication credentials
USERNAME = "admin"  # Change to your desired username
PASSWORD = "123"  # Change to your desired password

# Function to check the credentials
def check_credentials(username, password):
    return username == USERNAME and password == PASSWORD

# Authentication form
def authenticate():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Login"):
        if check_credentials(username, password):
            st.session_state.logged_in = True
            st.sidebar.success("Login successful!")
        else:
            st.session_state.logged_in = False
            st.sidebar.error("Invalid credentials, please try again.")

# Function to calculate compliance score
def calculate_compliance_score():
    # This is a simple scoring system, you can customize it
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    total_milestones = len(milestones)
    completed_milestones = len([m for m in milestones['status'] if m == "Completed"])
    
    # Compliance score is percentage of completed milestones
    score = (completed_milestones / total_milestones) * 100 if total_milestones > 0 else 0
    return score

# Function to check for overdue milestones
def check_overdue_milestones():
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    overdue_milestones = []
    current_date = datetime.now().date()
    
    for milestone in milestones.itertuples():
        due_date = datetime.strptime(milestone.due_date, "%Y-%m-%d").date()
        if due_date < current_date and milestone.status != "Completed":
            overdue_milestones.append(milestone)
    
    return overdue_milestones

def get_upcoming_milestones():
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    upcoming_milestones = []
    current_date = datetime.now().date()
    
    for milestone in milestones.itertuples():
        due_date = datetime.strptime(milestone.due_date, "%Y-%m-%d").date()
        if current_date <= due_date <= (current_date + timedelta(days=7)) and milestone.status != "Completed":
            upcoming_milestones.append(milestone)
    
    return upcoming_milestones



# Function to escalate non-compliant milestones
def escalate_milestones():
    overdue_milestones = check_overdue_milestones()
    for milestone in overdue_milestones:
        message = f"Escalation Alert: Milestone '{milestone.title}' is overdue and non-compliant."
        send_sms(message)

def dashboard():
    st.title("Compliance Tracker Dashboard")
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    st.dataframe(milestones)

    # Capture phone number and store it in session state
    st.subheader("Enter Your Phone Number to get update status with country code (eg - +91856783782)")
    phone_number = st.text_input(
        "Phone Number",
        key="user_phone_number",  # Key ties this input to `st.session_state`
        value=st.session_state.get("user_phone_number", "")  # Use session state as default value
    )

    # Update Status Form
    st.subheader("Update Milestone Status")
    milestone_id = st.number_input("Milestone ID", min_value=1, step=1)
    new_status = st.selectbox("New Status", ["Pending", "Completed", "Escalated"])
    if st.button("Update Status"):
        cursor.execute("UPDATE milestones SET status=? WHERE id=?", (new_status, milestone_id))
        conn.commit()
        milestone = cursor.execute("SELECT title FROM milestones WHERE id=?", (milestone_id,)).fetchone()
        if milestone:
            send_sms(f"Milestone '{milestone[0]}' updated to '{new_status}'.", phone_number)
        st.success(f"Milestone {milestone_id} updated to {new_status}!")

    # Display compliance score
    st.subheader("Compliance Score")
    score = calculate_compliance_score()
    st.write(f"Compliance Score: {score}%")



# Add New Milestone
def add_milestone():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        authenticate()  # Prompt for login if not logged in
        return  # Stop the execution of add_milestone if not logged in

    st.title("Add New Milestone")
    title = st.text_input("Milestone Title")
    due_date = st.date_input("Due Date")
    if st.button("Add Milestone"):
        cursor.execute("INSERT INTO milestones (title, due_date) VALUES (?, ?)", (title, due_date))
        conn.commit()
        st.success(f"Milestone '{title}' added successfully!")

# Navigation
def main():
    st.sidebar.title("Navigation")
    menu = ["Dashboard-user", "Add Milestone-admin", "Send SMS Notifications-admin"]
    choice = st.sidebar.radio("Go to", menu)

    if choice == "Dashboard-user":
        dashboard()
    elif choice == "Add Milestone-admin":
        add_milestone()
    elif choice == "Send SMS Notifications-admin":
        notifications()

if __name__ == "__main__":
    main()


