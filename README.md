# Compliance Tracker  

## Overview  
The **Compliance Tracker** is a web-based application designed to help organizations manage and track compliance milestones effectively. It allows users to add milestones, update their statuses, calculate compliance scores, identify overdue tasks, and send notifications (via SMS or WhatsApp) for important updates.  

This project was developed entirely on **Google Colab** with the help of **ngrok** for hosting and exposing the local Streamlit app to the web during the development phase.

---

## Features  
- **User Authentication**: Secure login system to access dashboard features.  
- **Dashboard**: View and manage compliance milestones in an interactive table.  
- **Add Milestones**: Add new milestones with due dates to the system.  
- **Update Status**: Update the status of existing milestones (Pending, Completed, Escalated).  
- **Compliance Score**: Calculates the compliance score as a percentage of completed milestones.  
- **Notifications**: Sends notifications (SMS/WhatsApp) for upcoming or overdue milestones.  
- **Escalation**: Automatically escalates overdue milestones by notifying stakeholders.  

---

## Tech Stack  
- **Frontend**: Streamlit  
- **Backend**: Python, SQLite  
- **Messaging Integration**: Twilio API  
- **Development Environment**: Google Colab with ngrok  
- **Deployment**: Streamlit Cloud  

---

## Setup Instructions  

### Prerequisites  
- Python 3.7 or higher  
- Twilio Account (for messaging functionality)  
- Google Colab (for development)  
- ngrok (for exposing local app)  
- Streamlit Account (for deployment)  

### Installation  
1. Clone the repository:  
   ```bash
   git clone https://github.com/your-username/compliance-tracker.git
   cd compliance-tracker

2. Install dependencies:  
   Run the following command to install all the required Python packages:
   ```bash
   pip install -r requirements.txt

### Set up the SQLite database:  
Create a database file named `compliance_tracker.db` and set up a `milestones` table to store the milestones:

```sql
CREATE TABLE milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT DEFAULT 'Pending'}



