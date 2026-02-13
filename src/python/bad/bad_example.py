def dangerous_query(conn, username):
    """
    BAD: SQL injection via string concatenation
    """
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


def run_user_code(user_input: str):
    """
    BAD: arbitrary code execution
    """
    return eval(user_input)
