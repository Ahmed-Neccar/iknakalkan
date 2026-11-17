import pytest

from services import profiles as ps
from services.audit import list_logs
from services.auth import PermissionDenied


def get_user(conn, name):
    return conn.execute("SELECT * FROM users WHERE username = ?", (name,)).fetchone()


CSV_OK = (
    "label,role_title,department,allowed_contact\n"
    "Ali (sentetik),Uzman,Finans,ali@example.com\n"
    "Veli (sentetik),Sorumlu,IT,veli@example.org\n"
)
CSV_MIXED = CSV_OK + "Kötü,Test,Test,biri@gercek-alan.invalid\n,Etiketsiz,X,\n"


def test_create_and_list_profile(conn):
    admin = get_user(conn, "admin")
    pid = ps.create_profile(conn, admin, "Ayşe (sentetik)", "Uzman", "Finans", "ayse@example.com")
    rows = ps.list_profiles(conn)
    assert len(rows) == 1 and rows[0]["id"] == pid
    assert rows[0]["data_source"] == "manual" and rows[0]["is_synthetic"] == 1


def test_update_profile(conn):
    admin = get_user(conn, "admin")
    pid = ps.create_profile(conn, admin, "Eski", "", "", "")
    ps.update_profile(conn, admin, pid, "Yeni", "Görev", "Dept", "yeni@example.com")
    p = ps.get_profile(conn, pid)
    assert p["label"] == "Yeni" and p["role_title"] == "Görev" and p["allowed_contact"] == "yeni@example.com"


def test_update_missing_profile(conn):
    with pytest.raises(ps.ValidationError):
        ps.update_profile(conn, get_user(conn, "admin"), 999, "X")


def test_validation_rules(conn):
    admin = get_user(conn, "admin")
    bad_inputs = [
        dict(label="   "),                                       # boş etiket
        dict(label="x" * 101),                                   # çok uzun
        dict(label="A", allowed_contact="eposta-degil"),         # geçersiz e-posta
        dict(label="A", allowed_contact="a@gercek-sirket.com"),  # izinli alan değil
    ]
    for bad in bad_inputs:
        with pytest.raises(ps.ValidationError):
            ps.create_profile(conn, admin, **bad)
    assert ps.list_profiles(conn) == []


def test_search(conn):
    admin = get_user(conn, "admin")
    ps.create_profile(conn, admin, "Ali", "", "Finans", "")
    ps.create_profile(conn, admin, "Veli", "", "IT", "")
    assert len(ps.list_profiles(conn, "finans")) == 1
    assert len(ps.list_profiles(conn, "")) == 2


def test_viewer_cannot_create_and_is_logged(conn):
    with pytest.raises(PermissionDenied):
        ps.create_profile(conn, get_user(conn, "viewer"), "Ali")
    assert ps.list_profiles(conn) == []
    assert "permission_denied" in [r["action"] for r in list_logs(conn)]


def test_only_admin_can_delete(conn):
    admin, analyst = get_user(conn, "admin"), get_user(conn, "analyst")
    pid = ps.create_profile(conn, analyst, "Ali")
    with pytest.raises(PermissionDenied):
        ps.delete_profile(conn, analyst, pid)
    assert len(ps.list_profiles(conn)) == 1
    ps.delete_profile(conn, admin, pid)
    assert ps.list_profiles(conn) == []


def test_csv_import_records_provenance(conn):
    admin = get_user(conn, "admin")
    result = ps.import_profiles_csv(conn, admin, CSV_OK.encode("utf-8"), "test.csv", "Sentetik üretim", True)
    assert result["imported"] == 2 and result["rejected"] == []
    row = ps.list_profiles(conn)[0]
    assert row["data_source"] == "csv_import:test.csv"
    assert row["data_origin"] == "Sentetik üretim"
    assert row["imported_at"]


def test_csv_import_skips_bad_rows_with_reasons(conn):
    result = ps.import_profiles_csv(conn, get_user(conn, "admin"), CSV_MIXED, "k.csv", "Sentetik", True)
    assert result["imported"] == 2
    assert [r[0] for r in result["rejected"]] == [4, 5]   # satır numaraları (başlık = 1)
    assert len(ps.list_profiles(conn)) == 2


def test_csv_import_needs_confirmation(conn):
    with pytest.raises(ps.ValidationError):
        ps.import_profiles_csv(conn, get_user(conn, "admin"), CSV_OK, "k.csv", "Sentetik", False)
    assert ps.list_profiles(conn) == []


def test_csv_import_needs_source_and_origin(conn):
    with pytest.raises(ps.ValidationError):
        ps.import_profiles_csv(conn, get_user(conn, "admin"), CSV_OK, "", "", True)


def test_csv_without_label_column(conn):
    with pytest.raises(ps.ValidationError):
        ps.import_profiles_csv(conn, get_user(conn, "admin"), "isim,x\nAli,1\n", "k.csv", "S", True)


def test_csv_too_large(conn):
    big = "label\n" + "a\n" * (ps.MAX_CSV_BYTES)
    with pytest.raises(ps.ValidationError):
        ps.import_profiles_csv(conn, get_user(conn, "admin"), big, "k.csv", "S", True)


def test_csv_turkish_headers_and_bom(conn):
    text = "\ufeffad_etiketi,gorev,departman,iletisim\nAli,Uzman,Finans,ali@example.com\n"
    result = ps.import_profiles_csv(conn, get_user(conn, "admin"), text.encode("utf-8"), "tr.csv", "S", True)
    assert result["imported"] == 1 and ps.list_profiles(conn)[0]["role_title"] == "Uzman"


def test_viewer_cannot_import(conn):
    with pytest.raises(PermissionDenied):
        ps.import_profiles_csv(conn, get_user(conn, "viewer"), CSV_OK, "k.csv", "S", True)
    assert ps.list_profiles(conn) == []


def test_import_is_audited(conn):
    ps.import_profiles_csv(conn, get_user(conn, "admin"), CSV_OK, "k.csv", "S", True)
    assert "profile_csv_import" in [r["action"] for r in list_logs(conn)]


def test_sample_csv_file_works(conn):
    from pathlib import Path
    sample = Path(__file__).resolve().parent.parent / "data" / "ornek_profiller.csv"
    result = ps.import_profiles_csv(conn, get_user(conn, "admin"), sample.read_bytes(), "ornek", "Sentetik", True)
    assert result["imported"] == 5 and len(result["rejected"]) == 1
