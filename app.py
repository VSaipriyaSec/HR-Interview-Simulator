
import streamlit as st

from src.storage.db import init_db

from src.ui.components import apply_custom_css
from src.ui.auth_view import show_auth
from src.ui.dashboard_view import show_dashboard
from src.ui.setup_view import show_setup
from src.ui.interview_view import show_interview
from src.ui.evaluation_view import show_evaluation
from src.ui.analytics_view import show_analytics


# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="HR Interview Simulator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# 2. INITIALIZE APPLICATION
# --------------------------------------------------

init_db()


# --------------------------------------------------
# 3. AUTHENTICATION CHECK
# --------------------------------------------------

if not st.session_state.get("authenticated", False):
    show_auth()
    st.stop()


# --------------------------------------------------
# 4. INITIALIZE PAGE
# --------------------------------------------------

if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"


# --------------------------------------------------
# 5. APPLY STREAMLIT THEME-AWARE CSS
# --------------------------------------------------

apply_custom_css()


# --------------------------------------------------
# 6. SIDEBAR NAVIGATION
# --------------------------------------------------

with st.sidebar:

    st.title("🎯 HR Simulator")
    st.caption("AI-Powered Interview Practice")

    if "user" in st.session_state:
        st.caption(
            f"Welcome, {st.session_state['user']['name']}!"
        )

    st.divider()

    st.subheader("Navigation")

    navigation_items = [
        ("dashboard", "📊 Dashboard"),
        ("setup", "🚀 New Interview"),
        ("interview", "🎤 Live Interview"),
        ("evaluation", "📋 Evaluation"),
        ("analytics", "📈 History & Analytics"),
    ]

    for page_id, label in navigation_items:

        is_current_page = (
            st.session_state["page"] == page_id
        )

        if st.button(
            label,
            key=f"nav_{page_id}",
            use_container_width=True,
            type="primary" if is_current_page else "secondary",
        ):
            st.session_state["page"] = page_id
            st.rerun()

    st.divider()

    # LOGOUT
    if st.button(
        "🚪 Logout",
        key="logout_button",
        use_container_width=True,
    ):
        st.session_state.clear()
        st.rerun()

    st.divider()

    st.caption("HR Interview Simulator")
    st.caption("Developed by V Saipriya")


# --------------------------------------------------
# 7. PAGE ROUTING
# --------------------------------------------------

current_page = st.session_state["page"]

if current_page == "dashboard":
    show_dashboard()

elif current_page == "setup":
    show_setup()

elif current_page == "interview":
    show_interview()

elif current_page == "evaluation":
    show_evaluation()

elif current_page == "analytics":
    show_analytics()

else:
    st.session_state["page"] = "dashboard"
    st.rerun()
