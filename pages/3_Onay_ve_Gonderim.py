"""Tekli/toplu onay, atlama ve simülasyon / kontrollü gerçek gönderim kuyruğu."""
import pandas as pd
import streamlit as st

from components.common import apply_theme, get_db, require_login, show_flash
from services import scenarios as ss
from services.auth import PermissionDenied, has_permission
from services.mailer import ValidationError as MailError
from services.mailer import list_events, queue_scenario, real_send_ready
from services.settings_service import list_recipients

st.set_page_config(page_title="Onay ve Gönderim", page_icon="✅", layout="wide")
apply_theme()
conn = get_db()
user = require_login()

st.title("✅ Onay ve Gönderim Yönetimi")
show_flash()
can_approve = has_permission(user["role"], "approve")
can_queue = has_permission(user["role"], "queue")


def done(msg):
    st.session_state["flash"] = msg
    st.rerun()


readiness = real_send_ready(conn)
if readiness["ready"]:
    st.warning("🟠 Gerçek gönderim şu an açık (yalnızca yetkili alıcı listesindeki adreslere, kapsamı doğrulanmış onaylarla).")
else:
    st.success("🟢 Gerçek gönderim kapalı — her şey simülasyon kuyruğunda kalır. Neden: " + "; ".join(readiness["reasons"]))

tab_approve, tab_queue, tab_log = st.tabs(["🖊️ Onay / Atlama", "📤 Kuyruğa Al / Gönder", "📜 Olay Günlüğü"])

# ---------- Onay / Atlama ----------
with tab_approve:
    pending = ss.list_scenarios(conn, "pending_approval")
    if not can_approve:
        st.info("Onaylama/atlama için yetkiniz yok.")
    elif not pending:
        st.info("Onay bekleyen senaryo yok. Önce 'Senaryolar' sayfasında analiz çalıştırın.")
    else:
        df = pd.DataFrame([{"id": r["id"], "başlık": r["title"]} for r in pending])
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("**Tekli işlem**")
        options = {r["id"]: f"#{r['id']} – {r['title']}" for r in pending}
        sid = st.selectbox("Senaryo", list(options), format_func=lambda i: options[i])
        scope_verified = st.checkbox(
            "İzinli test kapsamını doğruladım (bu senaryonun yetkilendirilmiş bir eğitim/test faaliyeti olduğunu onaylıyorum)",
            key="scope_single",
        )
        c1, c2 = st.columns(2)
        if c1.button("✅ Onayla", disabled=not scope_verified):
            try:
                ss.decide(conn, user, sid, "approved", scope_verified=True)
                done(f"Senaryo #{sid} onaylandı.")
            except (ss.ValidationError, PermissionDenied) as exc:
                st.error(str(exc))
        if c2.button("⏭️ Atla"):
            try:
                ss.decide(conn, user, sid, "skipped")
                done(f"Senaryo #{sid} atlandı.")
            except (ss.ValidationError, PermissionDenied) as exc:
                st.error(str(exc))

        st.divider()
        st.markdown("**Toplu işlem**")
        chosen = st.multiselect("Birden fazla senaryo seç", list(options), format_func=lambda i: options[i])
        bulk_scope = st.checkbox("Seçilenler için izinli test kapsamını doğruladım", key="scope_bulk")
        bc1, bc2 = st.columns(2)
        if bc1.button("✅ Seçilenleri toplu onayla", disabled=not (chosen and bulk_scope)):
            result = ss.bulk_decide(conn, user, chosen, "approved", scope_verified=True)
            done(f"{len(result['ok'])} senaryo onaylandı, {len(result['failed'])} başarısız.")
        if bc2.button("⏭️ Seçilenleri toplu atla", disabled=not chosen):
            result = ss.bulk_decide(conn, user, chosen, "skipped")
            done(f"{len(result['ok'])} senaryo atlandı, {len(result['failed'])} başarısız.")

# ---------- Kuyruğa Al / Gönder ----------
with tab_queue:
    approved = ss.list_scenarios(conn, "approved")
    if not can_queue:
        st.info("Kuyruğa almak için yetkiniz yok.")
    elif not approved:
        st.info("Onaylanmış, kuyruğa alınmayı bekleyen senaryo yok.")
    else:
        recipients = list_recipients(conn)
        options = {r["id"]: f"#{r['id']} – {r['title']}" for r in approved}
        sid = st.selectbox("Senaryo", list(options), format_func=lambda i: options[i], key="queue_sid")

        st.markdown("**Simülasyon (varsayılan, risksiz)**")
        if st.button("📥 Simülasyon kuyruğuna al"):
            try:
                result = queue_scenario(conn, user, sid, real_recipient_email=None)
                done(result["detail"])
            except MailError as exc:
                st.error(str(exc))

        st.divider()
        st.markdown("**Kontrollü gerçek gönderim**")
        if not recipients:
            st.caption("Yetkili alıcı yok. Önce 'Ayarlar' sayfasından ekleyin.")
        else:
            recipient_options = {r["email"]: f"{r['email']} ({r['label'] or 'etiketsiz'})" for r in recipients}
            target = st.selectbox("Yetkili alıcı", list(recipient_options),
                                  format_func=lambda e: recipient_options[e], key="queue_recipient")
            if st.button("📨 Bu adrese GERÇEK test maili gönder", disabled=not readiness["ready"]):
                try:
                    result = queue_scenario(conn, user, sid, real_recipient_email=target)
                    done(result["detail"])
                except MailError as exc:
                    st.error(str(exc))
            if not readiness["ready"]:
                st.caption("Gerçek gönderim şu an kapalı: " + "; ".join(readiness["reasons"]))

# ---------- Olay Günlüğü ----------
with tab_log:
    events = list_events(conn)
    if events:
        df = pd.DataFrame([dict(e) for e in events])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Henüz bir simülasyon/gönderim olayı yok.")
