"""Senaryo oluşturma, analiz, onay/atlama ve toplu işlem yönetimi."""
import json

from services.analysis import analyze_message
from services.audit import log_action
from services.auth import require_permission
from services.message_generator import generate_message
from services.profiles import get_profile

VALID_STATUSES = {"draft", "pending_approval", "approved", "skipped", "queued", "completed"}


class ValidationError(ValueError):
    pass


def create_scenario(conn, user, title, profile_id, description=""):
    require_permission(conn, user, "edit")
    title = (title or "").strip()
    if not title:
        raise ValidationError("Senaryo başlığı boş olamaz.")
    if profile_id and get_profile(conn, profile_id) is None:
        raise ValidationError("Seçilen profil bulunamadı.")
    cur = conn.execute(
        "INSERT INTO scenarios (title, description, profile_id, status, created_by) "
        "VALUES (?, ?, ?, 'draft', ?)",
        (title, (description or "").strip(), profile_id, user["id"]),
    )
    conn.commit()
    log_action(conn, user["id"], "scenario_create", "scenarios", cur.lastrowid, title)
    return cur.lastrowid


def generate_scenario_message(conn, user, scenario_id):
    """Profile göre mesaj üretir, senaryoya kaydeder ve otomatik ikna analizi yapar."""
    require_permission(conn, user, "edit")
    scenario = get_scenario(conn, scenario_id)
    if scenario is None:
        raise ValidationError("Senaryo bulunamadı.")
    if scenario["profile_id"] is None:
        raise ValidationError("Mesaj üretmek için senaryoya bir profil atanmalı.")
    profile = get_profile(conn, scenario["profile_id"])
    generated = generate_message(profile)
    update_message(conn, user, scenario_id, generated["subject"], generated["body"])
    run_analysis(conn, user, scenario_id)
    return generated


def update_message(conn, user, scenario_id, subject, body):
    require_permission(conn, user, "edit")
    if get_scenario(conn, scenario_id) is None:
        raise ValidationError("Senaryo bulunamadı.")
    conn.execute(
        "UPDATE scenarios SET message_subject=?, message_body=?, updated_at=datetime('now') WHERE id=?",
        ((subject or "").strip(), (body or "").strip(), scenario_id),
    )
    conn.commit()
    log_action(conn, user["id"], "scenario_message_update", "scenarios", scenario_id)


def run_analysis(conn, user, scenario_id):
    require_permission(conn, user, "edit")
    scenario = get_scenario(conn, scenario_id)
    if scenario is None:
        raise ValidationError("Senaryo bulunamadı.")
    text = f"{scenario['message_subject'] or ''}\n{scenario['message_body'] or ''}".strip()
    if not text:
        raise ValidationError("Analiz için önce bir mesaj gerekli.")
    result = analyze_message(text)
    conn.execute(
        "INSERT INTO analyses (scenario_id, message_text, mode, result_json) VALUES (?, ?, ?, ?)",
        (scenario_id, text, result["mode"].replace("template_fallback", "rule_based").replace("template", "rule_based"), json.dumps(result, ensure_ascii=False)),
    )
    set_status(conn, user, scenario_id, "pending_approval")
    conn.commit()
    log_action(conn, user["id"], "scenario_analyze", "scenarios", scenario_id, result["mode"])
    return result


def latest_analysis(conn, scenario_id):
    return conn.execute(
        "SELECT * FROM analyses WHERE scenario_id = ? ORDER BY id DESC LIMIT 1", (scenario_id,)
    ).fetchone()


def get_scenario(conn, scenario_id):
    return conn.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()


def list_scenarios(conn, status=None):
    if status:
        return conn.execute("SELECT * FROM scenarios WHERE status = ? ORDER BY id DESC", (status,)).fetchall()
    return conn.execute("SELECT * FROM scenarios ORDER BY id DESC").fetchall()


def set_status(conn, user, scenario_id, status):
    if status not in VALID_STATUSES:
        raise ValidationError(f"Geçersiz durum: {status}")
    conn.execute("UPDATE scenarios SET status=?, updated_at=datetime('now') WHERE id=?", (status, scenario_id))
    conn.commit()


def decide(conn, user, scenario_id, decision, scope_verified=False, note=""):
    """Tekli onay / atlama. decision: 'approved' | 'skipped'."""
    require_permission(conn, user, "approve")
    scenario = get_scenario(conn, scenario_id)
    if scenario is None:
        raise ValidationError("Senaryo bulunamadı.")
    if decision not in ("approved", "skipped"):
        raise ValidationError("Geçersiz karar.")
    conn.execute(
        "INSERT INTO approvals (scenario_id, decision, decided_by, scope_verified, note) VALUES (?, ?, ?, ?, ?)",
        (scenario_id, decision, user["id"], 1 if scope_verified else 0, (note or "").strip()),
    )
    set_status(conn, user, scenario_id, decision)
    conn.commit()
    log_action(conn, user["id"], f"scenario_{decision}", "scenarios", scenario_id, note)


def bulk_decide(conn, user, scenario_ids, decision, scope_verified=False):
    """Birden fazla senaryo için tekli onay/atlamayı tekrarlar; hangi id'lerin başarısız olduğunu da döner."""
    ok, failed = [], []
    for sid in scenario_ids:
        try:
            decide(conn, user, sid, decision, scope_verified)
            ok.append(sid)
        except ValidationError as exc:
            failed.append((sid, str(exc)))
    log_action(conn, user["id"], "scenario_bulk_decide", "scenarios", None,
               f"decision={decision}; ok={len(ok)}; failed={len(failed)}")
    return {"ok": ok, "failed": failed}
