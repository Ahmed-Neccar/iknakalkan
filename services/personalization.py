"""Kişiselleştirilmiş eğitim önerileri. Ayrı bir modül: kullanıcının hata yaptığı ikna
kategorilerini belirler ve bu kategorilere göre öneri üretir. Kurallar sabittir ama
girdi (hangi kategorilerde hata yapıldığı) gerçek kullanıcı performansından gelir."""
from services.analysis import TECHNIQUES
from services.audit import log_action
from services.training import category_breakdown

MATERIALS = {
    category: f"{category.replace('_', ' ').title()} tekniğini tanıma eğitimi: {spec['defense']}"
    for category, spec in TECHNIQUES.items()
}


def weak_categories(conn, profile_id, min_incorrect=1):
    """Hiç doğru cevaplanmamış ya da yanlış sayısı doğru sayısına eşit/daha fazla olan kategoriler."""
    breakdown = category_breakdown(conn, profile_id)
    weak = []
    for category, counts in breakdown.items():
        if counts["incorrect"] >= min_incorrect and counts["incorrect"] >= counts["correct"]:
            weak.append(category)
    return weak


def generate_recommendations(conn, user, profile_id):
    """Zayıf kategoriler için öneri oluşturur ve veritabanına kaydeder. Var olan aynı kategorideki
    eski önerinin üzerine yazmaz, yeni bir kayıt ekler (geçmiş izlenebilir kalsın diye)."""
    categories = weak_categories(conn, profile_id)
    created = []
    for category in categories:
        material = MATERIALS.get(category, f"{category} konusunda ek eğitim önerilir.")
        reason = "Bu kategoride yapılan sorularda yanlış cevap sayısı doğru cevap sayısına eşit veya fazla."
        cur = conn.execute(
            "INSERT INTO training_recommendations (profile_id, category, material, reason) VALUES (?, ?, ?, ?)",
            (profile_id, category, material, reason),
        )
        created.append(cur.lastrowid)
    conn.commit()
    if created:
        log_action(conn, user["id"] if user else None, "recommendation_generate", "training_recommendations",
                   None, f"profile={profile_id}; categories={categories}")
    return categories


def list_recommendations(conn, profile_id):
    return conn.execute(
        "SELECT * FROM training_recommendations WHERE profile_id = ? ORDER BY id DESC", (profile_id,)
    ).fetchall()
