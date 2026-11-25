
import re
import sqlite3
import bcrypt

from src.config import DATABASE_PATH


def register_user(name: str, email: str, password: str):
    """Create a new user account with a securely hashed password."""

    name = name.strip()
    email = email.strip().lower()

    if not name:
        return False, "Name is required."

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "Please enter a valid email address."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    if len(password.encode("utf-8")) > 72:
        return False, "Password must not exceed 72 bytes."

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    try:
        with sqlite3.connect(str(DATABASE_PATH)) as conn:
            conn.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (name, email, password_hash)
            )

        return True, "Account created successfully."

    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."


def login_user(email: str, password: str):
    """Verify login credentials and return the user's details."""

    email = email.strip().lower()

    with sqlite3.connect(str(DATABASE_PATH)) as conn:
        conn.row_factory = sqlite3.Row

        user = conn.execute(
            """
            SELECT id, name, email, password_hash
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

    if user is None:
        return None

    if not bcrypt.checkpw(
        password.encode("utf-8"),
        user["password_hash"].encode("utf-8")
    ):
        return None

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
    }
