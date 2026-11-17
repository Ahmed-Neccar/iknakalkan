import sqlite3

import pytest

from database import TABLES, init_db, table_counts
from services.audit import list_logs, log_action
from services.auth import (PermissionDenied, authenticate, has_permission,
                           hash_password, require_permission, verify_password)


def test_all_tables_created(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in TABLES:
        assert table in names


def test_init_is_idempotent(tmp_path):
    path = tmp_path / "x.db"
    init_db(path).close()
    conn = init_db(path)  # ikinci çalıştırma hata vermemeli ve kullanıcıları çoğaltmamalı
    assert table_counts(conn)["users"] == 3


def test_foreign_keys_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO training_attempts (profile_id, question_id, phase, selected_index, is_correct) "
                     "VALUES (999, 999, 'pre', 0, 0)")


def test_check_constraint_rejects_bad_status(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO scenarios (title, status) VALUES ('x', 'gecersiz')")


def test_empty_label_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO profiles (label) VALUES ('   ')")


def test_password_hashing():
    h = hash_password("gizli")
    assert h != "gizli" and verify_password("gizli", h) and not verify_password("yanlis", h)


def test_authenticate_success_and_failure_are_logged(conn):
    assert authenticate(conn, "admin", "admin123")["role"] == "admin"
    assert authenticate(conn, "admin", "yanlis") is None
    actions = [r["action"] for r in list_logs(conn)]
    assert "login" in actions and "login_failed" in actions


def test_viewer_cannot_edit_and_denial_is_logged(conn):
    viewer = authenticate(conn, "viewer", "viewer123")
    assert has_permission("viewer", "view") and not has_permission("viewer", "edit")
    with pytest.raises(PermissionDenied):
        require_permission(conn, viewer, "edit")
    assert "permission_denied" in [r["action"] for r in list_logs(conn)]


def test_audit_log_written(conn):
    log_action(conn, None, "test_action", "profiles", 1, "detay")
    assert list_logs(conn)[0]["action"] == "test_action"
