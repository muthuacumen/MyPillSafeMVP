import re
from datetime import date, timedelta
import streamlit as st


def _nav(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def _pwd_errors(pwd: str) -> list[str]:
    errs = []
    if len(pwd) < 8:
        errs.append("At least 8 characters")
    if not re.search(r"[A-Z]", pwd):
        errs.append("At least one uppercase letter")
    if not re.search(r"\d", pwd):
        errs.append("At least one number")
    return errs


def show_login() -> None:
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown(
            '<div style="text-align:center;padding:2rem 0 1.5rem">'
            '<span style="font-size:3.5rem">💊</span>'
            '<h1 style="color:#0D9488;font-size:2.2rem;font-weight:800;margin:0.4rem 0 0">PillSafe</h1>'
            '<p style="color:#64748B;margin:0.3rem 0 2rem;font-size:1rem">Medication safety, simplified.</p>'
            "</div>",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("#### Sign In")
            email = st.text_input(
                "Email address", placeholder="you@example.com", key="li_email"
            )
            password = st.text_input(
                "Password", type="password", placeholder="••••••••", key="li_pwd"
            )

            st.markdown("")
            if st.button("Sign In", type="primary", use_container_width=True):
                if not email or not password:
                    st.error("Please fill in all fields.")
                else:
                    try:
                        from st_db import db_login
                        user = db_login(email.strip().lower(), password)
                        st.session_state.user = user
                        _nav("dashboard")
                    except Exception as exc:
                        st.error(getattr(exc, "message", str(exc)))

            st.markdown(
                '<p style="text-align:center;margin-top:1rem;color:#64748B;font-size:0.9rem">'
                "Don't have an account?</p>",
                unsafe_allow_html=True,
            )
            if st.button("Create Account →", use_container_width=True):
                _nav("register")


def show_register() -> None:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown(
            '<div style="text-align:center;padding:2rem 0 1.5rem">'
            '<span style="font-size:3.5rem">💊</span>'
            '<h1 style="color:#0D9488;font-size:2.2rem;font-weight:800;margin:0.4rem 0 0">PillSafe</h1>'
            '<p style="color:#64748B;margin:0.3rem 0 2rem">Create your medication safety account.</p>'
            "</div>",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("#### Create Account")

            c1, c2 = st.columns(2)
            with c1:
                first_name = st.text_input("First Name", placeholder="Jane", key="rg_fn")
            with c2:
                last_name = st.text_input("Last Name", placeholder="Doe", key="rg_ln")

            email = st.text_input(
                "Email address", placeholder="you@example.com", key="rg_email"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Min 8 chars · 1 uppercase · 1 number",
                key="rg_pwd",
            )
            max_dob = date.today() - timedelta(days=18 * 365)
            dob = st.date_input(
                "Date of Birth (must be 18+)",
                value=date(1995, 1, 1),
                min_value=date(1920, 1, 1),
                max_value=max_dob,
                key="rg_dob",
            )

            st.markdown("")
            if st.button("Create Account", type="primary", use_container_width=True):
                errors: list[str] = []
                if not first_name or not last_name:
                    errors.append("First and last name are required.")
                if not email:
                    errors.append("Email is required.")
                if password:
                    errors.extend(_pwd_errors(password))
                else:
                    errors.append("Password is required.")

                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    try:
                        from st_db import db_register
                        db_register(
                            email=email.strip().lower(),
                            password=password,
                            first_name=first_name.strip(),
                            last_name=last_name.strip(),
                            dob=dob,
                        )
                        st.success("Account created! Please sign in.")
                        _nav("login")
                    except Exception as exc:
                        st.error(getattr(exc, "message", str(exc)))

            st.markdown(
                '<p style="text-align:center;margin-top:1rem;color:#64748B;font-size:0.9rem">'
                "Already have an account?</p>",
                unsafe_allow_html=True,
            )
            if st.button("← Sign In", use_container_width=True):
                _nav("login")
