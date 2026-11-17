"""Simülasyon kuyruğu ve kontrollü gerçek gönderim.

Gerçek gönderim yalnızca ŞU DÖRT koşul birden sağlandığında çalışır:
  1) Senaryo onaylanmış olmalı (status == 'approved')
  2) Onay sırasında 'scope_verified' işaretlenmiş olmalı (yetkili kapsam doğrulanmış)
  3) .env dosyasında ALLOW_REAL_SEND=true olmalı
  4) Ayarlar sayfasında (veritabanında) gerçek gönderim anahtarı da açık olmalı
Alıcı adresi ayrıca authorized_recipients listesinde olmalı; aksi halde gönderim reddedilir.
Bu koşullardan biri eksikse işlem SİMÜLASYON olarak kaydedilir, gerçek mail gönderilmez."""
import smtplib
from email.mime.text import MIMEText

import config
from services.audit import log_action
from services.auth import require_permission
from services.settings_service import (from_display_name, is_authorized_recipient,
                                        real_send_db_enabled)


class ValidationError(ValueError):
    pass


def real_send_ready(conn) -> dict:
    """Gerçek gönderimin şu an mümkün olup olmadığını, nedenleriyle birlikte döner."""
    reasons = []
    if not config.real_send_env_allowed():
        reasons.append(".env dosyasında ALLOW_REAL_SEND=true değil")
    if not real_send_db_enabled(conn):
        reasons.append("Ayarlar sayfasında gerçek gönderim kapalı")
    if not config.smtp_configured():
        reasons.append("SMTP bilgileri (.env) eksik")
    return {"ready": not reasons, "reasons": reasons}


def _send_smtp(to_email, subject, body):
    cfg = config.smtp_config()
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, cfg["username"], to_email
    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
        if cfg["use_tls"]:
            server.starttls()
        server.login(cfg["username"], cfg["password"])
        server.sendmail(cfg["username"], [to_email], msg.as_string())


def queue_scenario(conn, user, scenario_id, real_recipient_email=None):
    """Onaylanmış bir senaryoyu kuyruğa alır. Tüm koşullar sağlanmıyorsa SİMÜLASYON olarak kaydeder,
    hatayı yutmaz: gerçek gönderim denenip başarısız olursa 'failed' olarak kaydedilir."""
    require_permission(conn, user, "queue")
    scenario = conn.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
    if scenario is None:
        raise ValidationError("Senaryo bulunamadı.")
    if scenario["status"] != "approved":
        raise ValidationError("Yalnızca onaylanmış senaryolar kuyruğa alınabilir.")
    approval = conn.execute(
        "SELECT * FROM approvals WHERE scenario_id = ? AND decision='approved' ORDER BY id DESC LIMIT 1",
        (scenario_id,),
    ).fetchone()
    scope_ok = bool(approval and approval["scope_verified"])

    readiness = real_send_ready(conn)
    attempt_real = bool(real_recipient_email) and scope_ok and readiness["ready"]

    if real_recipient_email and not scope_ok:
        conn.execute(
            "INSERT INTO simulation_events (scenario_id, status, is_real_send, detail) VALUES (?, 'failed', 0, ?)",
            (scenario_id, "Reddedildi: onay sırasında izinli test kapsamı doğrulanmamış."),
        )
        conn.commit()
        raise ValidationError("Gerçek gönderim reddedildi: bu senaryo onaylanırken 'izinli test kapsamı' doğrulanmamış.")

    if real_recipient_email and not is_authorized_recipient(conn, real_recipient_email):
        conn.execute(
            "INSERT INTO simulation_events (scenario_id, status, is_real_send, detail) VALUES (?, 'failed', 0, ?)",
            (scenario_id, f"Reddedildi: {real_recipient_email} yetkili alıcı listesinde değil."),
        )
        conn.commit()
        raise ValidationError("Bu adres yetkili test alıcıları listesinde değil. Önce Ayarlar sayfasından ekleyin.")

    if not attempt_real:
        detail = "Simülasyon kuyruğuna alındı (gerçek gönderim kapalı)." if not real_recipient_email \
            else f"Simülasyon kuyruğuna alındı. Gerçek gönderim şu an mümkün değil: {', '.join(readiness['reasons'])}"
        conn.execute(
            "INSERT INTO simulation_events (scenario_id, status, is_real_send, detail) VALUES (?, 'queued', 0, ?)",
            (scenario_id, detail),
        )
        set_status_completed(conn, scenario_id)
        conn.commit()
        log_action(conn, user["id"], "scenario_queue_simulated", "scenarios", scenario_id, detail)
        return {"real_send": False, "detail": detail}

    try:
        subject = f"[SİMÜLASYON TESTİ] {scenario['message_subject'] or scenario['title']}"
        body = (scenario["message_body"] or "") + \
            "\n\n--\nBu mesaj bir güvenlik farkındalığı eğitimi simülasyonudur. " \
            f"Gönderen görünen ad: {from_display_name(conn)}"
        _send_smtp(real_recipient_email, subject, body)
        conn.execute(
            "INSERT INTO simulation_events (scenario_id, status, is_real_send, detail) VALUES (?, 'simulated', 1, ?)",
            (scenario_id, f"Gerçek test maili gönderildi: {real_recipient_email}"),
        )
        set_status_completed(conn, scenario_id)
        conn.commit()
        log_action(conn, user["id"], "scenario_real_send", "scenarios", scenario_id, real_recipient_email)
        return {"real_send": True, "detail": f"Gönderildi: {real_recipient_email}"}
    except Exception as exc:
        conn.execute(
            "INSERT INTO simulation_events (scenario_id, status, is_real_send, detail) VALUES (?, 'failed', 1, ?)",
            (scenario_id, f"Gönderim hatası: {exc}"),
        )
        conn.commit()
        log_action(conn, user["id"], "scenario_real_send_failed", "scenarios", scenario_id, str(exc))
        raise ValidationError(f"Gönderim başarısız oldu: {exc}")


def set_status_completed(conn, scenario_id):
    conn.execute("UPDATE scenarios SET status='queued', updated_at=datetime('now') WHERE id=?", (scenario_id,))


def list_events(conn, scenario_id=None):
    if scenario_id:
        return conn.execute(
            "SELECT * FROM simulation_events WHERE scenario_id=? ORDER BY id DESC", (scenario_id,)
        ).fetchall()
    return conn.execute("SELECT * FROM simulation_events ORDER BY id DESC").fetchall()
