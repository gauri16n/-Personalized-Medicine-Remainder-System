# -Personalized-Medicine-Remainder-System
# Medication Reminder Application

This is a full-stack Python application designed to help users remember to take their medications on time. It features a Flask backend, a PostgreSQL database, and a Tkinter GUI.

## Features

- User registration and login.
- Add and manage medication schedules.
- Daily view of medication timings.
- Mark doses as "taken".
- Automatic SMS and email reminders to the user if a dose is missed, plus an SMS alert to a designated close contact.

## Prerequisites

- **Python 3.6+**
- **PostgreSQL**: You need a running PostgreSQL server.
- **Git** (optional, for cloning)

## Setup Instructions

### 1. Set up the PostgreSQL Database

1.  Install PostgreSQL if you haven't already.
2.  Open the PostgreSQL command-line tool (`psql`) or a GUI tool like pgAdmin.
3.  Create a new database for the application.

    ```sql
    CREATE DATABASE med_reminder;
    ```

4.  Create a user and grant privileges (replace `'your_password'` with a secure password).

    ```sql
    CREATE USER postgres WITH PASSWORD 'your_password';
    GRANT ALL PRIVILEGES ON DATABASE med_reminder TO postgres;
    ```

### 2. Configure the Application

1.  Clone this repository or download the files into a directory named `medication-reminder-app`.

2.  **Create a `.env` file** in the root of the project directory (`medication-reminder-app/`) for your database credentials. This file is ignored by Git to keep your secrets safe.

    Create a file named `.env` and add the following content, replacing `'your_password'` with the password you set up in the previous step.

    ```.env
    DB_PASS='your_password'
    
    # You can also override other settings here if they differ from the defaults
    # DB_NAME='med_reminder'
    # DB_USER='postgres'
    # DB_HOST='localhost'
    # DB_PORT='5432'

    # --- Optional: Twilio Credentials for Real SMS Alerts ---
    # To enable sending real SMS alerts for missed doses, create a Twilio account
    # and add your credentials here. Otherwise, it will run in simulation mode.
    # TWILIO_ACCOUNT_SID='ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    # TWILIO_AUTH_TOKEN='your_auth_token'
    # TWILIO_PHONE_NUMBER='+15017122661'

    # --- Optional: Email (SMTP) Credentials for Real Email Alerts ---
    # To enable sending real email alerts for missed doses, provide your SMTP server
    # details here. For Gmail, you may need to create an "App Password".
    # SMTP_SERVER='smtp.gmail.com'
    # SMTP_PORT=587
    # SMTP_USER='your-email@gmail.com'
    # SMTP_PASS='your-gmail-app-password'
    ```

### 3. Install Dependencies

1.  Navigate to the project directory in your terminal and create/activate a virtual environment (recommended):

    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  Install the required Python packages:

    This project uses a `requirements.txt` file to manage all its dependencies. Install them with the following command:

    ```bash
    pip install -r requirements.txt
    ```

### 4. Initialize the Database Tables

Run the `init_db.py` script once to create all the necessary tables in your database.

```bash
python init_db.py
```

You should see the message "Tables created successfully!".

## How to Run the Application

You need to run the backend server and the frontend GUI in two separate terminal windows.

### Terminal 1: Start the Backend Server

1.  Make sure your virtual environment is activated.
2.  Run the Flask backend:

    ```bash
    python backend.py
    ```

    The server will start, and you'll see output indicating it's running on `http://127.0.0.1:5001`. Keep this terminal open.

    **Note**: The application is configured to run without Flask's auto-reloader (`use_reloader=False`). This is to prevent database connection leaks during development. You will need to manually stop (`Ctrl+C`) and restart the server to see any changes you make to the backend code.

### Terminal 2: Start the Frontend GUI

1.  Open a new terminal and navigate to the project directory.
2.  Make sure your virtual environment is activated in this terminal as well.
3.  Run the Tkinter GUI:

    ```bash
    python gui.py
    ```

The application window will appear. You can now register a new user, log in, and start adding medications. The application will automatically check for missed doses every minute and display alerts as needed.
