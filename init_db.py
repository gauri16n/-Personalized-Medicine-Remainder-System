# /medication-reminder-app/init_db.py
import psycopg2
from database import get_db_connection, release_db_connection

def create_tables():
    """Create tables in PostgreSQL."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    age INT,
                    contact VARCHAR(50),
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Close contacts
            cur.execute("""
                CREATE TABLE IF NOT EXISTS close_contacts (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    contact VARCHAR(50) NOT NULL
                );
            """)

            # Medications
            cur.execute("""
                CREATE TABLE IF NOT EXISTS medications (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id) ON DELETE CASCADE,
                    medicine_name VARCHAR(100) NOT NULL,
                    dosage VARCHAR(100),
                    time_to_take TIME NOT NULL
                );
            """)

            # Dose history
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dose_history (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id) ON DELETE CASCADE,
                    medication_id INT REFERENCES medications(id) ON DELETE CASCADE,
                    scheduled_for DATE NOT NULL,
                    scheduled_time TIME NOT NULL,
                    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, TAKEN, MISSED
                    updated_at TIMESTAMP
                );
            """)

            # Add indexes for performance and to prevent table-locking on deletes/updates.
            # This is crucial for preventing deadlocks during concurrent operations.
            cur.execute("CREATE INDEX IF NOT EXISTS idx_dose_history_medication_id ON dose_history (medication_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_dose_history_user_date ON dose_history (user_id, scheduled_for);")

            conn.commit()
            print("✅ Tables and indexes created successfully!")

    except (psycopg2.Error, ValueError, RuntimeError) as e:
        # Catch database errors from psycopg2 or ValueErrors from our connection logic
        if conn:
            conn.rollback()
        print(f"❌ Error during database initialization: {e}")
    finally:
        if conn:
            release_db_connection(conn)

if __name__ == "__main__":
    create_tables()
