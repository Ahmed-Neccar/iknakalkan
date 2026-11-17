"""İKNAKALKAN ana ekranı."""
import streamlit as st

import config
from components.common import apply_theme, get_db
from database import table_counts
from services.auth import authenticate, using_default_passwords

st.set_page_config(page_title="İKNAKALKAN | Araştırma Platformu", page_icon="🛡️", layout="wide")
apply_theme()
conn = get_db()

if "user" not in st.session_state:
    st.markdown("""
    <div class="ikna-hero">
      <div class="ikna-eyebrow">DEFENSIVE AI · RESEARCH WORKSPACE</div>
      <div class="ikna-title">İKNAKALKAN</div>
      <div class="ikna-sub">Sosyal mühendislik risklerini açıklanabilir biçimde inceleyin, güvenli simülasyonlarla farkındalığı ölçün ve eğitim etkisini raporlayın.</div>
      <span class="ikna-chip">🛡️ Savunma odaklı</span>
      <span class="ikna-chip">🔎 Açıklanabilir analiz</span>
      <span class="ikna-chip">📈 Ölçülebilir eğitim</span>
    </div>
    """, unsafe_allow_html=True)
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.markdown("### Araştırma için tasarlandı")
        st.markdown("""
        Bu çalışma alanı; sentetik veya açıkça izin verilmiş test verileriyle sosyal mühendislik göstergelerini incelemek ve güvenlik farkındalığını geliştirmek için hazırlanmıştır.
        """)
        st.markdown('<div class="ikna-card"><div class="ikna-card-title">Güvenli varsayılanlar</div><div class="ikna-card-text">Gerçek e-posta gönderimi varsayılan olarak kapalıdır. Analiz sonuçları karar desteğidir; kesin hüküm olarak değerlendirilmemelidir.</div></div>', unsafe_allow_html=True)
    with right:
        st.markdown("### Hesabınıza giriş yapın")
        with st.form("login", border=True):
            username = st.text_input("Kullanıcı adı", placeholder="Kullanıcı adınızı girin")
            password = st.text_input("Şifre", type="password", placeholder="Şifrenizi girin")
            submitted = st.form_submit_button("Güvenli giriş →", type="primary", use_container_width=True)
            if submitted:
                user = authenticate(conn, username, password)
                if user:
                    st.session_state["user"] = {"id": user["id"], "username": user["username"], "role": user["role"]}
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı.")
        if using_default_passwords(conn):
            with st.expander("Yerel demo hesapları"):
                st.warning("Yalnızca yerel demo için: admin/admin123, analyst/analyst123, viewer/viewer123. Dağıtım öncesinde parolaları değiştirin.")
    st.stop()

user = st.session_state["user"]
with st.sidebar:
    st.markdown("## 🛡️ İKNAKALKAN")
    st.caption("ARAŞTIRMA ÇALIŞMA ALANI")
    st.divider()
    st.markdown(f"**{user['username']}**")
    st.caption(f"Rol: {user['role']}")
    if st.button("Çıkış yap", use_container_width=True):
        del st.session_state["user"]
        st.rerun()
    st.divider()
    st.caption("Yalnızca sentetik / izinli test verileri kullanın.")

st.markdown("""
<div class="ikna-hero">
  <div class="ikna-eyebrow">DEFENSIVE AI · RESEARCH WORKSPACE</div>
  <div class="ikna-title">İKNAKALKAN <span style="color:#65e6c4">/</span> Kontrol Merkezi</div>
  <div class="ikna-sub">Açıklanabilir sosyal mühendislik analizi, güvenli simülasyonlar ve ölçülebilir farkındalık eğitimi için birleşik çalışma alanı.</div>
  <span class="ikna-chip">● Canlı olmayan güvenli demo</span>
  <span class="ikna-chip">🔎 Kanıta dayalı analiz</span>
  <span class="ikna-chip">📊 Araştırma ve raporlama</span>
</div>
""", unsafe_allow_html=True)

from services.mailer import real_send_ready
_ready = real_send_ready(conn)
status_cols = st.columns(3)
status_cols[0].markdown('<div class="ikna-card"><div class="ikna-section-label">Gönderim güvenliği</div><div class="ikna-card-title"><span class="ikna-status-dot"></span>Simülasyon öncelikli</div><div class="ikna-card-text">Gerçek gönderim yalnızca açıkça yapılandırılmış ve yetkilendirilmiş koşullarda mümkün olabilir.</div></div>', unsafe_allow_html=True)
status_cols[1].markdown(
    '<div class="ikna-card"><div class="ikna-section-label">Analiz motoru</div><div class="ikna-card-title">🧠 ' + ('Yerel Ollama yapılandırıldı' if config.llm_available() else 'Kural tabanlı analiz') + '</div><div class="ikna-card-text">Model erişimi analiz sırasında doğrulanır; kullanılamazsa sistemin geri dönüş davranışına bakın.</div></div>',
    unsafe_allow_html=True)
status_cols[2].markdown('<div class="ikna-card"><div class="ikna-section-label">Veri yönetişimi</div><div class="ikna-card-title">🔐 Sentetik / izinli veri</div><div class="ikna-card-text">Test kapsamını dar tutun ve kişisel verileri raporlara eklemeyin.</div></div>', unsafe_allow_html=True)

st.markdown("### Çalışma alanı özeti")
counts = table_counts(conn)
cols = st.columns(min(5, max(1, len(counts))))
for i, (table, n) in enumerate(counts.items()):
    cols[i % len(cols)].metric(table.replace("_", " ").title(), n)

st.markdown("### Araştırma modülleri")
modules = [
    ("01", "Profiller", "Sentetik test profillerini ve izinli veri kümelerini yönetin.", "Profil yönetimi ve CSV içe aktarma"),
    ("02", "Senaryolar", "Senaryo oluşturun, mesajları inceleyin ve ikna göstergelerini analiz edin.", "Senaryo ve analiz"),
    ("03", "Onay ve gönderim", "Güvenli simülasyon akışını ve onay adımlarını izleyin.", "Kontrollü iş akışı"),
    ("04", "Eğitim", "Ön test / son test sonuçlarıyla farkındalık değişimini ölçün.", "Eğitim ve kişiselleştirme"),
    ("05", "Grafikler ve rapor", "Sonuçları görselleştirin ve araştırma çıktıları üretin.", "Analitik ve raporlama"),
    ("06", "Ayarlar", "Uygulama tercihlerini ve güvenli çalışma sınırlarını yönetin.", "Yapılandırma"),
]
for row_start in range(0, len(modules), 3):
    card_cols = st.columns(3, gap="medium")
    for col, item in zip(card_cols, modules[row_start:row_start+3]):
        num, title, desc, tag = item
        col.markdown(f'<div class="ikna-card"><div class="ikna-section-label">MODÜL {num}</div><div class="ikna-card-title">{title}</div><div class="ikna-card-text">{desc}<br><br><span style="color:#65e6c4">↗ {tag}</span></div></div>', unsafe_allow_html=True)
    st.write("")
st.caption("İKNAKALKAN · Üniversite düzeyinde güvenlik farkındalığı ve açıklanabilir analiz araştırması")
