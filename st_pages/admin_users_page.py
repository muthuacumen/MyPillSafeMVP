import streamlit as st
import pandas as pd


def show_admin_users() -> None:
    me = st.session_state.user

    st.markdown(
        '<div style="margin-bottom:1rem">'
        '<div style="font-size:1.4rem;font-weight:700;color:#0F172A">👥 Manage Users</div>'
        '<div style="color:#64748B;font-size:0.95rem;margin-top:0.2rem">'
        "View and manage all registered accounts."
        "</div></div>",
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refresh list"):
        st.rerun()

    try:
        from st_db import (
            db_list_users,
            db_activate_user,
            db_deactivate_user,
            db_change_role,
            db_delete_user,
        )
        users = db_list_users()
    except Exception as exc:
        st.error(f"Could not load users: {exc}")
        return

    if not users:
        st.info("No users registered yet.")
        return

    # Summary table
    df = pd.DataFrame(users)[
        ["email", "first_name", "last_name", "role", "is_active", "created_at"]
    ].copy()
    df.columns = ["Email", "First Name", "Last Name", "Role", "Active", "Joined"]
    df["Active"] = df["Active"].apply(lambda v: "✅ Active" if v else "⛔ Inactive")
    df["Role"] = df["Role"].apply(
        lambda r: f"🛡️ {r}" if r == "ADMIN" else f"👤 {r}"
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### ⚙️ User Actions")

    others = [u for u in users if u["id"] != me["id"]]
    if not others:
        st.info("No other users to manage (only you are registered).")
        return

    options = {f"{u['email']}  [{u['role']}]": u for u in others}
    selected_label = st.selectbox("Select a user to manage", list(options.keys()))
    sel = options[selected_label]

    # User detail card
    status_color = "#0D9488" if sel["is_active"] else "#EF4444"
    st.markdown(
        f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;'
        f'padding:0.85rem 1rem;margin-bottom:1rem;display:flex;gap:1.5rem;flex-wrap:wrap">'
        f'<span><strong>Email:</strong> {sel["email"]}</span>'
        f'<span><strong>Name:</strong> {sel["first_name"]} {sel["last_name"]}</span>'
        f'<span><strong>Role:</strong> {sel["role"]}</span>'
        f'<span style="color:{status_color}"><strong>Status:</strong> '
        f'{"Active" if sel["is_active"] else "Inactive"}</span>'
        f'<span><strong>Joined:</strong> {sel["created_at"]}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, _ = st.columns([1, 1, 1, 1])
    new_role = "PATIENT" if sel["role"] == "ADMIN" else "ADMIN"

    with c1:
        if sel["is_active"]:
            if st.button("⛔ Deactivate", use_container_width=True):
                db_deactivate_user(sel["id"])
                st.success(f"Deactivated {sel['email']}")
                st.rerun()
        else:
            if st.button("✅ Activate", use_container_width=True):
                db_activate_user(sel["id"])
                st.success(f"Activated {sel['email']}")
                st.rerun()

    with c2:
        if st.button(f"🔄 Make {new_role}", use_container_width=True):
            db_change_role(sel["id"], new_role)
            st.success(f"Role changed to {new_role}")
            st.rerun()

    with c3:
        if st.button("🗑️ Delete", use_container_width=True):
            st.session_state["_confirm_del"] = sel["id"]

    # Delete confirmation
    if st.session_state.get("_confirm_del") == sel["id"]:
        st.warning(
            f"⚠️ Delete **{sel['email']}**? This removes the account and all its data."
        )
        y, n = st.columns(2)
        with y:
            if st.button("Yes, delete permanently", type="primary"):
                db_delete_user(sel["id"])
                st.session_state["_confirm_del"] = None
                st.success("User deleted.")
                st.rerun()
        with n:
            if st.button("Cancel"):
                st.session_state["_confirm_del"] = None
                st.rerun()
