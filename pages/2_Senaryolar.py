"""Senaryo oluşturma, yapay zekâ ile mesaj üretme, önizleme/düzenleme ve ikna analizi."""
import json

import pandas as pd
import streamlit as st

from components.common import apply_theme, get_db, require_login, show_flash
from services import profiles as ps
from services import scenarios as ss
from services.auth import PermissionDenied, has_permission

st.set_page_config(page_title="Senaryolar", page_icon="🎭", layout="wide")
apply_theme()
conn = get_db()
user = require_login()

st.title("🎭 Senaryo ve Mesaj Yönetimi")
show_flash()
can_edit = has_permission(user["role"], "edit")

STATUS_LABELS = {
    "draft": "📝 Taslak", "pending_approval": "⏳ Onay bekliyor",
    "approved": "✅ Onaylandı", "skipped": "⏭️ Atlandı",
    "queued": "📤 Kuyruğa alındı", "completed": "✔️ Tamamlandı",
}


def done(msg):
    st.session_state["flash"] = msg
    st.rerun()


tab_list, tab_new, tab_work = st.tabs(["📋 Senaryolar", "➕ Yeni senaryo", "✏️ Mesaj & Analiz"])

with tab_list:
    rows = ss.list_scenarios(conn)
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])[["id", "title", "status", "profile_id", "updated_at"]]
        df["status"] = df["status"].map(STATUS_LABELS)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Henüz senaryo yok. 'Yeni senaryo' sekmesinden ekleyin.")

with tab_new:
    if not can_edit:
        st.info("Senaryo oluşturmak için yetkiniz yok.")
    else:
        profile_rows = ps.list_profiles(conn)
        if not profile_rows:
            st.warning("Önce 'Profiller' sayfasından en az bir profil ekleyin.")
        else:
            options = {r["id"]: f"#{r['id']} – {r['label']} ({r['department'] or '-'})" for r in profile_rows}
            with st.form("new_scenario"):
                title = st.text_input("Senaryo başlığı *", placeholder="Örn: BT Acil Şifre Yenileme")
                profile_id = st.selectbox("Hedef profil *", list(options), format_func=lambda i: options[i])
                description = st.text_area("Açıklama (isteğe bağlı)")
                if st.form_submit_button("Senaryoyu oluştur"):
                    try:
                        sid = ss.create_scenario(conn, user, title, profile_id, description)
                        done(f"Senaryo #{sid} oluşturuldu. 'Mesaj & Analiz' sekmesinden devam edin.")
                    except (ss.ValidationError, PermissionDenied) as exc:
                        st.error(str(exc))

with tab_work:
    rows = ss.list_scenarios(conn)
    if not rows:
        st.info("Önce bir senaryo oluşturun.")
    else:
        options = {r["id"]: f"#{r['id']} – {r['title']} [{STATUS_LABELS.get(r['status'], r['status'])}]" for r in rows}
        sid = st.selectbox("Senaryo seç", list(options), format_func=lambda i: options[i])
        scenario = ss.get_scenario(conn, sid)
        profile = ps.get_profile(conn, scenario["profile_id"]) if scenario["profile_id"] else None

        if profile is not None:
            st.caption(f"Hedef profil: **{profile['label']}** – {profile['role_title'] or '-'} / {profile['department'] or '-'}")

        col_gen, col_status = st.columns([1, 2])
        with col_gen:
            if can_edit and st.button("🤖 Yapay zekâ ile mesaj üret", disabled=profile is None):
                try:
                    ss.generate_scenario_message(conn, user, sid)
                    done("Mesaj üretildi ve otomatik analiz edildi.")
                except ss.ValidationError as exc:
                    st.error(str(exc))
        with col_status:
            st.info(f"Durum: **{STATUS_LABELS.get(scenario['status'], scenario['status'])}**")

        st.subheader("✉️ Mesaj önizleme / düzenleme")
        if can_edit:
            with st.form(f"edit_msg_{sid}"):
                subject = st.text_input("Konu", value=scenario["message_subject"] or "")
                body = st.text_area("Gövde", value=scenario["message_body"] or "", height=220)
                c1, c2 = st.columns(2)
                save = c1.form_submit_button("💾 Mesajı kaydet")
                analyze = c2.form_submit_button("🔍 İkna analizini çalıştır")
                if save:
                    ss.update_message(conn, user, sid, subject, body)
                    done("Mesaj kaydedildi.")
                if analyze:
                    try:
                        ss.update_message(conn, user, sid, subject, body)
                        ss.run_analysis(conn, user, sid)
                        done("Analiz tamamlandı.")
                    except ss.ValidationError as exc:
                        st.error(str(exc))
        else:
            st.text_input("Konu", value=scenario["message_subject"] or "", disabled=True)
            st.text_area("Gövde", value=scenario["message_body"] or "", height=220, disabled=True)

        st.subheader("🧠 İkna analizi sonucu")
        analysis = ss.latest_analysis(conn, sid)
        if analysis is None:
            st.caption("Henüz analiz yapılmadı.")
        else:
            result = json.loads(analysis["result_json"])
            mode_label = {"rule_based": "kural tabanlı / demo", "llm": "LLM", "demo": "demo"}.get(result["mode"], result["mode"])
            st.caption(f"Analiz modu: **{mode_label}**" + (f" — {result.get('note')}" if result.get("note") else ""))
            st.write(f"Genel risk seviyesi: **{result.get('overall_risk', '-')}**")
            if not result.get("findings"):
                st.info("Belirgin bir ikna tekniği tespit edilmedi.")
            for f in result.get("findings", []):
                with st.expander(f"🔸 {f['technique'].replace('_', ' ').title()} (güven: {f['confidence']})"):
                    st.write(f"**Kanıt:** \"…{f['evidence']}…\"")
                    st.write(f"**Açıklama:** {f['explanation']}")
                    st.write(f"**Alternatif yorum / belirsizlik:** {f['alternative']}")
                    st.write(f"**Önerilen savunma:** {f['defense']}")
