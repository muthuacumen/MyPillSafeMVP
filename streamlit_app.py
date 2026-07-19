import streamlit as st

# ── Page config — must be the very first Streamlit call ──────────────────────
st.set_page_config(
    page_title="PillSafe",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Pages ─────────────────────────────────────────────────────────────────────
from st_pages.auth_page import show_login, show_register
from st_pages.dashboard_page import show_dashboard
from st_pages.analyze_page import show_analyze
from st_pages.admin_dashboard_page import show_admin_dashboard
from st_pages.admin_users_page import show_admin_users


# ── Global CSS ────────────────────────────────────────────────────────────────
def _inject_css() -> None:
    st.markdown(
        """
<style>
/* Hide default Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Primary button — teal gradient */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #09706C 0%, #0EA5A0 100%);
    color: white !important;
    border: none;
    border-radius: 10px;
    padding: 0.55rem 1.25rem;
    font-weight: 600;
    font-size: 0.9rem;
    width: 100%;
    transition: opacity 0.2s;
}
div.stButton > button[kind="primary"]:hover { opacity: 0.88; }

/* Secondary / default button */
div.stButton > button[kind="secondary"],
div.stButton > button:not([kind="primary"]) {
    border: 1.5px solid #CBD5E1;
    border-radius: 10px;
    background: white;
    font-size: 0.875rem;
    width: 100%;
    transition: border-color 0.2s;
}
div.stButton > button:not([kind="primary"]):hover {
    border-color: #0D9488;
    color: #0D9488;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
[data-testid="stMetricValue"] { color: #0F172A !important; font-weight: 700; }
[data-testid="stMetricLabel"] { color: #64748B !important; font-size: 0.8rem; }

/* File uploader */
[data-testid="stFileUploader"] {
    border: 2px dashed #CBD5E1;
    border-radius: 12px;
    background: #F8FAFC;
    padding: 0.5rem;
}
[data-testid="stFileUploader"]:hover { border-color: #0D9488; }

/* Inputs */
input[type="text"], input[type="password"], input[type="email"] {
    border-radius: 8px !important;
    border-color: #CBD5E1 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: white;
    border-right: 1px solid #E2E8F0;
}

/* Sidebar nav buttons — override default style */
[data-testid="stSidebar"] div.stButton > button {
    text-align: left !important;
    justify-content: flex-start;
    border: none !important;
    background: transparent !important;
    color: #334155 !important;
    font-size: 0.9rem;
    border-radius: 8px !important;
    padding: 0.45rem 0.75rem !important;
}
[data-testid="stSidebar"] div.stButton > button:hover {
    background: #F1F5F9 !important;
    color: #0D9488 !important;
    border: none !important;
}

/* Dataframe headers */
[data-testid="stDataFrame"] th {
    background: #F8FAFC !important;
    color: #475569 !important;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
</style>
        """,
        unsafe_allow_html=True,
    )


# ── Session defaults ──────────────────────────────────────────────────────────
def _init_session() -> None:
    defaults = {
        "user": None,
        "page": "login",
        "analysis_result": None,
        "_confirm_del": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _nav(page: str) -> None:
    st.session_state.page = page
    st.rerun()


# ── Authenticated sidebar ─────────────────────────────────────────────────────
def _show_sidebar() -> None:
    user = st.session_state.user
    with st.sidebar:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:10px;'
            'padding:1rem 0 1.25rem;border-bottom:1px solid #E2E8F0;margin-bottom:1rem">'
            '<span style="font-size:1.8rem">💊</span>'
            '<span style="color:#0D9488;font-size:1.3rem;font-weight:800">PillSafe</span>'
            "</div>",
            unsafe_allow_html=True,
        )

        role_badge = (
            '<span style="background:#FEF3C7;color:#92400E;border-radius:4px;'
            'padding:1px 6px;font-size:0.7rem;font-weight:600">ADMIN</span>'
            if user["role"] == "ADMIN"
            else ""
        )
        st.markdown(
            f'<div style="padding:0.25rem 0 1rem">'
            f'<div style="font-weight:700;color:#0F172A">'
            f'{user["first_name"]} {user["last_name"]} {role_badge}</div>'
            f'<div style="color:#64748B;font-size:0.8rem">{user["email"]}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        if st.button("🏠  Dashboard", use_container_width=True):
            _nav("dashboard")
        if st.button("🔬  Analyse Medication", use_container_width=True):
            _nav("analyze")

        if user["role"] == "ADMIN":
            st.markdown(
                '<div style="font-size:0.7rem;font-weight:700;color:#94A3B8;'
                'letter-spacing:0.08em;text-transform:uppercase;padding:0.75rem 0 0.25rem">'
                "Administration</div>",
                unsafe_allow_html=True,
            )
            if st.button("📊  Platform Stats", use_container_width=True):
                _nav("admin_dashboard")
            if st.button("👥  Manage Users", use_container_width=True):
                _nav("admin_users")

        st.markdown("---")
        if st.button("🚪  Sign Out", use_container_width=True):
            for k in ["user", "analysis_result", "_confirm_del"]:
                st.session_state[k] = None
            _nav("login")


# ── Router ────────────────────────────────────────────────────────────────────
def main() -> None:
    _inject_css()
    _init_session()

    user = st.session_state.user
    page = st.session_state.page

    if user is None:
        if page == "register":
            show_register()
        else:
            show_login()
        return

    _show_sidebar()

    if page in ("dashboard", "login", "register"):
        show_dashboard()
    elif page == "analyze":
        show_analyze()
    elif page == "admin_dashboard":
        show_admin_dashboard() if user["role"] == "ADMIN" else show_dashboard()
    elif page == "admin_users":
        show_admin_users() if user["role"] == "ADMIN" else show_dashboard()
    else:
        show_dashboard()


main()
