"""Farkındalık eğitimi: soru bankası, eğitim öncesi/sonrası test, puanlama."""
from services.audit import log_action

CATEGORIES = ["otorite", "aciliyet", "sosyal_kanit", "korku_tehdit", "odul_kazanc", "merak", "guven_suistimali"]

SEED_QUESTIONS = [
    ("otorite", "\"IT Departmanı Müdürü\" imzalı bir mail, şifrenizi hemen paylaşmanızı istiyor. Ne yaparsınız?",
     ["Direkt paylaşırım, yetkili biri istiyor", "Göndereni resmi bir kanaldan (telefonla) doğrularım",
      "Hiçbir şey yapmam, mail'i yok sayarım"], 1,
     "Otorite taklidi yaygın bir tekniktir; gerçek yetkililer şifre istemez, her zaman doğrulama yapılmalı."),
    ("otorite", "CEO'nun adını kullanan bir mail acil bir ödeme talep ediyor. En doğru tepki hangisidir?",
     ["Hemen ödemeyi yaparım, CEO istiyor", "Finans ekibinden ayrı bir kanalla teyit alırım",
      "Mail'i direkt silerim"], 1,
     "Üst düzey yönetici adı kullanılarak yapılan taleplerde bile bağımsız doğrulama şarttır."),

    ("aciliyet", "Bir mail \"Hesabınız 2 saat içinde kapatılacak, hemen tıklayın\" diyor. Bu ne işareti olabilir?",
     ["Normal bir sistem bildirimi", "Aciliyet baskısı yaratan bir oltalama taktiği", "Gerçek bir hata mesajı"], 1,
     "Kısa süre baskısı, kurbanı düşünmeden hareket etmeye zorlamak için kullanılan klasik bir tekniktir."),
    ("aciliyet", "\"Son 10 dakika!\" ifadesi içeren bir mail aldığınızda ne yapmalısınız?",
     ["Zaman kaybetmeden tıklarım", "Durur, göndereni ve bağlantıyı dikkatle incelerim",
      "Arkadaşlarıma yönlendiririm"], 1,
     "Baskı hissi oluştuğunda durup doğrulamak, oltalamaya karşı en etkili savunmadır."),

    ("sosyal_kanit", "\"Departmanınızdaki herkes bu formu doldurdu\" diyen bir mail görürseniz ne düşünmelisiniz?",
     ["Herkes yaptıysa ben de yapmalıyım", "Bu iddia doğrulanamaz, bağımsız kontrol etmeliyim",
      "Böyle mailler her zaman güvenlidir"], 1,
     "'Herkes yaptı' iddiası doğrulanamayan sosyal kanıt baskısıdır, tek başına güven nedeni olmamalı."),
    ("sosyal_kanit", "Bir mail \"500 çalışan zaten kaydoldu\" diyor ama siz bu kampanyadan haberdar değilsiniz. Ne yapmalısınız?",
     ["Geri kalmamak için hemen kaydolurum", "Kampanyayı resmi duyuru kanallarından teyit ederim",
      "Mail'i meslektaşlarıma iletirim"], 1,
     "Haberdar olmadığınız bir kampanya iddiası, resmi kanaldan doğrulanmadan kabul edilmemelidir."),

    ("korku_tehdit", "\"Hesabınız yasal işlem görecek\" diyen bir mail aldınız. Doğru yaklaşım nedir?",
     ["Panikleyip hemen linke tıklarım", "Sakin kalıp göndereni ve adresini kontrol ederim",
      "Hemen parama el konulacağını düşünürüm"], 1,
     "Tehdit dili panik yaratmak için kullanılır; sakin kalıp doğrulama yapmak en güvenli yoldur."),
    ("korku_tehdit", "Bir mail, işlem yapmazsanız \"erişiminizin kalıcı olarak silineceğini\" söylüyor. Ne yapmalısınız?",
     ["Hemen istenen bilgiyi girerim", "BT/Güvenlik birimine danışmadan işlem yapmam",
      "Hesabımı kendim silerim"], 1,
     "Kalıcı kayıp tehdidi klasik bir korkutma taktiğidir; resmi birime danışmadan hareket edilmemelidir."),

    ("odul_kazanc", "\"Tebrikler, hediye kazandınız!\" diyen beklenmedik bir mail aldınız. Ne yapmalısınız?",
     ["Hemen bağlantıya tıklarım", "Kaynağını doğrulamadan hiçbir bilgi girmem", "Arkadaşlarımla paylaşırım"], 1,
     "Beklenmeyen ödül vaatleri, kişisel bilgi çalmak için sık kullanılan bir yemdir."),
    ("odul_kazanc", "Katılmadığınız bir çekilişten \"ödül kazandınız\" maili gelirse ne yapmalısınız?",
     ["Bilgilerimi girip ödülümü alırım", "Böyle bir çekilişe katılmadığım için şüpheyle yaklaşırım",
      "Hemen arkadaşımı etiketlerim"], 1,
     "Katılmadığınız bir çekilişten kazanma bildirimi almak, oltalama girişiminin güçlü bir işaretidir."),

    ("merak", "\"Maaş zammı listesi ektedir, hemen açın\" diyen bir mail aldınız. En doğru davranış nedir?",
     ["Merakla hemen açarım", "Beklenmeyen eki açmadan göndereni doğrularım", "Eki indirip herkese gönderirim"], 1,
     "Merak uyandıran başlıklar, zararlı ekleri açtırmak için sıkça kullanılır."),
    ("merak", "\"Sizinle ilgili gizli bir belge\" diyen beklenmedik bir mail aldığınızda ne yapmalısınız?",
     ["Hemen merakla açarım", "Göndereni doğrulamadan açmam", "Meslektaşlarıma yönlendiririm"], 1,
     "Kişisel merakı hedef alan mailler, zararlı yazılım bulaştırmak için yaygın bir yöntemdir."),

    ("guven_suistimali", "\"Bildiğiniz üzere her zamanki gibi\" diye başlayan tanıdık tonlu bir mail aldınız ama gönderen adresi garip. Ne yapmalısınız?",
     ["Tanıdık tona güvenip devam ederim", "Gönderen adresini ve imzayı dikkatle kontrol ederim",
      "Hemen cevap yazarım"], 1,
     "Tanıdık ton, güven kazanmak için taklit edilebilir; adres her zaman ayrıca doğrulanmalıdır."),
    ("guven_suistimali", "Daha önce iletişim kurduğunuzu iddia eden ama hatırlamadığınız bir kişiden mail geldi. Ne yapmalısınız?",
     ["Hatırlamasam da güvenirim", "Önceki yazışmaları kontrol eder, doğrulamadan işlem yapmam",
      "Direkt istenen bilgiyi gönderirim"], 1,
     "Sahte tanıdıklık iddiaları güven suistimalinin bir parçasıdır; geçmiş kayıtlar kontrol edilmelidir."),
]


