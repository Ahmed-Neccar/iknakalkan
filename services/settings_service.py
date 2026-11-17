"""Uygulama ayarları (gönderen adı, yetkili alıcılar, gerçek gönderim anahtarı).
Yalnızca SMTP parolası buradan hariç tutulur; o yalnızca ortam değişkeninde kalır."""
import re

from services.audit import log_action
from services.auth import require_permission

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

DEFAULTS = {
    "from_display_name": "Farkındalık Eğitimi (Simülasyon)",
    "real_send_db_enabled": "false",  # veritabanı tarafındaki anahtar; .env'deki ALLOW_REAL_SEND ile VE'lenir
}


class ValidationError(ValueError):
    pass


def get_setting(conn, key, default=None):
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row is not None:
        return row["value"]
    return DEFAULTS.get(key, default)


def set_setting(conn, user, key, value):
    require_permission(conn, user, "manage_users")  # yalnızca admin ayarları değiştirebilir
    conn.execute(
        "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
        (key, value),
    )
    conn.commit()
    log_action(conn, user["id"], "setting_update", "app_settings", None, f"{key}={value}")


def real_send_db_enabled(conn) -> bool:
    return get_setting(conn, "real_send_db_enabled") == "true"


def from_display_name(conn) -> str:
    return get_setting(conn, "from_display_name")


def list_recipients(conn):
    return conn.execute("SELECT * FROM authorized_recipients ORDER BY id DESC").fetchall()


def add_recipient(conn, user, email, label=""):
    require_permission(conn, user, "manage_users")
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise ValidationError("Geçerli bir e-posta adresi girin.")
    try:
        conn.execute(
            "INSERT INTO authorized_recipients (email, label, added_by) VALUES (?, ?, ?)",
            (email, (label or "").strip(), user["id"]),
        )
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise ValidationError("Bu adres zaten listede.")
        raise
    conn.commit()
    log_action(conn, user["id"], "recipient_add", "authorized_recipients", None, email)


def remove_recipient(conn, user, recipient_id):
    require_permission(conn, user, "manage_users")
    row = conn.execute("SELECT * FROM authorized_recipients WHERE id = ?", (recipient_id,)).fetchone()
    if row is None:
        raise ValidationError("Kayıt bulunamadı.")
    conn.execute("DELETE FROM authorized_recipients WHERE id = ?", (recipient_id,))
    conn.commit()
    log_action(conn, user["id"], "recipient_remove", "authorized_recipients", recipient_id, row["email"])


def is_authorized_recipient(conn, email) -> bool:
    email = (email or "").strip().lower()
    row = conn.execute("SELECT 1 FROM authorized_recipients WHERE email = ?", (email,)).fetchone()
    return row is not None
