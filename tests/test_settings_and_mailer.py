import pytest

from services import profiles as ps
from services import scenarios as ss
from services.auth import PermissionDenied
from services.mailer import ValidationError as MailError
from services.mailer import queue_scenario, real_send_ready
from services.settings_service import (ValidationError, add_recipient, is_authorized_recipient,
                                        list_recipients, remove_recipient, set_setting)


def get_user(conn, name):
    return conn.execute("SELECT * FROM users WHERE username = ?", (name,)).fetchone()


def approved_scenario(conn, admin, scope_verified=True):
    pid = ps.create_profile(conn, admin, "Ayşe (sentetik)", "Uzman", "Finans", "ayse@example.com")
    sid = ss.create_scenario(conn, admin, "S", pid)
    ss.update_message(conn, admin, sid, "Konu", "Gövde")
    ss.run_analysis(conn, admin, sid)
    ss.decide(conn, admin, sid, "approved", scope_verified=scope_verified)
    return sid


def test_add_and_remove_recipient(conn):
    admin = get_user(conn, "admin")
    add_recipient(conn, admin, "Test@Example.com", "Kendi adresim")
    assert is_authorized_recipient(conn, "test@example.com")
    rows = list_recipients(conn)
    assert len(rows) == 1
    remove_recipient(conn, admin, rows[0]["id"])
    assert not is_authorized_recipient(conn, "test@example.com")


def test_add_recipient_validates_email(conn):
    with pytest.raises(ValidationError):
        add_recipient(conn, get_user(conn, "admin"), "gecersiz-adres")


def test_add_recipient_rejects_duplicate(conn):
    admin = get_user(conn, "admin")
    add_recipient(conn, admin, "a@example.com")
    with pytest.raises(ValidationError):
        add_recipient(conn, admin, "a@example.com")


def test_viewer_cannot_manage_recipients(conn):
    with pytest.raises(PermissionDenied):
        add_recipient(conn, get_user(conn, "viewer"), "a@example.com")


def test_queue_without_real_recipient_is_simulation(conn):
    admin = get_user(conn, "admin")
    sid = approved_scenario(conn, admin)
    result = queue_scenario(conn, admin, sid, real_recipient_email=None)
    assert result["real_send"] is False
    assert ss.get_scenario(conn, sid)["status"] == "queued"


def test_queue_only_approved_scenarios(conn):
    admin = get_user(conn, "admin")
    pid = ps.create_profile(conn, admin, "A")
    sid = ss.create_scenario(conn, admin, "S", pid)  # hâlâ 'draft'
    with pytest.raises(MailError):
        queue_scenario(conn, admin, sid)


def test_real_send_blocked_without_env_flag(conn, monkeypatch):
    import config
    monkeypatch.setattr(config, "real_send_env_allowed", lambda: False)  # .env kapalı
    admin = get_user(conn, "admin")
    add_recipient(conn, admin, "alici@example.com")
    sid = approved_scenario(conn, admin, scope_verified=True)
    result = queue_scenario(conn, admin, sid, real_recipient_email="alici@example.com")
    assert result["real_send"] is False  # env kapalıyken gerçek gönderim denenmez, simülasyona düşer


def test_real_send_blocked_without_scope_verification(conn, monkeypatch):
    import config
    monkeypatch.setattr(config, "real_send_env_allowed", lambda: True)
    monkeypatch.setattr(config, "smtp_configured", lambda: True)
    admin = get_user(conn, "admin")
    set_setting(conn, admin, "real_send_db_enabled", "true")
    add_recipient(conn, admin, "alici@example.com")
    sid = approved_scenario(conn, admin, scope_verified=False)  # kapsam doğrulanmadı
    with pytest.raises(MailError):
        queue_scenario(conn, admin, sid, real_recipient_email="alici@example.com")


def test_real_send_blocked_for_unauthorized_recipient(conn, monkeypatch):
    import config
    monkeypatch.setattr(config, "real_send_env_allowed", lambda: True)
    monkeypatch.setattr(config, "smtp_configured", lambda: True)
    admin = get_user(conn, "admin")
    set_setting(conn, admin, "real_send_db_enabled", "true")
    sid = approved_scenario(conn, admin, scope_verified=True)
    with pytest.raises(MailError):
        queue_scenario(conn, admin, sid, real_recipient_email="yabanci@example.com")


def test_real_send_ready_reports_reasons(conn):
    readiness = real_send_ready(conn)
    assert readiness["ready"] is False and readiness["reasons"]


def test_real_send_succeeds_with_all_conditions(conn, monkeypatch):
    import config
    import services.mailer as mailer
    monkeypatch.setattr(config, "real_send_env_allowed", lambda: True)
    monkeypatch.setattr(config, "smtp_configured", lambda: True)
    sent = {}
    monkeypatch.setattr(mailer, "_send_smtp", lambda to, subject, body: sent.update(to=to, subject=subject))
    admin = get_user(conn, "admin")
    set_setting(conn, admin, "real_send_db_enabled", "true")
    add_recipient(conn, admin, "alici@example.com")
    sid = approved_scenario(conn, admin, scope_verified=True)
    result = queue_scenario(conn, admin, sid, real_recipient_email="alici@example.com")
    assert result["real_send"] is True
    assert sent["to"] == "alici@example.com"
    events = mailer.list_events(conn, sid)
    assert events[0]["is_real_send"] == 1 and events[0]["status"] == "simulated"


def test_real_send_failure_is_recorded(conn, monkeypatch):
    import config
    import services.mailer as mailer
    monkeypatch.setattr(config, "real_send_env_allowed", lambda: True)
    monkeypatch.setattr(config, "smtp_configured", lambda: True)
    def boom(to, subject, body):
        raise RuntimeError("SMTP sunucusuna bağlanılamadı")
    monkeypatch.setattr(mailer, "_send_smtp", boom)
    admin = get_user(conn, "admin")
    set_setting(conn, admin, "real_send_db_enabled", "true")
    add_recipient(conn, admin, "alici@example.com")
    sid = approved_scenario(conn, admin, scope_verified=True)
    with pytest.raises(MailError):
        queue_scenario(conn, admin, sid, real_recipient_email="alici@example.com")
    events = mailer.list_events(conn, sid)
    assert events[0]["status"] == "failed"
