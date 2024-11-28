import streamlit as st
import pandas as pd
import sqlite3
from twilio.rest import Client
from datetime import datetime
import pypdf  # Use pypdf for PDF extraction

# SQLite database connection
conn = sqlite3.connect('compliance_tracker.db')  # Adjust the path if needed
cursor = conn.cursor()

# Fetching Twilio Credentials from Streamlit secrets
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
            to=RECIPIENT_PHONE_NUMBER
        )
        st.success("SMS sent successfully!")
    except Exception as e:
        st.error(f"Failed to send SMS: {e}")

# Simple authentication credentials
USERNAME = "admin"  # Change to your desired username
PASSWORD = "123"  # Change to your desired password

# Authentication form
def authenticate():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Login"):
        if username == USERNAME and password == PASSWORD:
            st.session_state.logged_in = True
            st.sidebar.success("Login successful!")
        else:
            st.session_state.logged_in = False
            st.sidebar.error("Invalid credentials!")

# Function to calculate compliance score
def calculate_compliance_score():
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    total_milestones = len(milestones)
    completed_milestones = len(milestones[milestones['status'] == "Completed"])
    return (completed_milestones / total_milestones) * 100 if total_milestones > 0 else 0

# Function to check for overdue milestones
def check_overdue_milestones():
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    overdue = milestones[(milestones['due_date'] < datetime.now().strftime('%Y-%m-%d')) & (milestones['status'] != "Completed")]
    return overdue

# Function to read and update milestones from a PDF
def read_and_update_pdf(pdf_file):
    reader = pypdf.PdfReader(pdf_file)
    data = []

    for page in reader.pages:
        lines = page.extract_text().split('/n')
        for line in lines:
            if "id" not in line.lower():
                parts = line.split()
                if len(parts) >= 4:
                    title = " ".join(parts[1:-2])
                    status = parts[-2]
                    due_date = parts[-1]
                    data.append((title, status, due_date))

    for title, status, due_date in data:
        cursor.execute("SELECT MAX(id) FROM milestones")
        max_id = cursor.fetchone()[0]
        new_id = 1 if max_id is None else max_id + 1
        cursor.execute(
            "INSERT INTO milestones (id, title, status, due_date) VALUES (?, ?, ?, ?)",
            (new_id, title, status, due_date),
        )
    conn.commit()
    st.success("PDF milestones added successfully!")

# Dashboard to view milestones and compliance score
def dashboard():
    st.title("Compliance Tracker Dashboard")
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    st.dataframe(milestones)

    st.subheader("Compliance Score")
    score = calculate_compliance_score()
    st.write(f"Compliance Score: {score}%")

    # Option to update status of milestones
    st.subheader("Update Milestone Status")
    milestone_id = st.number_input("Milestone ID", min_value=1, step=1)
    new_status = st.selectbox("New Status", ["Pending", "Completed", "Escalated"])

    if st.button("Update Status"):
        cursor.execute("UPDATE milestones SET status=? WHERE id=?", (new_status, milestone_id))
        conn.commit()

        # Fetch the milestone title for the SMS message
        milestone = cursor.execute("SELECT title FROM milestones WHERE id=?", (milestone_id,)).fetchone()

        if milestone:
            milestone_title = milestone[0]
            message = f"Milestone '{milestone_title}' has been updated to '{new_status}'."
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

# Function to add new milestones
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

# Notifications section
def notifications():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        authenticate()  # Prompt for login if not logged in
        return  # Stop the execution of notifications if not logged in

    st.title("Send SMS Notifications")

    # Pre-fill phone number from session state
    admin_phone_number = st.text_input(
        "Specify Phone Number to send alert with country code (eg - +919153831641)",
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
                send_sms(message)

# Get upcoming milestones
def get_upcoming_milestones():
    milestones = pd.read_sql_query("SELECT * FROM milestones", conn)
    upcoming_milestones = []
    current_date = datetime.now().date()
    
    for milestone in milestones.itertuples():
        due_date = datetime.strptime(milestone.due_date, "%Y-%m-%d").date()
        if current_date <= due_date <= (current_date + timedelta(days=7)) and milestone.status != "Completed":
            upcoming_milestones.append(milestone)
    
    return upcoming_milestones

if __name__ == "__main__":
    main()
