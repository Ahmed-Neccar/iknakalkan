"""Profil yönetimi + CSV içe aktarma. Tüm kurallar burada; arayüz sadece bu fonksiyonları çağırır."""
import csv
import io
import re
from datetime import datetime, timezone

import config
from services.audit import log_action
from services.auth import require_permission

MAX_LEN = {"label": 100, "role_title": 100, "department": 100, "allowed_contact": 150}
MAX_CSV_BYTES = 1_000_000
MAX_CSV_ROWS = 1000
EMAIL_RE = re.compile(r"^[^@\s]+@([^@\s]+\.[^@\s]+)$")

# CSV başlık takma adları (Türkçe başlıklar da kabul edilir)
HEADER_ALIASES = {
    "label": "label", "ad_etiketi": "label", "etiket": "label",
    "role_title": "role_title", "gorev": "role_title", "görev": "role_title",
    "department": "department", "departman": "department",
    "allowed_contact": "allowed_contact", "iletisim": "allowed_contact", "e-posta": "allowed_contact",
}


class ValidationError(ValueError):
    """Girdi geçersiz. Mesaj kullanıcıya gösterilebilir (gizli bilgi içermez)."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def validate_profile(label, role_title="", department="", allowed_contact="") -> dict:
    data = {
        "label": (label or "").strip(),
        "role_title": (role_title or "").strip(),
        "department": (department or "").strip(),
        "allowed_contact": (allowed_contact or "").strip(),
    }
    if not data["label"]:
        raise ValidationError("Ad etiketi boş olamaz.")
    for field, limit in MAX_LEN.items():
        if len(data[field]) > limit:
            raise ValidationError(f"'{field}' en fazla {limit} karakter olabilir.")
    contact = data["allowed_contact"]
    if contact:
        match = EMAIL_RE.match(contact)
        if not match:
            raise ValidationError("İletişim bilgisi geçerli bir e-posta adresi olmalı.")
        domain = match.group(1).lower()
        if domain not in config.allowed_email_domains():
            allowed = ", ".join(sorted(config.allowed_email_domains()))
            raise ValidationError(f"'{domain}' izinli test alanları arasında değil. İzinli alanlar: {allowed}")
    return data


def _insert(conn, data, data_source, data_origin, imported_at):
    cur = conn.execute(
        "INSERT INTO profiles (label, role_title, department, allowed_contact, data_source, data_origin, "
        "is_synthetic, imported_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
        (data["label"], data["role_title"], data["department"], data["allowed_contact"],
         data_source, data_origin, imported_at),
    )
    return cur.lastrowid


def create_profile(conn, user, label, role_title="", department="", allowed_contact=""):
    require_permission(conn, user, "edit")
    data = validate_profile(label, role_title, department, allowed_contact)
    pid = _insert(conn, data, "manual", "Elle girildi (sentetik)", None)
    conn.commit()
    log_action(conn, user["id"], "profile_create", "profiles", pid, data["label"])
    return pid


def get_profile(conn, profile_id):
    return conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()


def list_profiles(conn, search=None):
    if search and search.strip():
        like = f"%{search.strip()}%"
        return conn.execute(
            "SELECT * FROM profiles WHERE label LIKE ? OR department LIKE ? OR role_title LIKE ? ORDER BY id DESC",
            (like, like, like),
        ).fetchall()
    return conn.execute("SELECT * FROM profiles ORDER BY id DESC").fetchall()


def update_profile(conn, user, profile_id, label, role_title="", department="", allowed_contact=""):
    require_permission(conn, user, "edit")
    if get_profile(conn, profile_id) is None:
        raise ValidationError("Profil bulunamadı.")
    data = validate_profile(label, role_title, department, allowed_contact)
    conn.execute(
        "UPDATE profiles SET label=?, role_title=?, department=?, allowed_contact=?, "
        "updated_at=datetime('now') WHERE id=?",
        (data["label"], data["role_title"], data["department"], data["allowed_contact"], profile_id),
    )
    conn.commit()
    log_action(conn, user["id"], "profile_update", "profiles", profile_id, data["label"])


def delete_profile(conn, user, profile_id):
    require_permission(conn, user, "delete")  # sadece admin
    profile = get_profile(conn, profile_id)
    if profile is None:
        raise ValidationError("Profil bulunamadı.")
    conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    conn.commit()
    log_action(conn, user["id"], "profile_delete", "profiles", profile_id, profile["label"])


def import_profiles_csv(conn, user, raw, source_name, origin, confirm_authorized):
    """CSV'den profil içe aktarır. Kaynak, veri kökeni ve zaman damgası her kayda yazılır.
    Hatalı satırlar atlanır ve nedenleriyle birlikte döndürülür; geçerli satırlar eklenir."""
    require_permission(conn, user, "edit")
    if not confirm_authorized:
        raise ValidationError("İçe aktarmadan önce verilerin sentetik veya izinli test verisi olduğunu onaylamalısınız.")
    source_name, origin = (source_name or "").strip(), (origin or "").strip()
    if not source_name or not origin:
        raise ValidationError("Kaynak adı ve veri kökeni boş olamaz.")

    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if len(raw) > MAX_CSV_BYTES:
        raise ValidationError("CSV dosyası çok büyük (en fazla 1 MB).")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("CSV dosyası UTF-8 olarak okunamadı.")

    reader = csv.DictReader(io.StringIO(text))
    mapping = {}
    for header in reader.fieldnames or []:
        key = HEADER_ALIASES.get((header or "").strip().lower())
        if key:
            mapping[header] = key
    if "label" not in mapping.values():
        raise ValidationError("CSV'de 'label' (veya 'ad_etiketi') sütunu bulunamadı.")

    imported_at = _now()
    data_source = f"csv_import:{source_name}"[:150]
    imported, rejected = 0, []
    for row_no, row in enumerate(reader, start=2):  # 1. satır başlık
        if row_no - 1 > MAX_CSV_ROWS:
            raise ValidationError(f"CSV en fazla {MAX_CSV_ROWS} satır içerebilir.")
        values = {mapping[h]: v for h, v in row.items() if h in mapping}
        try:
            data = validate_profile(values.get("label"), values.get("role_title"),
                                    values.get("department"), values.get("allowed_contact"))
        except ValidationError as exc:
            rejected.append((row_no, str(exc)))
            continue
        _insert(conn, data, data_source, origin, imported_at)
        imported += 1
    conn.commit()
    log_action(conn, user["id"], "profile_csv_import", "profiles", None,
               f"kaynak={source_name}; eklenen={imported}; reddedilen={len(rejected)}")
    return {"imported": imported, "rejected": rejected}