def seed_questions_if_empty(conn):
    """Soru bankası boşsa örnek soruları ekler. Tekrar çağrılması güvenlidir (idempotent)."""
    if conn.execute("SELECT COUNT(*) FROM training_questions").fetchone()[0] > 0:
        return 0
    import json
    for category, question_text, options, correct_index, explanation in SEED_QUESTIONS:
        conn.execute(
            "INSERT INTO training_questions (category, question_text, options_json, correct_index, explanation, phase) "
            "VALUES (?, ?, ?, ?, ?, 'both')",
            (category, question_text, json.dumps(options, ensure_ascii=False), correct_index, explanation),
        )
    conn.commit()
    return len(SEED_QUESTIONS)


def list_questions(conn, phase=None):
    if phase:
        return conn.execute(
            "SELECT * FROM training_questions WHERE phase = ? OR phase = 'both' ORDER BY id", (phase,)
        ).fetchall()
    return conn.execute("SELECT * FROM training_questions ORDER BY id").fetchall()


def get_question(conn, question_id):
    return conn.execute("SELECT * FROM training_questions WHERE id = ?", (question_id,)).fetchone()


class ValidationError(ValueError):
    pass


def record_attempt(conn, user, profile_id, question_id, phase, selected_index):
    """Bir soruya verilen cevabı kaydeder. Puan gerçek cevaptan hesaplanır, burada sabitlenmez."""
    if phase not in ("pre", "post"):
        raise ValidationError("Geçersiz aşama (phase); 'pre' veya 'post' olmalı.")
    question = get_question(conn, question_id)
    if question is None:
        raise ValidationError("Soru bulunamadı.")
    profile_row = conn.execute("SELECT id FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    if profile_row is None:
        raise ValidationError("Profil bulunamadı.")
    is_correct = 1 if int(selected_index) == question["correct_index"] else 0
    conn.execute(
        "INSERT INTO training_attempts (profile_id, question_id, phase, selected_index, is_correct) "
        "VALUES (?, ?, ?, ?, ?)",
        (profile_id, question_id, phase, selected_index, is_correct),
    )
    conn.commit()
    log_action(conn, user["id"] if user else None, "training_attempt", "training_attempts", question_id,
               f"profile={profile_id}; phase={phase}; correct={is_correct}")
    return bool(is_correct)


def compute_score(conn, profile_id, phase):
    """Verilen aşama için doğru cevap yüzdesini döner. Hiç deneme yoksa None döner."""
    rows = conn.execute(
        "SELECT is_correct FROM training_attempts WHERE profile_id = ? AND phase = ?", (profile_id, phase)
    ).fetchall()
    if not rows:
        return None
    correct = sum(r["is_correct"] for r in rows)
    return {"total": len(rows), "correct": correct, "percent": round(100 * correct / len(rows), 1)}


def category_breakdown(conn, profile_id, phase=None):
    """Kategoriye göre doğru/yanlış sayısı. phase verilmezse tüm denemeler dikkate alınır."""
    query = (
        "SELECT q.category AS category, a.is_correct AS is_correct FROM training_attempts a "
        "JOIN training_questions q ON q.id = a.question_id WHERE a.profile_id = ?"
    )
    params = [profile_id]
    if phase:
        query += " AND a.phase = ?"
        params.append(phase)
    rows = conn.execute(query, params).fetchall()
    breakdown = {}
    for r in rows:
        d = breakdown.setdefault(r["category"], {"correct": 0, "incorrect": 0})
        d["correct" if r["is_correct"] else "incorrect"] += 1
    return breakdown


def progress_over_time(conn, profile_id):
    """Profilin zaman içindeki puanlarını (her deneme sırasıyla) döner, grafik için kullanılır."""
    return conn.execute(
        "SELECT created_at, phase, is_correct FROM training_attempts WHERE profile_id = ? ORDER BY created_at",
        (profile_id,),
    ).fetchall()
