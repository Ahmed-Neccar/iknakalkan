import json

import pytest

from services import profiles as ps
from services import scenarios as ss
from services.auth import PermissionDenied


def get_user(conn, name):
    return conn.execute("SELECT * FROM users WHERE username = ?", (name,)).fetchone()


def make_profile(conn, admin):
    return ps.create_profile(conn, admin, "Ayşe (sentetik)", "Muhasebe Uzmanı", "Finans", "ayse@example.com")


def test_create_scenario_requires_title(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    with pytest.raises(ss.ValidationError):
        ss.create_scenario(conn, admin, "  ", pid)


def test_create_scenario_and_generate_message(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    sid = ss.create_scenario(conn, admin, "BT Acil Senaryo", pid)
    generated = ss.generate_scenario_message(conn, admin, sid)
    scenario = ss.get_scenario(conn, sid)
    assert scenario["message_subject"] and scenario["message_body"]
    assert "Ayşe" in scenario["message_subject"] or "Ayşe" in scenario["message_body"]
    assert scenario["status"] == "pending_approval"  # otomatik analiz durumu ilerletir
    assert generated["mode"] in ("template", "llm", "template_fallback")


def test_generate_message_requires_profile(conn):
    admin = get_user(conn, "admin")
    sid = ss.create_scenario(conn, admin, "Profilsiz Senaryo", None)
    with pytest.raises(ss.ValidationError):
        ss.generate_scenario_message(conn, admin, sid)


def test_run_analysis_stores_result_and_advances_status(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    sid = ss.create_scenario(conn, admin, "Senaryo", pid)
    ss.update_message(conn, admin, sid, "Acil!", "Hesabınız hemen kesilecek, tıklayın.")
    result = ss.run_analysis(conn, admin, sid)
    assert result["findings"]
    analysis = ss.latest_analysis(conn, sid)
    assert json.loads(analysis["result_json"])["findings"]
    assert ss.get_scenario(conn, sid)["status"] == "pending_approval"


def test_run_analysis_requires_message(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    sid = ss.create_scenario(conn, admin, "Senaryo", pid)
    with pytest.raises(ss.ValidationError):
        ss.run_analysis(conn, admin, sid)


def test_single_approve_and_skip(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    sid1 = ss.create_scenario(conn, admin, "S1", pid)
    sid2 = ss.create_scenario(conn, admin, "S2", pid)
    ss.update_message(conn, admin, sid1, "x", "y")
    ss.update_message(conn, admin, sid2, "x", "y")
    ss.run_analysis(conn, admin, sid1)
    ss.run_analysis(conn, admin, sid2)

    ss.decide(conn, admin, sid1, "approved", scope_verified=True)
    ss.decide(conn, admin, sid2, "skipped")
    assert ss.get_scenario(conn, sid1)["status"] == "approved"
    assert ss.get_scenario(conn, sid2)["status"] == "skipped"


def test_bulk_decide(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    ids = []
    for i in range(3):
        sid = ss.create_scenario(conn, admin, f"S{i}", pid)
        ss.update_message(conn, admin, sid, "x", "y")
        ss.run_analysis(conn, admin, sid)
        ids.append(sid)
    result = ss.bulk_decide(conn, admin, ids, "approved", scope_verified=True)
    assert len(result["ok"]) == 3 and result["failed"] == []
    for sid in ids:
        assert ss.get_scenario(conn, sid)["status"] == "approved"


def test_viewer_cannot_create_or_decide(conn):
    viewer = get_user(conn, "viewer")
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    with pytest.raises(PermissionDenied):
        ss.create_scenario(conn, viewer, "x", pid)
    sid = ss.create_scenario(conn, admin, "S", pid)
    ss.update_message(conn, admin, sid, "x", "y")
    ss.run_analysis(conn, admin, sid)
    with pytest.raises(PermissionDenied):
        ss.decide(conn, viewer, sid, "approved")
