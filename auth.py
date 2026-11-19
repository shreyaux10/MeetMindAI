
import sqlite3

from flask_login import UserMixin


# =====================================
# DATABASE CONFIGURATION
# =====================================

DATABASE = "meetmind.db"


# =====================================
# USER MODEL
# =====================================

class User(UserMixin):

    def __init__(self, id, name, email, password_hash):

        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash


# =====================================
# GET DATABASE CONNECTION
# =====================================

def get_auth_db():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# =====================================
# INITIALIZE AUTHENTICATION DATABASE
# =====================================

def init_auth_db():

    with get_auth_db() as db:

        # Create users table

        db.execute("""
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                email TEXT NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                created_at TEXT NOT NULL

            )
        """)

        # Check existing meetings table columns

        columns = db.execute(
            "PRAGMA table_info(meetings)"
        ).fetchall()

        column_names = [
            column["name"] for column in columns
        ]

        # Add user_id without deleting existing meetings

        if columns and "user_id" not in column_names:

            db.execute("""
                ALTER TABLE meetings
                ADD COLUMN user_id INTEGER
            """)

    print("Authentication database initialized!")


# =====================================
# FIND USER BY ID
# =====================================

def get_user_by_id(user_id):

    with get_auth_db() as db:

        row = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

    if row is None:
        return None

    return User(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        password_hash=row["password_hash"]
    )


# =====================================
# FIND USER BY EMAIL
# =====================================

def get_user_by_email(email):

    with get_auth_db() as db:

        row = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

    if row is None:
        return None

    return User(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        password_hash=row["password_hash"]
    )
