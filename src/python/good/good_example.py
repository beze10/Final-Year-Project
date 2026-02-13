# Good Python

import sqlite3
import re

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")

def validate_username(username: str) -> str:
    if not isinstance(username, str):
        raise ValueError("Invalid type")

    username = username.strip()
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Invalid username format")

    return username


def get_user_by_username(conn: sqlite3.Connection, username: str):
    """
    GOOD: parameterised query prevents SQL injection
    """
    username = validate_username(username)

    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username FROM users WHERE username = ?",
        (username,)
    )
    return cursor.fetchone()
