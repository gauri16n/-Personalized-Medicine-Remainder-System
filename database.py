# /medication-reminder-app/database.py
import psycopg2
import psycopg2.pool
import os
import atexit
from dotenv import load_dotenv


# Load environment variables from a .env file
load_dotenv()

# --- Database connection details are now loaded from environment variables ---
DB_NAME = os.getenv("DB_NAME", "med_reminder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")  # It's crucial to set this in your .env file
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

if not DB_PASS:
    raise ValueError(
        "❌ Error: DB_PASS environment variable not set. "
        "Please create a .env file with your database credentials (see README.md)."
    )

try:
    # Use ThreadedConnectionPool because the Flask dev server is multi-threaded by default.
    # This prevents race conditions when multiple requests try to access the pool simultaneously.
    pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,  # A reasonable number for a small application
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
except psycopg2.OperationalError as e:
    print(f"❌ FATAL: Could not initialize database connection pool: {e}")
    pool = None # Ensure pool is None if initialization fails

def _close_pool():
    """Closes all connections in the pool. Registered to run on program exit."""
    if pool:
        pool.closeall()
        print("Database connection pool closed.")

if pool:
    atexit.register(_close_pool)

def get_db_connection():
    """
    Gets a connection from the pool.
    """
    if pool is None:
        raise RuntimeError("Database connection pool is not available.")
    return pool.getconn()

def release_db_connection(conn):
    """
    Returns a connection to the pool.
    """
    if pool:
        pool.putconn(conn)
