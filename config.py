"""Uygulama ayarları. Tüm gizli değerler ortam değişkenlerinden okunur, kaynak koda yazılmaz."""
import os
from pathlib import Path

try:  # .env dosyası varsa oku (python-dotenv isteğe bağlıdır)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent


def get_db_path() -> Path:
    """Veritabanı yolu: IKNA_DB_PATH varsa onu, yoksa data/ikna.db kullanılır."""
    custom = os.environ.get("IKNA_DB_PATH", "").strip()
    return Path(custom) if custom else BASE_DIR / "data" / "ikna.db"


def llm_available() -> bool:
    """Yerel Ollama servisi ayarlandı mı? API anahtarı varlığı canlı model kanıtı değildir."""
    return os.environ.get("IKNA_LLM_PROVIDER", "ollama").strip().lower() == "ollama"


def ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "qwen2.5:3b").strip() or "qwen2.5:3b"



def allowed_email_domains() -> set:
    """Profillere yalnızca bu (sentetik/test) alan adlarındaki e-postalar eklenebilir."""
    raw = os.environ.get("ALLOWED_EMAIL_DOMAINS", "example.com,example.org,example.net,test.local")
    return {d.strip().lower() for d in raw.split(",") if d.strip()}


# ---- E-posta gönderim ayarları (SMTP bilgileri yalnızca ortam değişkenlerinden okunur) ----

def smtp_config():
    """SMTP bağlantı bilgileri. Parola dahil hiçbiri koda veya veritabanına yazılmaz."""
    return {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587") or "587"),
        "username": os.environ.get("SMTP_USERNAME", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", "").strip(),
        "use_tls": os.environ.get("SMTP_USE_TLS", "true").strip().lower() == "true",
    }


def smtp_configured() -> bool:
    c = smtp_config()
    return bool(c["host"] and c["username"] and c["password"])


def real_send_env_allowed() -> bool:
    """Ortam değişkeni seviyesinde kilit. Veritabanındaki anahtarla birlikte İKİSİ de açık olmalı."""
    return os.environ.get("ALLOW_REAL_SEND", "false").strip().lower() == "true"
