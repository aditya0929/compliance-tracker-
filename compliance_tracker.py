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

        # Notify the user that the update was successful
        st.success(f"Milestone {milestone_id} updated to '{new_status}'!")

# Add or upload milestones in the admin section
def add_milestone():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        authenticate()
        return

    st.title("Add New Milestone (Admin Section)")

    # Form to add milestones manually
    with st.form("add_milestone_form"):
        title = st.text_input("Milestone Title")
        status = st.selectbox("Status", ["Pending", "Completed", "Escalated"])
        due_date = st.date_input("Due Date")
        submit = st.form_submit_button("Add Milestone")

        if submit:
            cursor.execute(
                "INSERT INTO milestones (title, status, due_date) VALUES (?, ?, ?)",
                (title, status, due_date),
            )
            conn.commit()
            st.success(f"Milestone '{title}' added successfully!")

    # Option to upload milestones via PDF
    st.subheader("Or Upload Milestones via PDF")
    uploaded_pdf = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_pdf:
        read_and_update_pdf(uploaded_pdf)

# Notifications feature for admins
def notifications():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        authenticate()
        return

    st.title("Send SMS Notifications")
    milestones = pd.read_sql_query("SELECT * FROM milestones WHERE status != 'Completed'", conn)
    st.dataframe(milestones)

    # Create a button for each pending milestone to send notification manually
    for idx, row in milestones.iterrows():
        message = f"Reminder: Milestone '{row['title']}' is due on {row['due_date']}."
        
        # Use the row index (or any unique attribute) as a key to avoid duplicate button IDs
        if st.button(f"Send Notification for '{row['title']}'", key=f"send_button_{row['id']}"):
            send_sms(message)

# Navigation
def main():
    st.sidebar.title("Navigation")
    menu = ["Dashboard", "Add Milestone (Admin)", "Send Notifications (Admin)"]
    choice = st.sidebar.radio("Go to", menu)

    if choice == "Dashboard":
        dashboard()
    elif choice == "Add Milestone (Admin)":
        add_milestone()
    elif choice == "Send Notifications (Admin)":
        notifications()

if __name__ == "__main__":
    main()
