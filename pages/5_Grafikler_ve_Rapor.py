"""Plotly grafikleri ve CSV/PDF raporu. Tüm veriler veritabanından, demo sabiti kullanılmaz."""
import pandas as pd
import plotly.express as px
import streamlit as st

from components.common import apply_theme, get_db, require_login
from services import reporting as rpt

st.set_page_config(page_title="Grafikler ve Rapor", page_icon="📊", layout="wide")
apply_theme()
conn = get_db()
user = require_login()

st.title("📊 Analitik ve Raporlama")

metrics = rpt.summary_metrics(conn)
cols = st.columns(len(metrics))
for col, (label, value) in zip(cols, metrics.items()):
    col.metric(label, value)

st.divider()

# ---------- Eğitim öncesi/sonrası karşılaştırma ----------
st.subheader("Eğitim öncesi ve sonrası puan karşılaştırması")
pre_post = rpt.pre_vs_post_by_profile(conn)
if pre_post:
    df = pd.DataFrame(pre_post)
    df_long = df.melt(id_vars="label", value_vars=["pre", "post"], var_name="Aşama", value_name="Puan (%)")
    df_long["Aşama"] = df_long["Aşama"].map({"pre": "Eğitim öncesi", "post": "Eğitim sonrası"})
    fig = px.bar(df_long, x="label", y="Puan (%)", color="Aşama", barmode="group",
                 labels={"label": "Profil"})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Henüz hem eğitim öncesi hem eğitim sonrası testi tamamlamış profil yok.")

# ---------- Kategoriye göre başarı ----------
st.subheader("İkna tekniği kategorilerine göre başarı")
cat = rpt.category_success(conn)
if cat:
    df = pd.DataFrame(cat)
    df_long = df.melt(id_vars="category", value_vars=["correct", "incorrect"], var_name="Sonuç", value_name="Sayı")
    df_long["Sonuç"] = df_long["Sonuç"].map({"correct": "Doğru", "incorrect": "Yanlış"})
    fig = px.bar(df_long, x="category", y="Sayı", color="Sonuç", barmode="stack",
                 labels={"category": "Kategori"})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Henüz test cevabı yok.")

# ---------- Yanlış cevap dağılımı ----------
st.subheader("Yanlış cevapların dağılımı")
wrong = rpt.wrong_answer_distribution(conn)
if wrong:
    df = pd.DataFrame(wrong)
    fig = px.pie(df, names="category", values="incorrect")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Henüz yanlış cevap yok.")

# ---------- Zaman içindeki gelişim ----------
st.subheader("Zaman içindeki gelişim")
progress = rpt.progress_over_time(conn)
if progress:
    df = pd.DataFrame(progress)
    fig = px.line(df, x="day", y="percent", markers=True, labels={"day": "Tarih", "percent": "Ortalama doğru (%)"})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Henüz zaman içinde karşılaştırılacak veri yok.")

st.divider()

# ---------- Dışa aktarma ----------
st.subheader("Rapor dışa aktarma")
c1, c2 = st.columns(2)

with c1:
    st.write("**CSV raporu** (kategoriye göre başarı)")
    csv_bytes = rpt.export_csv(cat)
    st.download_button("📄 CSV indir", csv_bytes, "ikna_rapor.csv", "text/csv", disabled=not cat)

with c2:
    st.write("**PDF raporu** (özet)")
    try:
        pdf_bytes = rpt.export_pdf(conn)
        st.download_button("📕 PDF indir", pdf_bytes, "ikna_rapor.pdf", "application/pdf")
    except rpt.PdfUnavailable as exc:
        st.error(f"PDF oluşturulamadı: {exc}")
        st.caption("CSV raporu yukarıdan hâlâ indirilebilir.")
