import sqlite3
import pickle
import datetime
import os

class DatabaseManager:
    def __init__(self, db_path="attendance.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                embedding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create Attendance Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT CHECK(type IN ('IN', 'OUT')),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()
        conn.close()

    def add_user(self, name):
        """Register a new user (Name only). ID is auto-generated."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO users (name) VALUES (?)', (name,))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id

    def get_user_name(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM users WHERE id = ?', (user_id,))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else "Unknown"

    def get_users_dict(self):
        """Returns {id: name} mapping."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM users')
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in rows}

    def log_attendance(self, user_id, punch_type):
        """Log attendance (IN/OUT)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO attendance (user_id, type) VALUES (?, ?)', (user_id, punch_type))
        conn.commit()
        conn.close()

    def get_last_attendance(self, user_id):
        """Get the last punch type for a user to toggle state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT type, timestamp FROM attendance WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result # (type, timestamp) or None
