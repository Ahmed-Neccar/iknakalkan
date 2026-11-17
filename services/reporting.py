"""Analitik ve raporlama. Tüm veriler veritabanından okunur; sabit sayı yalnızca
açıkça 'demo' olarak işaretlenen yerlerde kullanılabilir (burada kullanılmıyor)."""
import csv
import io


def pre_vs_post_by_profile(conn):
    """Her profil için eğitim öncesi/sonrası doğru yüzdesi. Her iki aşamayı da tamamlamış profiller döner."""
    rows = conn.execute(
        "SELECT a.profile_id AS profile_id, p.label AS label, a.phase AS phase, "
        "SUM(a.is_correct) AS correct, COUNT(*) AS total "
        "FROM training_attempts a JOIN profiles p ON p.id = a.profile_id "
        "GROUP BY a.profile_id, a.phase"
    ).fetchall()
    by_profile = {}
    for r in rows:
        d = by_profile.setdefault(r["profile_id"], {"label": r["label"], "pre": None, "post": None})
        percent = round(100 * r["correct"] / r["total"], 1) if r["total"] else None
        d[r["phase"]] = percent
    return [v for v in by_profile.values() if v["pre"] is not None and v["post"] is not None]


def category_success(conn):
    """Tüm profiller genelinde ikna tekniği kategorisine göre doğru/yanlış sayısı."""
    rows = conn.execute(
        "SELECT q.category AS category, "
        "SUM(a.is_correct) AS correct, SUM(1 - a.is_correct) AS incorrect, COUNT(*) AS total "
        "FROM training_attempts a JOIN training_questions q ON q.id = a.question_id "
        "GROUP BY q.category ORDER BY q.category"
    ).fetchall()
    return [dict(r) for r in rows]


def wrong_answer_distribution(conn):
    """Yanlış cevapların kategoriye göre dağılımı (yalnızca yanlışlar)."""
    return [{"category": r["category"], "incorrect": r["incorrect"]}
            for r in category_success(conn) if r["incorrect"] > 0]


def progress_over_time(conn):
    """Tarihe göre (gün bazında) ortalama doğru yüzdesi, tüm profiller genelinde."""
    rows = conn.execute(
        "SELECT substr(created_at, 1, 10) AS day, "
        "SUM(is_correct) AS correct, COUNT(*) AS total "
        "FROM training_attempts GROUP BY day ORDER BY day"
    ).fetchall()
    return [{"day": r["day"], "percent": round(100 * r["correct"] / r["total"], 1)} for r in rows]


def completed_trainings_count(conn):
    """Hem 'pre' hem 'post' aşamasını tamamlamış profil sayısı."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM ("
        "  SELECT profile_id FROM training_attempts WHERE phase='pre' "
        "  INTERSECT "
        "  SELECT profile_id FROM training_attempts WHERE phase='post'"
        ")"
    ).fetchone()
    return row["n"]


def summary_metrics(conn):
    return {
        "Tamamlanan eğitim sayısı (öncesi+sonrası)": completed_trainings_count(conn),
        "Toplam senaryo sayısı": conn.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0],
        "Toplam analiz sayısı": conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0],
        "Toplam test denemesi": conn.execute("SELECT COUNT(*) FROM training_attempts").fetchone()[0],
        "Toplam profil sayısı": conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0],
    }


# ---------- Dışa aktarma ----------

def export_csv(rows: list[dict]) -> bytes:
    """Satır listesini CSV bayt dizisine çevirir. Boş listede yalnızca başlık yoksa boş döner."""
    if not rows:
        return b""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


class PdfUnavailable(RuntimeError):
    """PDF kütüphanesi (reportlab) bu ortamda kurulu değil veya PDF oluşturulamadı."""


def export_pdf(conn) -> bytes:
    """Özet rapor PDF'i üretir. reportlab yoksa/PDF oluşturulamazsa PdfUnavailable fırlatır;
    bu durumda çağıran taraf CSV raporunu sunmaya devam etmelidir."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise PdfUnavailable(f"reportlab kütüphanesi kurulu değil: {exc}")

    try:
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4
        y = height - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "İkna Analiz Platformu - Özet Rapor")
        y -= 30
        c.setFont("Helvetica", 11)
        for label, value in summary_metrics(conn).items():
            c.drawString(40, y, f"{label}: {value}")
            y -= 18
        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Kategoriye göre başarı")
        y -= 20
        c.setFont("Helvetica", 10)
        for row in category_success(conn):
            c.drawString(50, y, f"{row['category']}: doğru {row['correct']}, yanlış {row['incorrect']}")
            y -= 15
            if y < 50:
                c.showPage()
                y = height - 50
        c.save()
        return buf.getvalue()
    except Exception as exc:
        raise PdfUnavailable(f"PDF oluşturulurken hata oluştu: {exc}")
