
import streamlit as st
import pandas as pd
import sqlite3
from twilio.rest import Client
from datetime import datetime, timedelta

# SQLite database connection
conn = sqlite3.connect('/content/compliance_tracker.db')
cursor = conn.cursor()

# Twilio Credentials (Use your own credentials)
TWILIO_ACCOUNT_SID = "AC3d0179d31bda1e4dde5e4eaa9de9edea"  # Replace with your Twilio SID
TWILIO_AUTH_TOKEN = "3c613bee5dee896ea708f5170c5b744c"  # Replace with your Twilio Auth Token
TWILIO_PHONE_NUMBER = "+15865018392"  # Replace with your Twilio phone number
recipient_phone_number = "+919153831641"  # Replace with the recipient's phone number

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Function to send SMS
def send_sms(message):
    try:
        client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=recipient_phone_number
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

# Dashboard for viewing milestones and updating status
def dashboard():
    st.title("Compliance Tracker Dashboard")
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    st.dataframe(milestones)

    # Update Status Form
    st.subheader("Update Milestone Status")
    milestone_id = st.number_input("Milestone ID", min_value=1, step=1)
    new_status = st.selectbox("New Status", ["Pending", "Completed", "Escalated"])
    if st.button("Update Status"):
        cursor.execute("UPDATE milestones SET status=? WHERE id=?", (new_status, milestone_id))
        conn.commit()
        milestone = cursor.execute("SELECT title FROM milestones WHERE id=?", (milestone_id,)).fetchone()
        if milestone:
            send_sms(f"Milestone '{milestone[0]}' updated to '{new_status}'.")
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

# Send SMS Notifications
def notifications():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        authenticate()  # Prompt for login if not logged in
        return  # Stop the execution of notifications if not logged in

    st.title("Send SMS Notifications")

    # Fetch upcoming milestones from the database
    upcoming_milestones = get_upcoming_milestones()
    if not upcoming_milestones:
        st.write("No upcoming milestones to notify!")
    else:
        st.write("Upcoming Milestones for Notification:")

        # Convert the list of milestones into a DataFrame
        upcoming_milestones_df = pd.DataFrame(upcoming_milestones, columns=['id', 'title', 'status', 'due_date', 'escalated'])
        st.dataframe(upcoming_milestones_df)

        # Send SMS for upcoming milestones
        for _, milestone in upcoming_milestones_df.iterrows():
            # Use the 'id' column to generate a unique key for each button
            button_key = f"send_sms_button_{milestone['id']}"
            if st.button(f"Send SMS for '{milestone['title']}'", key=button_key):
                message = f"Reminder: Milestone '{milestone['title']}' is due on {milestone['due_date']} and is currently '{milestone['status']}'."
                send_sms(message)

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

