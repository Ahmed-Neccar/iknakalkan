"""Farkındalık eğitimi: eğitim öncesi/sonrası test, puanlama, kişiselleştirilmiş öneriler."""
import json

import pandas as pd
import streamlit as st

from components.common import apply_theme, get_db, require_login, show_flash
from services import personalization as pers
from services import profiles as ps
from services import training as tr

st.set_page_config(page_title="Eğitim", page_icon="🎓", layout="wide")
apply_theme()
conn = get_db()
user = require_login()
tr.seed_questions_if_empty(conn)

st.title("🎓 Farkındalık Eğitimi")
show_flash()

profile_rows = ps.list_profiles(conn)
if not profile_rows:
    st.warning("Önce 'Profiller' sayfasından en az bir profil ekleyin.")
    st.stop()

options = {r["id"]: f"#{r['id']} – {r['label']}" for r in profile_rows}
profile_id = st.selectbox("Profil seç (test bu profil adına kaydedilecek)", list(options), format_func=lambda i: options[i])

tab_test, tab_results, tab_reco = st.tabs(["📝 Test", "📊 Sonuçlar", "🎯 Kişiselleştirilmiş Öneriler"])

with tab_test:
    phase = st.radio("Aşama", ["pre", "post"], format_func=lambda p: "Eğitim öncesi" if p == "pre" else "Eğitim sonrası", horizontal=True)
    questions = tr.list_questions(conn, phase)
    st.caption(f"{len(questions)} soru. Her soruyu cevaplayıp 'Kaydet' deyin.")
    for q in questions:
        opts = json.loads(q["options_json"])
        key = f"q_{q['id']}_{phase}_{profile_id}"
        with st.form(key):
            st.write(f"**{q['question_text']}**")
            choice = st.radio("Cevabınız", list(range(len(opts))), format_func=lambda i: opts[i], key=key + "_radio")
            if st.form_submit_button("Kaydet"):
                correct = tr.record_attempt(conn, user, profile_id, q["id"], phase, choice)
                if correct:
                    st.success("Doğru!")
                else:
                    st.error(f"Yanlış. {q['explanation']}")

with tab_results:
    pre = tr.compute_score(conn, profile_id, "pre")
    post = tr.compute_score(conn, profile_id, "post")
    c1, c2 = st.columns(2)
    c1.metric("Eğitim öncesi puan", f"%{pre['percent']}" if pre else "Henüz yok", f"{pre['correct']}/{pre['total']}" if pre else "")
    c2.metric("Eğitim sonrası puan", f"%{post['percent']}" if post else "Henüz yok", f"{post['correct']}/{post['total']}" if post else "")
    if pre and post:
        diff = post["percent"] - pre["percent"]
        st.info(f"Gelişim: {'+' if diff >= 0 else ''}{diff:.1f} puan")

    st.subheader("Kategoriye göre sonuçlar")
    breakdown = tr.category_breakdown(conn, profile_id)
    if breakdown:
        df = pd.DataFrame([
            {"Kategori": c, "Doğru": v["correct"], "Yanlış": v["incorrect"]} for c, v in breakdown.items()
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("Henüz test cevabı yok.")

with tab_reco:
    st.caption("Kategori bazında yanlış sayısı doğru sayısına eşit veya fazlaysa, o kategori 'zayıf' kabul edilir ve öneri üretilir.")
    if st.button("🎯 Önerileri güncelle"):
        categories = pers.generate_recommendations(conn, user, profile_id)
        if categories:
            st.success(f"{len(categories)} kategori için yeni öneri oluşturuldu.")
        else:
            st.info("Şu an zayıf kategori tespit edilmedi (ya hiç test yok ya da performans iyi).")
    rows = pers.list_recommendations(conn, profile_id)
    if rows:
        st.dataframe(pd.DataFrame([dict(r) for r in rows])[["category", "material", "created_at"]],
                     use_container_width=True, hide_index=True)
    else:
        st.caption("Henüz öneri üretilmedi.")
