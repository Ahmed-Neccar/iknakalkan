"""Kimlik doğrulama ve rol bazlı yetkilendirme."""
import hashlib
import hmac
import os
import secrets

from services.audit import log_action

# Hangi rol hangi işlemi yapabilir
PERMISSIONS = {
    "admin": {"view", "edit", "delete", "approve", "queue", "manage_users", "export"},
    "analyst": {"view", "edit", "approve", "export"},
    "viewer": {"view"},
}

DEFAULT_DEMO_PASSWORDS = {"admin": "admin123", "analyst": "analyst123", "viewer": "viewer123"}


class PermissionDenied(Exception):
    """Kullanıcının rolü bu işleme izin vermiyor."""


def hash_password(password: str, salt: bytes = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
        expected = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
        )
        return hmac.compare_digest(expected.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


def ensure_default_users(conn):
    """Kullanıcı yoksa demo kullanıcılarını ekler. Yönetici şifresi IKNA_ADMIN_PASSWORD ile değiştirilebilir."""
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return
    passwords = dict(DEFAULT_DEMO_PASSWORDS)
    admin_pw = os.environ.get("IKNA_ADMIN_PASSWORD", "").strip()
    if admin_pw:
        passwords["admin"] = admin_pw
    for username, role in (("admin", "admin"), ("analyst", "analyst"), ("viewer", "viewer")):
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hash_password(passwords[username]), role),
        )
    conn.commit()


def authenticate(conn, username: str, password: str):
    """Başarılıysa kullanıcı satırını, değilse None döner. Hata mesajı hangisinin yanlış olduğunu belli etmez."""
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", ((username or "").strip(),)
    ).fetchone()
    if row and verify_password(password or "", row["password_hash"]):
        log_action(conn, row["id"], "login", "users", row["id"])
        return row
    log_action(conn, None, "login_failed", "users", None, "başarısız giriş denemesi")
    return None


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def require_permission(conn, user, permission: str):
    """Yetki yoksa işlemi kaydeder ve PermissionDenied fırlatır."""
    if not has_permission(user["role"], permission):
        log_action(conn, user["id"], "permission_denied", detail=permission)
        raise PermissionDenied(f"'{user['role']}' rolü '{permission}' işlemini yapamaz.")


def using_default_passwords(conn) -> bool:
    """Demo şifreleri hâlâ geçerli mi? (UI'da uyarı göstermek için)"""
    for username, pw in DEFAULT_DEMO_PASSWORDS.items():
        row = conn.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
        if row and verify_password(pw, row["password_hash"]):
            return True
    return False
