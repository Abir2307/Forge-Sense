import sqlite3
import hashlib

DB_FILE = "safetwin.db"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_admin(username, name, email, password, secret_code):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, name, email, password, secret_code, admin, verified) VALUES (?, ?, ?, ?, ?, 1, 1)",
            (username, name, email, hash_password(password), secret_code)
        )
        conn.commit()
        print(f"Admin user '{username}' added successfully.")
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # usage
    add_admin("admin", "Administrator", "admin@example.com", "admin123", "ADMIN123")