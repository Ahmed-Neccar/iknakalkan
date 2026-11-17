"""Geliştirme/demo ortamında mevcut kullanıcı parolasını güvenli biçimde yeniler.
Kullanım: python reset_password.py
"""
import getpass

from database import init_db
from services.auth import hash_password


def main():
    conn = init_db()
    try:
        users = conn.execute("SELECT username, role FROM users ORDER BY username").fetchall()
        if not users:
            print("Veritabanında kullanıcı bulunamadı.")
            return
        print("Mevcut kullanıcılar:")
        for user in users:
            print(f"- {user['username']} ({user['role']})")
        username = input("Parolasını değiştirmek istediğin kullanıcı: ").strip()
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            print("Bu kullanıcı bulunamadı. Kullanıcı adını kontrol et.")
            return
        password = getpass.getpass("Yeni parola (en az 10 karakter): ")
        confirm = getpass.getpass("Yeni parola tekrar: ")
        if len(password) < 10:
            print("Güvenlik için parola en az 10 karakter olmalı.")
            return
        if password != confirm:
            print("Parolalar eşleşmiyor; hiçbir değişiklik yapılmadı.")
            return
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), row['id']))
        conn.commit()
        print(f"'{username}' kullanıcısının parolası güncellendi. Şimdi uygulamaya bu yeni parolayla giriş yapabilirsin.")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
