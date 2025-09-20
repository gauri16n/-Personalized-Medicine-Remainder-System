# /medication-reminder-app/backend.py
from flask import Flask, request, jsonify, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, release_db_connection
import psycopg2.extras
from datetime import datetime, timedelta, date
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
import os
from functools import wraps

app = Flask(__name__)
# A secret key is required for session management.
# It's best practice to load this from an environment variable.
# Generate a strong key with: python -c 'import secrets; print(secrets.token_hex(16))'
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a-default-secret-key-for-dev-only')

# --- Twilio Configuration ---
# IMPORTANT: To send real SMS, replace with your actual Twilio credentials.
# For better security, use environment variables in a real application.
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'your_auth_token')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '+15017122661') # Your Twilio number

# --- Email (SMTP) Configuration ---
SMTP_SERVER = os.environ.get('SMTP_SERVER')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587)) # 587 is common for TLS
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')

def send_sms(to_number, body):
    """Sends an SMS using Twilio. Includes a simulation mode."""
    if 'ACxxxxxxxx' in TWILIO_ACCOUNT_SID or 'your_auth_token' in TWILIO_AUTH_TOKEN:
        print("\n--- SMS SIMULATION ---")
        print(f"To: {to_number}\nBody: {body}")
        print("--- (To send real SMS, update Twilio credentials in your .env file) ---\n")
        return "simulated"
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(body=body, from_=TWILIO_PHONE_NUMBER, to=to_number)
        print(f"SMS sent to {to_number}. SID: {message.sid}")
        return message.sid
    except Exception as e:
        print(f"Error sending SMS to {to_number}: {e}")
        return None

def send_email(to_email, subject, body):
    """Sends an email using SMTP. Includes a simulation mode."""
    if not all([SMTP_SERVER, SMTP_USER, SMTP_PASS]):
        print("\n--- EMAIL SIMULATION ---")
        print(f"To: {to_email}\nSubject: {subject}\nBody: {body}")
        print("--- (To send real emails, update SMTP credentials in your .env file) ---\n")
        return "simulated"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls() # Secure the connection
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            print(f"Email sent successfully to {to_email}")
        return "sent"
    except Exception as e:
        print(f"Error sending email to {to_email}: {e}")
        return None


# --- Database Connection Handling for Flask App Context ---

def get_conn():
    """
    Opens a new database connection from the pool if there is none yet for
    the current application context `g`.
    """
    if 'db_conn' not in g:
        g.db_conn = get_db_connection()
    return g.db_conn

@app.teardown_appcontext
def teardown_db(exception):
    """
    Releases the database connection back to the pool at the end of the request.
    This function is registered with Flask to be called automatically.
    """
    db_conn = g.pop('db_conn', None)
    if db_conn is not None:
        release_db_connection(db_conn)

