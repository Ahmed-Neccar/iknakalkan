"""Gönderen adı, yetkili test alıcıları ve gerçek gönderim anahtarı. SMTP parolası burada YOKTUR,
yalnızca .env dosyasında tutulur."""
import pandas as pd
import streamlit as st

import config
from components.common import apply_theme, get_db, require_login, show_flash
from services.auth import PermissionDenied, has_permission
from services.mailer import real_send_ready
from services.settings_service import (ValidationError, add_recipient, from_display_name,
                                        get_setting, list_recipients, real_send_db_enabled,
                                        remove_recipient, set_setting)

st.set_page_config(page_title="Ayarlar", page_icon="⚙️", layout="wide")
apply_theme()
conn = get_db()
user = require_login()

st.title("⚙️ Ayarlar")
show_flash()
is_admin = has_permission(user["role"], "manage_users")
if not is_admin:
    st.warning("Bu sayfadaki ayarları yalnızca admin rolü değiştirebilir.")


def done(msg):
    st.session_state["flash"] = msg
    st.rerun()


tab_general, tab_recipients, tab_status = st.tabs(["🏷️ Genel", "👥 Yetkili Test Alıcıları", "🔎 Gönderim Durumu"])

with tab_general:
    name = st.text_input("Gönderen görünen adı", value=from_display_name(conn), disabled=not is_admin)
    real_on = st.checkbox(
        "Gerçek gönderimi bu ortamda etkinleştir (ek olarak .env'de ALLOW_REAL_SEND=true olmalı)",
        value=real_send_db_enabled(conn), disabled=not is_admin,
    )
    if is_admin and st.button("Kaydet"):
        set_setting(conn, user, "from_display_name", name)
        set_setting(conn, user, "real_send_db_enabled", "true" if real_on else "false")
        done("Ayarlar kaydedildi.")

with tab_recipients:
    st.caption("Gerçek gönderim yalnızca burada listelenen, kendi rızasıyla teste katılan adreslere yapılabilir.")
    rows = list_recipients(conn)
    if rows:
        st.dataframe(pd.DataFrame([dict(r) for r in rows])[["id", "email", "label", "created_at"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info("Henüz yetkili alıcı eklenmedi.")
    if is_admin:
        with st.form("add_recipient", clear_on_submit=True):
            email = st.text_input("E-posta")
            label = st.text_input("Etiket (isteğe bağlı)", placeholder="Örn: Hoca, kendi test adresim")
            if st.form_submit_button("Ekle"):
                try:
                    add_recipient(conn, user, email, label)
                    done("Yetkili alıcı eklendi.")
                except (ValidationError, PermissionDenied) as exc:
                    st.error(str(exc))
        if rows:
            del_id = st.selectbox("Kaldırılacak kayıt", [r["id"] for r in rows],
                                  format_func=lambda i: next(r["email"] for r in rows if r["id"] == i))
            if st.button("🗑️ Listeden kaldır"):
                try:
                    remove_recipient(conn, user, del_id)
                    done("Alıcı listeden kaldırıldı.")
                except (ValidationError, PermissionDenied) as exc:
                    st.error(str(exc))

with tab_status:
    readiness = real_send_ready(conn)
    if readiness["ready"]:
        st.warning("🟠 Gerçek gönderim şu an mümkün.")
    else:
        st.success("🟢 Gerçek gönderim şu an KAPALI.")
        for reason in readiness["reasons"]:
            st.write(f"- {reason}")
    st.caption(f"SMTP host yapılandırılmış mı: {'evet' if config.smtp_configured() else 'hayır'} "
               f"(parola bu ekranda asla gösterilmez, yalnızca .env dosyasında tutulur).")
