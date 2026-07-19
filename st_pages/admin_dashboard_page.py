import streamlit as st


def show_admin_dashboard() -> None:
    st.markdown(
        '<div style="margin-bottom:1rem">'
        '<div style="font-size:1.4rem;font-weight:700;color:#0F172A">📊 Admin Dashboard</div>'
        '<div style="color:#64748B;font-size:0.95rem;margin-top:0.2rem">'
        "Platform statistics and recent activity."
        "</div></div>",
        unsafe_allow_html=True,
    )

    try:
        from st_db import db_get_stats, db_list_analyses
        stats = db_get_stats()
    except Exception as exc:
        st.error(f"Could not load stats: {exc}")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total Users", stats["total_users"])
    with col2:
        st.metric("✅ Active Users", stats["active_users"])
    with col3:
        st.metric("🔬 Total Analyses", stats["total_analyses"])
    with col4:
        st.metric("🛡️ Admins", stats["admin_count"])

    st.markdown("---")
    st.markdown("#### 🔬 Recent Analyses")

    try:
        analyses = db_list_analyses(limit=10)
    except Exception:
        analyses = []

    if not analyses:
        st.info("No analyses recorded yet.")
        return

    import pandas as pd
    df = pd.DataFrame(analyses)[
        ["image_filename", "user_id", "status", "ml_enabled", "created_at"]
    ]
    df.columns = ["Image", "User ID", "Status", "ML", "Date"]
    df["User ID"] = df["User ID"].str[:8] + "…"
    df["Status"] = df["Status"].apply(
        lambda s: f"✅ {s}" if s == "completed" else f"⏳ {s}"
    )
    df["ML"] = df["ML"].apply(lambda v: "✅" if v else "—")
    st.dataframe(df, use_container_width=True, hide_index=True)