def with_db_cursor(f):
    """
    A decorator to provide a database cursor to a Flask route.
    It gets a connection from the Flask app context `g` and handles transactions.
    The connection itself is managed by the `teardown_db` function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                result = f(cur, *args, **kwargs)
                conn.commit()
                return result
        except (psycopg2.Error, ValueError, RuntimeError) as e:
            conn.rollback()
            print(f"Database Error in '{f.__name__}': {e}")
            # Return a generic error to the client for security
            return jsonify({"error": "A database error occurred. Please check server logs."}), 500
    return decorated_function

# --- Helper Functions ---
def generate_daily_doses(cur, user_id):
    """
    Ensures dose_history for the current day is populated for all of a user's medications.
    This function is idempotent: it only adds entries that are missing for the current day,
    making it safe to call multiple times (e.g., on login and after adding a new medication).
    """
    today = date.today()
    cur.execute("SELECT id, time_to_take FROM medications WHERE user_id = %s", (user_id,))
    medications = cur.fetchall()

    for med in medications:
        # Check if a dose for THIS specific medication already exists for today
        cur.execute(
            "SELECT 1 FROM dose_history WHERE medication_id = %s AND scheduled_for = %s",
            (med['id'], today)
        )
        if not cur.fetchone():
            # Insert if it doesn't exist
            cur.execute(
                "INSERT INTO dose_history (user_id, medication_id, scheduled_for, scheduled_time, status) VALUES (%s, %s, %s, %s, 'PENDING')",
                (user_id, med['id'], today, med['time_to_take'])
            )

# --- API Routes ---
@app.route("/api/register", methods=["POST"])
@with_db_cursor
def register(cur):
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    age_str = data.get("age")
    user_contact = data.get("user_contact")
    cc_name = data.get("cc_name")
    cc_contact = data.get("cc_contact")

    if not all([name, email, password, age_str, user_contact, cc_name, cc_contact]):
        return jsonify({"error": "All fields are required"}), 400

    # Validate that age is a number before inserting into the database.
    try:
        age = int(age_str)
    except (ValueError, TypeError):
        return jsonify({"error": "Age must be a valid number."}), 400

    cur.execute("SELECT id FROM users WHERE name=%s OR email=%s", (name, email))
    if cur.fetchone():
        return jsonify({"error": "Username or email already exists"}), 409

    hashed = generate_password_hash(password)
    cur.execute(
        "INSERT INTO users (name, email, age, contact, password_hash) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (name, email, age, user_contact, hashed), # Use the converted integer 'age'
    )
    user_id = cur.fetchone()["id"]

    # Insert into close_contacts table
    cur.execute(
        "INSERT INTO close_contacts (user_id, name, contact) VALUES (%s, %s, %s)",
        (user_id, cc_name, cc_contact)
    )

    return jsonify({"success": True, "message": "User registered successfully"}), 201

@app.route("/api/login", methods=["POST"])
@with_db_cursor
def login(cur):
    data = request.get_json()
    name, password = data.get("name"), data.get("password")

    cur.execute("SELECT * FROM users WHERE name=%s", (name,))
    user = cur.fetchone()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        generate_daily_doses(cur, user['id'])
        return jsonify({"success": True, "user_id": user["id"], "name": user["name"]})
    else:
        return jsonify({"error": "Invalid login"}), 401

@app.route("/api/add_medication", methods=["POST"])
@with_db_cursor
def add_medication(cur):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in. Please log in again."}), 401

    data = request.get_json()
    cur.execute(
        "INSERT INTO medications (user_id, medicine_name, dosage, time_to_take) VALUES (%s,%s,%s,%s)",
        (user_id, data['medicine_name'], data['dosage'], data['time']),
    )
    # Ensure today's schedule includes the newly added medication.
    generate_daily_doses(cur, user_id)
    return jsonify({"success": True, "message": "Medication added successfully"})

@app.route("/api/medications", methods=["GET"])
@with_db_cursor
def get_all_medications(cur):
    """Gets a list of all medications for the user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in. Please log in again."}), 401

    cur.execute("SELECT id, medicine_name, dosage, time_to_take FROM medications WHERE user_id = %s ORDER BY time_to_take", (user_id,))
    meds_raw = cur.fetchall()
    medications = [dict(row) for row in meds_raw]
    for med in medications:
        med['time_to_take'] = med['time_to_take'].strftime('%H:%M:%S')
    return jsonify({"success": True, "medications": medications})

@app.route("/api/delete_medication", methods=["POST"])
@with_db_cursor
def delete_medication(cur):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in. Please log in again."}), 401

    data = request.get_json()
    medication_id = data.get('medication_id')

    # The ON DELETE CASCADE in the database will also delete related dose_history records.
    cur.execute("DELETE FROM medications WHERE id = %s AND user_id = %s", (medication_id, user_id))
    if cur.rowcount == 0:
        return jsonify({"error": "Medication not found or you do not have permission to delete it."}), 404
    return jsonify({"success": True, "message": "Medication deleted successfully."})

