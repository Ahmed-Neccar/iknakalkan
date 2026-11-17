"""İşlem kayıtları (audit log)."""


def log_action(conn, user_id, action, entity=None, entity_id=None, detail=None):
    conn.execute(
        "INSERT INTO audit_logs (user_id, action, entity, entity_id, detail) VALUES (?, ?, ?, ?, ?)",
        (user_id, action, entity, entity_id, detail),
    )
    conn.commit()


def list_logs(conn, limit=100):
    return conn.execute(
        "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
