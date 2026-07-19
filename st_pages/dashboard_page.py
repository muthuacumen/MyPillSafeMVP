from datetime import datetime
import streamlit as st


def _nav(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def show_dashboard() -> None:
    user = st.session_state.user
    name = user.get("first_name", "there")

    # Hero banner
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#09706C 0%,#0B8A86 50%,#0EA5A0 100%);'
        f'border-radius:16px;padding:1.75rem 2rem;margin-bottom:1.5rem;color:white">'
        f'<div style="font-size:1.4rem;font-weight:800">Welcome back, {name}! 👋</div>'
        f'<div style="opacity:0.85;font-size:0.95rem;margin-top:0.25rem">'
        f"Your medication safety dashboard — everything at a glance."
        f"</div></div>",
        unsafe_allow_html=True,
    )

    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💊 Meds Analysed", user.get("medications_analyzed", 0))
    with col2:
        st.metric("✅ Safety Score", "98%")
    with col3:
        st.metric("📅 Days Active", "7")
    with col4:
        st.metric("⚠️ Alerts", "0")

    st.markdown("---")
    left, right = st.columns([1.3, 1])

    with left:
        st.markdown("#### 🚀 Quick Actions")
        if st.button(
            "🔬  Analyse a Medication",
            type="primary",
            use_container_width=True,
        ):
            _nav("analyze")
        st.markdown("")

        st.markdown("#### 💡 Safety Tips")
        tips = [
            ("🕐", "Take medications at the same time each day for consistency."),
            ("📋", "Keep an up-to-date list of all your prescriptions."),
            ("💊", "Never share prescription medications with others."),
            ("🚫", "Don't crush or split pills unless directed by your doctor."),
        ]
        for icon, tip in tips:
            st.markdown(
                f'<div style="display:flex;gap:0.75rem;align-items:flex-start;'
                f'padding:0.65rem 0.85rem;border-radius:10px;background:#F0FDFA;'
                f'border:1px solid #99F6E4;margin-bottom:0.5rem">'
                f'<span style="font-size:1.2rem;line-height:1.4">{icon}</span>'
                f'<span style="color:#0F766E;font-size:0.875rem;line-height:1.5">{tip}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

    with right:
        # Weekly schedule
        st.markdown("#### 📅 Weekly Schedule")
        today_idx = datetime.today().weekday()
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        dcols = st.columns(7)
        for i, (dc, day) in enumerate(zip(dcols, days)):
            with dc:
                if i == today_idx:
                    st.markdown(
                        f'<div style="background:#0D9488;color:white;border-radius:8px;'
                        f'padding:5px 2px;text-align:center;font-size:0.72rem;font-weight:700">'
                        f"{day}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div style="background:#F1F5F9;color:#94A3B8;border-radius:8px;'
                        f'padding:5px 2px;text-align:center;font-size:0.72rem">{day}</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown("")
        st.markdown("#### 📈 Recent Activity")
        st.info("No recent scans yet. Use **Analyse a Medication** to get started!")

        if user["role"] == "ADMIN":
            st.markdown("---")
            st.markdown("#### 🛡️ Admin")
            if st.button("📊 Platform Stats", use_container_width=True):
                _nav("admin_dashboard")
            if st.button("👥 Manage Users", use_container_width=True):
                _nav("admin_users")
