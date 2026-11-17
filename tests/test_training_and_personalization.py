import pytest

from services import profiles as ps
from services import training as tr
from services import personalization as pers


def get_user(conn, name):
    return conn.execute("SELECT * FROM users WHERE username = ?", (name,)).fetchone()


def make_profile(conn, admin):
    return ps.create_profile(conn, admin, "Test Kişi (sentetik)")


def test_seed_questions_idempotent(conn):
    n1 = tr.seed_questions_if_empty(conn)
    n2 = tr.seed_questions_if_empty(conn)
    assert n1 > 0 and n2 == 0
    assert len(tr.list_questions(conn)) == n1


def test_record_attempt_scores_correctly(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    tr.seed_questions_if_empty(conn)
    q = tr.list_questions(conn)[0]
    assert tr.record_attempt(conn, admin, pid, q["id"], "pre", q["correct_index"]) is True
    wrong_index = 0 if q["correct_index"] != 0 else 1
    assert tr.record_attempt(conn, admin, pid, q["id"], "pre", wrong_index) is False


def test_record_attempt_validates_phase_and_profile(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    tr.seed_questions_if_empty(conn)
    q = tr.list_questions(conn)[0]
    with pytest.raises(tr.ValidationError):
        tr.record_attempt(conn, admin, pid, q["id"], "ortasinda", 0)
    with pytest.raises(tr.ValidationError):
        tr.record_attempt(conn, admin, 9999, q["id"], "pre", 0)
    with pytest.raises(tr.ValidationError):
        tr.record_attempt(conn, admin, pid, 9999, "pre", 0)


def test_compute_score(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    tr.seed_questions_if_empty(conn)
    questions = tr.list_questions(conn)
    tr.record_attempt(conn, admin, pid, questions[0]["id"], "pre", questions[0]["correct_index"])
    wrong = 0 if questions[1]["correct_index"] != 0 else 1
    tr.record_attempt(conn, admin, pid, questions[1]["id"], "pre", wrong)
    score = tr.compute_score(conn, pid, "pre")
    assert score["total"] == 2 and score["correct"] == 1 and score["percent"] == 50.0


def test_compute_score_none_when_no_attempts(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    assert tr.compute_score(conn, pid, "pre") is None


def test_category_breakdown(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    tr.seed_questions_if_empty(conn)
    otorite_qs = [q for q in tr.list_questions(conn) if q["category"] == "otorite"]
    tr.record_attempt(conn, admin, pid, otorite_qs[0]["id"], "pre", otorite_qs[0]["correct_index"])
    wrong = 0 if otorite_qs[1]["correct_index"] != 0 else 1
    tr.record_attempt(conn, admin, pid, otorite_qs[1]["id"], "pre", wrong)
    breakdown = tr.category_breakdown(conn, pid)
    assert breakdown["otorite"] == {"correct": 1, "incorrect": 1}


def test_personalization_flags_weak_category(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    tr.seed_questions_if_empty(conn)
    korku_qs = [q for q in tr.list_questions(conn) if q["category"] == "korku_tehdit"]
    for q in korku_qs:
        wrong = 0 if q["correct_index"] != 0 else 1
        tr.record_attempt(conn, admin, pid, q["id"], "pre", wrong)
    categories = pers.generate_recommendations(conn, admin, pid)
    assert "korku_tehdit" in categories
    recs = pers.list_recommendations(conn, pid)
    assert recs and recs[0]["category"] == "korku_tehdit" and recs[0]["material"]


def test_personalization_no_recommendation_when_strong(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    tr.seed_questions_if_empty(conn)
    otorite_qs = [q for q in tr.list_questions(conn) if q["category"] == "otorite"]
    for q in otorite_qs:
        tr.record_attempt(conn, admin, pid, q["id"], "pre", q["correct_index"])
    categories = pers.generate_recommendations(conn, admin, pid)
    assert "otorite" not in categories


def test_personalization_no_recommendation_without_attempts(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    assert pers.generate_recommendations(conn, admin, pid) == []


def test_progress_over_time_returns_rows(conn):
    admin = get_user(conn, "admin")
    pid = make_profile(conn, admin)
    tr.seed_questions_if_empty(conn)
    q = tr.list_questions(conn)[0]
    tr.record_attempt(conn, admin, pid, q["id"], "pre", q["correct_index"])
    rows = tr.progress_over_time(conn, pid)
    assert len(rows) == 1 and rows[0]["phase"] == "pre"
