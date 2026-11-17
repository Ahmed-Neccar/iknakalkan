"""Profil yönetimi sayfası: listele, ekle, düzenle, sil, CSV içe aktar."""
from pathlib import Path

import pandas as pd
import streamlit as st

import config
from components.common import apply_theme, get_db, require_login, show_flash
from services import profiles as ps
from services.auth import PermissionDenied, has_permission

st.set_page_config(page_title="Profiller", page_icon="👥", layout="wide")
apply_theme()
conn = get_db()
user = require_login()

st.title("👥 Hedef Profil Yönetimi")
st.caption("Yalnızca sentetik veya izinli test verisi girin. Gerçek kişilerin özel bilgilerini eklemeyin.")
show_flash()

can_edit = has_permission(user["role"], "edit")
can_delete = has_permission(user["role"], "delete")
if not can_edit:
    st.info("Rolünüz (viewer) yalnızca görüntülemeye izin veriyor.")


def done(message):
    st.session_state["flash"] = message
    st.rerun()


tab_list, tab_add, tab_edit, tab_import = st.tabs(["📋 Liste", "➕ Ekle", "✏️ Düzenle / Sil", "📥 CSV içe aktar"])

# ---------- Liste ----------
with tab_list:
    search = st.text_input("Ara (etiket, görev veya departman)")
    rows = ps.list_profiles(conn, search)
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(rows)} profil")
    else:
        st.info("Henüz profil yok. 'Ekle' veya 'CSV içe aktar' sekmesini kullanın.")

# ---------- Ekle ----------
with tab_add:
    if can_edit:
        st.caption("İzinli e-posta alanları: " + ", ".join(sorted(config.allowed_email_domains())))
        with st.form("add_profile", clear_on_submit=True):
            label = st.text_input("Ad etiketi *", placeholder="Ayşe (sentetik)")
            role_title = st.text_input("Görev")
            department = st.text_input("Departman")
            contact = st.text_input("İzinli iletişim (e-posta)", placeholder="ayse.test@example.com")
            if st.form_submit_button("Profili kaydet"):
                try:
                    ps.create_profile(conn, user, label, role_title, department, contact)
                    done("Profil eklendi.")
                except (ps.ValidationError, PermissionDenied) as exc:
                    st.error(str(exc))
    else:
        st.info("Profil eklemek için yetkiniz yok.")

# ---------- Düzenle / Sil ----------
with tab_edit:
    all_rows = ps.list_profiles(conn)
    if not can_edit:
        st.info("Düzenlemek için yetkiniz yok.")
    elif not all_rows:
        st.info("Düzenlenecek profil yok.")
    else:
        options = {r["id"]: f"#{r['id']} – {r['label']}" for r in all_rows}
        pid = st.selectbox("Profil seç", list(options), format_func=lambda i: options[i])
        p = ps.get_profile(conn, pid)
        with st.form(f"edit_profile_{pid}"):
            label = st.text_input("Ad etiketi *", value=p["label"])
            role_title = st.text_input("Görev", value=p["role_title"] or "")
            department = st.text_input("Departman", value=p["department"] or "")
            contact = st.text_input("İzinli iletişim (e-posta)", value=p["allowed_contact"] or "")
            if st.form_submit_button("Güncelle"):
                try:
                    ps.update_profile(conn, user, pid, label, role_title, department, contact)
                    done("Profil güncellendi.")
                except (ps.ValidationError, PermissionDenied) as exc:
                    st.error(str(exc))
        st.divider()
        if can_delete:
            confirm = st.checkbox("Bu profili kalıcı olarak silmek istediğimi onaylıyorum", key=f"del_ok_{pid}")
            if st.button("🗑️ Profili sil", disabled=not confirm):
                try:
                    ps.delete_profile(conn, user, pid)
                    done("Profil silindi.")
                except (ps.ValidationError, PermissionDenied) as exc:
                    st.error(str(exc))
        else:
            st.caption("Silme yalnızca admin rolüne açıktır.")

# ---------- CSV içe aktar ----------
with tab_import:
    if not can_edit:
        st.info("İçe aktarmak için yetkiniz yok.")
    else:
        st.write("Sütunlar: `label` (zorunlu), `role_title`, `department`, `allowed_contact`. "
                 "Türkçe başlıklar da olur: `ad_etiketi`, `gorev`, `departman`, `iletisim`.")
        sample = Path(config.BASE_DIR / "data" / "ornek_profiller.csv")
        if sample.exists():
            st.download_button("Örnek CSV'yi indir", sample.read_bytes(), "ornek_profiller.csv", "text/csv")
        uploaded = st.file_uploader("CSV dosyası", type=["csv"])
        source_name = st.text_input("Kaynak adı", value=uploaded.name if uploaded else "")
        origin = st.text_input("Veri kökeni", placeholder="Örn: Sınıf projesi için elle üretilmiş sentetik veri")
        confirm = st.checkbox("Bu verilerin sentetik veya izinli test verisi olduğunu onaylıyorum")
        if st.button("İçe aktar", disabled=uploaded is None):
            try:
                result = ps.import_profiles_csv(conn, user, uploaded.getvalue(), source_name, origin, confirm)
                st.success(f"{result['imported']} profil eklendi, {len(result['rejected'])} satır reddedildi.")
                if result["rejected"]:
                    st.dataframe(pd.DataFrame(result["rejected"], columns=["Satır", "Neden"]), hide_index=True)
            except (ps.ValidationError, PermissionDenied) as exc:
                st.error(str(exc))
