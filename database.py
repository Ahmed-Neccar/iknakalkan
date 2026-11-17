"""SQLite veritabanı: tablolar ilk çalıştırmada otomatik oluşturulur."""
import sqlite3
from pathlib import Path

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'analyst', 'viewer')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL CHECK (length(trim(label)) > 0),   -- ad etiketi (sentetik)
    role_title TEXT,                                        -- görev
    department TEXT,
    allowed_contact TEXT,                                   -- izin verilen iletişim bilgisi
    data_source TEXT NOT NULL DEFAULT 'manual',             -- manual / csv_import
    data_origin TEXT,                                       -- veri kökeni
    is_synthetic INTEGER NOT NULL DEFAULT 1 CHECK (is_synthetic IN (0, 1)),
    imported_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    description TEXT,
    message_subject TEXT,
    message_body TEXT,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'pending_approval', 'approved', 'skipped', 'queued', 'completed')),
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER REFERENCES scenarios(id) ON DELETE CASCADE,
    message_text TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('llm', 'rule_based', 'demo')),
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'skipped')),
    decided_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    scope_verified INTEGER NOT NULL DEFAULT 0 CHECK (scope_verified IN (0, 1)),
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS simulation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('queued', 'simulated', 'failed')),
    is_real_send INTEGER NOT NULL DEFAULT 0 CHECK (is_real_send IN (0, 1)),
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS training_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,                                 -- ikna tekniği kategorisi
    question_text TEXT NOT NULL,
    options_json TEXT NOT NULL,                             -- seçenek listesi (JSON)
    correct_index INTEGER NOT NULL CHECK (correct_index >= 0),
    explanation TEXT NOT NULL,
    phase TEXT NOT NULL DEFAULT 'both' CHECK (phase IN ('pre', 'post', 'both')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS training_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES training_questions(id) ON DELETE CASCADE,
    phase TEXT NOT NULL CHECK (phase IN ('pre', 'post')),
    selected_index INTEGER NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS training_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    material TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS authorized_recipients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    label TEXT,
    added_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity TEXT,
    entity_id INTEGER,
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

TABLES = [
    "users", "profiles", "scenarios", "analyses", "approvals",
    "simulation_events", "training_questions", "training_attempts",
    "training_recommendations", "audit_logs", "app_settings", "authorized_recipients",
]


def get_connection(db_path=None) -> sqlite3.Connection:
    """Bağlantı açar; yabancı anahtar kontrolü her bağlantıda açılmalıdır."""
    path = Path(db_path) if db_path else config.get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None) -> sqlite3.Connection:
    """Tabloları (yoksa) oluşturur ve varsayılan demo kullanıcılarını ekler. Tekrar çalıştırılabilir."""
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    from services.auth import ensure_default_users  # döngüsel import olmasın diye burada
    ensure_default_users(conn)
    return conn


def table_counts(conn: sqlite3.Connection) -> dict:
    """Her tablodaki kayıt sayısı (ana sayfa için)."""
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
