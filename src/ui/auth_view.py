
import streamlit as st

from src.services.auth_service import register_user, login_user


def show_auth():
    """Display login and account creation screens."""

    st.markdown(
        "<h1 style='text-align:center;'>🎯 HR Interview Simulator</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;'>AI-Powered Interview Practice</p>",
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 1.5, 1])

    with center:
        tab_login, tab_register = st.tabs(["Login", "Create Account"])

        with tab_login:
            st.subheader("Welcome Back")

            with st.form("login_form"):
                email = st.text_input("Email Address")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button(
                    "Login", use_container_width=True
                )

            if submitted:
                user = login_user(email, password)

                if user:
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = user
                    st.session_state["page"] = "dashboard"
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

        with tab_register:
            st.subheader("Create Your Account")

            with st.form("register_form"):
                name = st.text_input("Full Name")
                email = st.text_input("Email Address")
                password = st.text_input(
                    "Password", type="password"
                )
                confirm_password = st.text_input(
                    "Confirm Password", type="password"
                )

                submitted = st.form_submit_button(
                    "Create Account", use_container_width=True
                )

            if submitted:
                if password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    success, message = register_user(
                        name, email, password
                    )

                    if success:
                        st.success(message)
                        st.info("Please switch to Login to continue.")
                    else:
                        st.error(message)
