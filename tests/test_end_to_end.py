"""Uygulamanın temel kullanıcı akışını uçtan uca test eder:
giriş -> profil -> senaryo -> mesaj üretimi -> analiz -> onay -> simülasyon kuyruğu
-> eğitim testi -> kişiselleştirme -> raporlama."""
from services import personalization as pers
from services import profiles as ps
from services import reporting as rpt
from services import scenarios as ss
from services import training as tr
from services.auth import authenticate
from services.mailer import queue_scenario


def test_full_user_flow(conn):
    # 1) Giriş
    admin = authenticate(conn, "admin", "admin123")
    assert admin is not None

    # 2) Profil oluştur
    pid = ps.create_profile(conn, admin, "Ayşe (sentetik)", "Muhasebe Uzmanı", "Finans", "ayse@example.com")
    assert ps.get_profile(conn, pid) is not None

    # 3) Senaryo oluştur ve yapay zekâ ile mesaj üret
    sid = ss.create_scenario(conn, admin, "Uçtan Uca Senaryo", pid)
    ss.generate_scenario_message(conn, admin, sid)
    scenario = ss.get_scenario(conn, sid)
    assert scenario["message_subject"] and scenario["status"] == "pending_approval"

    # 4) Analiz sonucu kayıtlı mı
    analysis = ss.latest_analysis(conn, sid)
    assert analysis is not None

    # 5) Onayla (kapsam doğrulanmış)
    ss.decide(conn, admin, sid, "approved", scope_verified=True)
    assert ss.get_scenario(conn, sid)["status"] == "approved"

    # 6) Simülasyon kuyruğuna al (gerçek gönderim olmadan)
    result = queue_scenario(conn, admin, sid, real_recipient_email=None)
    assert result["real_send"] is False
    assert ss.get_scenario(conn, sid)["status"] == "queued"

    # 7) Eğitim testi: öncesi ve sonrası
    tr.seed_questions_if_empty(conn)
    questions = tr.list_questions(conn)
    wrong_index = lambda q: 0 if q["correct_index"] != 0 else 1
    for q in questions[:3]:
        tr.record_attempt(conn, admin, pid, q["id"], "pre", wrong_index(q))
    for q in questions[:3]:
        tr.record_attempt(conn, admin, pid, q["id"], "post", q["correct_index"])
    pre_score = tr.compute_score(conn, pid, "pre")
    post_score = tr.compute_score(conn, pid, "post")
    assert post_score["percent"] > pre_score["percent"]

    # 8) Kişiselleştirilmiş öneri üretildi mi (pre'de yanlış yapılan kategoriler için)
    categories = pers.generate_recommendations(conn, admin, pid)
    assert isinstance(categories, list)

    # 9) Raporlama: tüm veriler veritabanından geliyor
    metrics = rpt.summary_metrics(conn)
    assert metrics["Toplam profil sayısı"] >= 1
    assert metrics["Toplam senaryo sayısı"] >= 1

    # 10) Audit log'da akışın izleri var mı
    actions = [r["action"] for r in conn.execute("SELECT action FROM audit_logs").fetchall()]
    for expected in ("login", "profile_create", "scenario_create", "scenario_analyze",
                     "scenario_approved", "scenario_queue_simulated", "training_attempt"):
        assert expected in actions
