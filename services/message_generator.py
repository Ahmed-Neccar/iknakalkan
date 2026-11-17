"""Profile özgü oltalama (phishing) örnek mesajı üretir. LLM yoksa şablon tabanlı,
her profile göre kişiselleştirilmiş bir taslak oluşturur; LLM eklenirse _call_llm kullanılacaktır."""
import random

import config

TEMPLATES = [
    {
        "subject": "[Acil] Hesap Doğrulaması Gerekiyor – {department}",
        "body": (
            "Sayın {label},\n\n"
            "BT Departmanı olarak, {department} biriminde {role_title} olarak görev yapan "
            "hesabınızda olağan dışı bir giriş denemesi tespit ettik. Güvenliğiniz için hesabınızın "
            "24 saat içinde doğrulanması gerekmektedir. Aksi takdirde erişiminiz geçici olarak kısıtlanacaktır.\n\n"
            "Doğrulama için lütfen aşağıdaki bağlantıyı kullanınız:\n"
            "[GÜVENLİ DOĞRULAMA BAĞLANTISI – SİMÜLASYON]\n\n"
            "Saygılarımızla,\nBT Destek Ekibi"
        ),
    },
    {
        "subject": "{label} - {department} Birimi İçin Önemli Duyuru",
        "body": (
            "Merhaba {label},\n\n"
            "Yönetim, {department} biriminde bu hafta yapılan bir değerlendirme sonucunda "
            "{role_title} pozisyonundaki çalışanlar için güncellenmiş bordro belgelerini paylaştı. "
            "Belgenin yalnızca bugün erişime açık olduğunu hatırlatmak isteriz.\n\n"
            "Belgeyi görüntülemek için: [BELGE BAĞLANTISI – SİMÜLASYON]\n\n"
            "İyi çalışmalar,\nİnsan Kaynakları"
        ),
    },
    {
        "subject": "Ödeme Onayı Bekliyor – {department}",
        "body": (
            "Sayın {label},\n\n"
            "{department} birimi adına oluşturulan bir ödeme talebi onayınızı bekliyor. "
            "Talebin bugün saat 17:00'ye kadar onaylanmaması durumunda işlem iptal edilecek ve "
            "yeniden başlatılması gerekecektir.\n\n"
            "Onaylamak için: [ONAY BAĞLANTISI – SİMÜLASYON]\n\n"
            "Saygılarımızla,\nFinans Operasyon"
        ),
    },
]


def _call_llm(profile: dict) -> dict:
    raise NotImplementedError("Bu ortamda gerçek bir LLM API çağrısı yapılmamıştır (API anahtarı entegrasyonu geliştirici tarafından eklenmelidir).")


def generate_message(profile) -> dict:
    """profile: veritabanı satırı (label, role_title, department). Döner: {subject, body, mode}."""
    fields = {
        "label": profile["label"],
        "role_title": profile["role_title"] or "çalışan",
        "department": profile["department"] or "ilgili birim",
    }
    if config.llm_available():
        try:
            result = _call_llm(fields)
            result["mode"] = "llm"
            return result
        except Exception as exc:
            tpl = random.choice(TEMPLATES)
            return {
                "subject": tpl["subject"].format(**fields),
                "body": tpl["body"].format(**fields),
                "mode": "template_fallback",
                "note": f"LLM üretimi başarısız oldu, şablon tabanlı moda geçildi: {exc}",
            }
    tpl = random.choice(TEMPLATES)
    return {
        "subject": tpl["subject"].format(**fields),
        "body": tpl["body"].format(**fields),
        "mode": "template",
        "note": "LLM anahtarı tanımlı değil; mesaj şablon tabanlı üretildi (demo modu).",
    }
