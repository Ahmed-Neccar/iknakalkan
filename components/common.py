"""Tüm sayfalarda ortak kullanılan yardımcılar."""
import streamlit as st

from database import init_db


@st.cache_resource
def get_db():
    return init_db()


def require_login():
    """Giriş yapılmamışsa sayfayı durdurur. Giriş varsa kullanıcıyı (dict) döndürür."""
    if "user" not in st.session_state:
        st.warning("Bu sayfayı görmek için önce ana sayfadan giriş yapın.")
        st.stop()
    return st.session_state["user"]


def show_flash():
    """İşlem sonrası mesajı (yeniden çizimden sonra) bir kez gösterir."""
    msg = st.session_state.pop("flash", None)
    if msg:
        st.success(msg)


# Shared visual system: restrained dark navy, accessible contrast, responsive cards.
def apply_theme():
    """Tutarlı, yüksek kontrastlı ve responsive İKNAKALKAN tasarım sistemi."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root {
      --ink:#edf3ff; --muted:#a6b5cc; --panel:#111c2d; --panel2:#15243a;
      --line:#2a3b53; --accent:#65e6c4; --blue:#8eb8ff; --danger:#ff8d9a;
    }
    .stApp { background:radial-gradient(ellipse at 8% 0%,#1a3550 0%,#0b1422 43%,#080e18 100%); color:var(--ink); }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
    h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.035em; color:#f3f7ff; }
    h1 { font-size:2.35rem !important; }
    h2 { font-size:1.55rem !important; }
    p, label, .stMarkdown { color:var(--ink); }
    [data-testid="stSidebar"] { background:linear-gradient(180deg,#0c1727,#09111d); border-right:1px solid var(--line); }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#c4d1e5; }
    [data-testid="stMetric"] { background:linear-gradient(145deg,rgba(24,42,64,.96),rgba(14,26,42,.96)); border:1px solid var(--line); padding:17px 19px; border-radius:16px; box-shadow:0 8px 24px #00000012; }
    [data-testid="stMetricLabel"] { color:var(--muted); }
    [data-testid="stMetricValue"] { font-family:'Space Grotesk',sans-serif; color:#f4f8ff; }
    div[data-testid="stForm"], div[data-testid="stExpander"], div[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line) !important; border-radius:15px !important; }
    .stButton>button, .stDownloadButton>button { border-radius:11px; border:1px solid #38516e; font-weight:700; min-height:2.6rem; transition:all .16s ease; }
    .stButton>button[kind="primary"], .stFormSubmitButton>button { background:linear-gradient(120deg,#65e6c4,#8bdccf); color:#07151a; border:0; }
    .stButton>button:hover, .stDownloadButton>button:hover { border-color:var(--accent); transform:translateY(-1px); }
    [data-testid="stDataFrame"], [data-testid="stTable"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
    [data-testid="stAlert"] { border-radius:12px; border:1px solid #ffffff12; }
    input, textarea { border-radius:10px !important; }
    .ikna-hero { position:relative; overflow:hidden; padding:1.65rem 1.8rem 1.7rem; border:1px solid #34516a; border-radius:22px; background:linear-gradient(115deg,rgba(24,54,75,.92),rgba(15,28,46,.92) 65%,rgba(20,53,57,.7)); box-shadow:0 18px 48px #00000020; margin:.25rem 0 1.25rem; }
    .ikna-hero:after { content:' '; position:absolute; width:240px; height:240px; right:-65px; top:-95px; border:1px solid #65e6c433; border-radius:50%; box-shadow:0 0 0 28px #65e6c40a,0 0 0 58px #65e6c406; }
    .ikna-eyebrow { color:var(--accent); font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.18em; margin-bottom:.45rem; }
    .ikna-title { font-family:'Space Grotesk',sans-serif; color:#f5f8ff; font-size:2.45rem; line-height:1.12; font-weight:700; letter-spacing:-.055em; margin:.2rem 0 .65rem; }
    .ikna-sub { color:#b7c8dc; font-size:1rem; max-width:850px; line-height:1.65; }
    .ikna-chip { display:inline-block; border:1px solid #45647b; border-radius:999px; color:#d8e7f8; padding:.32rem .65rem; font-size:.76rem; margin:.85rem .35rem 0 0; background:#0d1c2c88; }
    .ikna-section-label { color:#91a8c4; text-transform:uppercase; letter-spacing:.12em; font-size:.72rem; font-weight:700; margin-bottom:.45rem; }
    .ikna-card { height:100%; border:1px solid var(--line); border-radius:16px; padding:1rem 1.05rem; background:linear-gradient(145deg,#142238,#101a2a); }
    .ikna-card-title { color:#f1f6ff; font-weight:700; font-size:1rem; margin-bottom:.4rem; }
    .ikna-card-text { color:#a9bbd2; font-size:.88rem; line-height:1.55; }
    .ikna-status-dot { display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--accent); margin-right:.4rem; }
    hr { border-color:var(--line) !important; }
    @media (max-width: 760px) {
      .ikna-hero { padding:1.2rem; border-radius:16px; }
      .ikna-title { font-size:2rem; }
      h1 { font-size:1.9rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)
