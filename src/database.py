import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
import os


db_name = os.getenv("dbname")
user = os.getenv("user")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")

def get_connection():
    return psycopg2.connect(
        dbname=db_name,
        user=user,
        password=password,
        host=host,
        port=port,
        cursor_factory=RealDictCursor
    )


def execute_query(query, params=None, fetch=False):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(query, params)

    data = None
    if fetch:
        data = cursor.fetchall()

    conn.commit()
    cursor.close()
    conn.close()

    return data


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id SERIAL PRIMARY KEY,
        amount NUMERIC,
        transaction_type TEXT,
        merchant TEXT,
        category TEXT,
        sub_category TEXT,
        additional_notes TEXT,
        timestamp TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_deleted BOOLEAN DEFAULT FALSE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hashed_tranxn (
        id SERIAL PRIMARY KEY,
        hashed_string TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("PostgreSQL Database initialized successfully.")