@app.route("/api/schedule", methods=["GET"])
@with_db_cursor
def get_schedule(cur):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in. Please log in again."}), 401

    generate_daily_doses(cur, user_id)
    cur.execute(
        """
        SELECT dh.id as dose_id, m.medicine_name, m.dosage, dh.scheduled_time, dh.status
        FROM dose_history dh
        JOIN medications m ON dh.medication_id = m.id
        WHERE dh.user_id = %s AND dh.scheduled_for = %s
        ORDER BY dh.scheduled_time;
        """,
        (user_id, date.today())
    )
    schedule_raw = cur.fetchall()
    schedule = [dict(row) for row in schedule_raw]
    for item in schedule:
        item['scheduled_time'] = item['scheduled_time'].strftime('%H:%M:%S')
    return jsonify({"success": True, "schedule": schedule})

@app.route('/api/confirm_dose', methods=['POST'])
@with_db_cursor
def confirm_dose(cur):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in. Please log in again."}), 401

    data = request.get_json()
    dose_id = data.get('dose_id')
    cur.execute(
        "UPDATE dose_history SET status = 'TAKEN', updated_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s",
        (dose_id, user_id)
    )
    return jsonify({"success": True, "message": "Dose confirmed"})

@app.route('/api/check_missed_doses', methods=['GET'])
@with_db_cursor
def check_missed_doses(cur):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in. Please log in again."}), 401

    missed_alerts = []
    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
    # Fetch the user's contact info.
    # Use FOR UPDATE SKIP LOCKED to prevent deadlocks. This tells the database to select rows for updating,
    # but to skip any rows that are already locked by another transaction (e.g., a concurrent delete operation).
    # This makes the background check more robust.
    cur.execute(
        """
        SELECT dh.id, m.medicine_name, u.name as user_name, u.contact as user_contact, u.email as user_email,
               cc.name as cc_name, cc.contact as cc_contact
        FROM dose_history dh
        JOIN medications m ON dh.medication_id = m.id
        JOIN users u ON dh.user_id = u.id
        LEFT JOIN close_contacts cc ON dh.user_id = cc.user_id
        WHERE dh.user_id = %s AND dh.scheduled_for = %s AND dh.status = 'PENDING' AND dh.scheduled_time < %s
        FOR UPDATE SKIP LOCKED;
        """,
        (user_id, date.today(), ten_minutes_ago.time())
    )
    missed_doses = cur.fetchall()

    for dose in missed_doses:
        cur.execute("UPDATE dose_history SET status = 'MISSED' WHERE id = %s", (dose['id'],))
        patient_name = dose['user_name']

        # --- Send Notification to User ---
        user_email_subject = "Medication Reminder: Missed Dose"
        user_email_body = f"Hi {patient_name},\n\nThis is a reminder that you missed your dose for {dose['medicine_name']}.\n\nPlease take it as soon as possible.\n\n- MedReminder App"
        user_sms_body = f"MedReminder Alert: Hi {patient_name}, it looks like you missed your {dose['medicine_name']} dose. Please take it as soon as possible."
        send_sms(dose['user_contact'], user_sms_body)
        send_email(dose['user_email'], user_email_subject, user_email_body)

        # --- Send Notification to Close Contact ---
        if dose.get('cc_contact'):
            cc_sms_body = f"MedReminder Alert: {patient_name} has missed their {dose['medicine_name']} dose. Please check on them."
            send_sms(dose['cc_contact'], cc_sms_body)
            # We don't have email for close contact, so only SMS is sent.
            gui_alert_message = f"ALERT: Missed {dose['medicine_name']} dose. Sending reminders to you and your contact, {dose['cc_name']}."
        else:
            gui_alert_message = f"ALERT: Missed {dose['medicine_name']} dose. Sending reminders to you."

        missed_alerts.append(gui_alert_message)

    return jsonify({"success": True, "missed_alerts": missed_alerts})

if __name__ == "__main__":
    # IMPORTANT: use_reloader=False is crucial for development when using a database
    # connection pool. The Flask auto-reloader can cause connection leaks by not
    # properly closing the pool on restart. Disabling it makes the server stable,
    # but you will need to manually restart it after making code changes.
    app.run(debug=True, port=5001, use_reloader=False)
