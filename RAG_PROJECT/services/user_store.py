"""SQLite-backed user store using the stdlib sqlite3 module — no extra ORM needed."""
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from utils.security import hash_password, verify_password

DB_PATH = Path(__file__).parent.parent / "data" / "users.db"


@dataclass
class User:
    user_id: str
    username: str
    hashed_password: str
    role: str          # "admin" | "user"
    created_at: float
    is_active: bool


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id      TEXT PRIMARY KEY,
                username     TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role         TEXT NOT NULL DEFAULT 'user',
                created_at   REAL NOT NULL,
                is_active    INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.commit()
        # Seed a default admin if none exists
        row = conn.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1").fetchone()
        if not row:
            _create_user_internal(conn, "admin", "Admin@123456", "admin")


def _create_user_internal(conn: sqlite3.Connection, username: str, password: str, role: str) -> User:
    uid = str(uuid.uuid4())
    now = time.time()
    hashed = hash_password(password)
    conn.execute(
        "INSERT INTO users (user_id, username, hashed_password, role, created_at, is_active) VALUES (?,?,?,?,?,1)",
        (uid, username, hashed, role, now),
    )
    conn.commit()
    return User(uid, username, hashed, role, now, True)


def create_user(username: str, password: str, role: str = "user") -> User:
    with _get_conn() as conn:
        return _create_user_internal(conn, username, password, role)


def get_user_by_username(username: str) -> Optional[User]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        return None
    return User(
        user_id=row["user_id"],
        username=row["username"],
        hashed_password=row["hashed_password"],
        role=row["role"],
        created_at=row["created_at"],
        is_active=bool(row["is_active"]),
    )


def get_user_by_id(user_id: str) -> Optional[User]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        return None
    return User(
        user_id=row["user_id"],
        username=row["username"],
        hashed_password=row["hashed_password"],
        role=row["role"],
        created_at=row["created_at"],
        is_active=bool(row["is_active"]),
    )


def authenticate_user(username: str, password: str) -> Optional[User]:
    user = get_user_by_username(username)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def username_exists(username: str) -> bool:
    with _get_conn() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
    return row is not None


# Initialise on import
_init_db()
