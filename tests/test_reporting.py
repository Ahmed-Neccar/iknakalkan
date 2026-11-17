from services import profiles as ps
from services import reporting as rpt
from services import training as tr


def get_user(conn, name):
    return conn.execute("SELECT * FROM users WHERE username = ?", (name,)).fetchone()


def setup_completed_training(conn, admin, correct_pre=True, correct_post=True):
    pid = ps.create_profile(conn, admin, "Test (sentetik)")
    tr.seed_questions_if_empty(conn)
    q = tr.list_questions(conn)[0]
    pre_choice = q["correct_index"] if correct_pre else (0 if q["correct_index"] != 0 else 1)
    post_choice = q["correct_index"] if correct_post else (0 if q["correct_index"] != 0 else 1)
    tr.record_attempt(conn, admin, pid, q["id"], "pre", pre_choice)
    tr.record_attempt(conn, admin, pid, q["id"], "post", post_choice)
    return pid


def test_pre_vs_post_only_includes_completed_profiles(conn):
    admin = get_user(conn, "admin")
    setup_completed_training(conn, admin, correct_pre=False, correct_post=True)
    pid2 = ps.create_profile(conn, admin, "Yarım Kalan")
    tr.record_attempt(conn, admin, pid2, tr.list_questions(conn)[0]["id"], "pre", 0)  # sadece pre
    rows = rpt.pre_vs_post_by_profile(conn)
    assert len(rows) == 1
    assert rows[0]["pre"] == 0.0 and rows[0]["post"] == 100.0


def test_category_success_aggregates_across_profiles(conn):
    admin = get_user(conn, "admin")
    setup_completed_training(conn, admin)
    rows = rpt.category_success(conn)
    assert sum(r["total"] for r in rows) == 2  # pre + post


def test_wrong_answer_distribution_only_nonzero(conn):
    admin = get_user(conn, "admin")
    setup_completed_training(conn, admin, correct_pre=False, correct_post=True)
    wrong = rpt.wrong_answer_distribution(conn)
    assert wrong and all(w["incorrect"] > 0 for w in wrong)


def test_progress_over_time_has_entries(conn):
    admin = get_user(conn, "admin")
    setup_completed_training(conn, admin)
    rows = rpt.progress_over_time(conn)
    assert len(rows) >= 1


def test_completed_trainings_count(conn):
    admin = get_user(conn, "admin")
    setup_completed_training(conn, admin)
    assert rpt.completed_trainings_count(conn) == 1


def test_summary_metrics_are_real_counts(conn):
    admin = get_user(conn, "admin")
    ps.create_profile(conn, admin, "A")
    ps.create_profile(conn, admin, "B")
    metrics = rpt.summary_metrics(conn)
    assert metrics["Toplam profil sayısı"] == 2


def test_export_csv_roundtrip(conn):
    admin = get_user(conn, "admin")
    setup_completed_training(conn, admin)
    data = rpt.category_success(conn)
    csv_bytes = rpt.export_csv(data)
    text = csv_bytes.decode("utf-8-sig")
    assert "category" in text and str(data[0]["correct"]) in text or str(data[0]["incorrect"]) in text


def test_export_csv_empty_list(conn):
    assert rpt.export_csv([]) == b""


def test_export_pdf_or_graceful_failure(conn):
    admin = get_user(conn, "admin")
    setup_completed_training(conn, admin)
    try:
        pdf_bytes = rpt.export_pdf(conn)
        assert pdf_bytes[:4] == b"%PDF"
    except rpt.PdfUnavailable as exc:
        assert str(exc)  # hata nedeni açık olmalı
