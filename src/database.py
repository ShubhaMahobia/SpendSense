import sqlite3

DB_PATH = "expenses.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            transaction_type TEXT,
            merchant  TEXT,
            category TEXT,
            sub_category TEXT,
            additional_notes TEXT,
            timestamp TEXT,
            created_at TEXT,
            updated_at TEXT,
            is_deleted BOOLEAN
        )
        
        """)

        cursor.execute("""
         CREATE TABLE IF NOT EXISTS hashed_tranxn (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hashed_string TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """)

        conn.commit()

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")