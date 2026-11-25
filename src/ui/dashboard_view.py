
import streamlit as st

from src.storage.db import (
    init_db,
    get_all_sessions,
    get_session_score_summary,
)

from src.ui.components import (
    render_section_header,
    render_metric_card,
    render_empty_state,
)


def show_dashboard():
    """Display the logged-in user's interview dashboard."""

    init_db()

    # Get the logged-in user's ID.
    user_id = st.session_state["user"]["id"]

    # Fetch only this user's interview history.
    sessions = get_all_sessions(user_id=user_id)

    # Calculate interview statistics.
    total_interviews = len(sessions)

    completed = sum(
        1 for session in sessions
        if session["status"] == "completed"
    )

    in_progress = sum(
        1 for session in sessions
        if session["status"] == "in_progress"
    )

    abandoned = sum(
        1 for session in sessions
        if session["status"] == "abandoned"
    )

    # Calculate average score.
    score_total = 0.0
    evaluated_sessions = 0

    for session in sessions:
        summary = get_session_score_summary(
            session["session_id"],
            user_id=user_id,
        )

        if summary["valid_eval_count"] > 0:
            score_total += summary["avg_overall"]
            evaluated_sessions += 1

    average_score = (
        round(score_total / evaluated_sessions, 1)
        if evaluated_sessions > 0
        else 0.0
    )

    # Welcome section.
    st.title("Welcome to HR Interview Simulator")

    st.caption(
        "Practice interviews, improve your answers, "
        "and track your interview performance."
    )

    if st.button(
        "➕ Start New Interview",
        type="primary",
    ):
        st.session_state["page"] = "setup"
        st.rerun()

    st.divider()

    # Overview.
    render_section_header(
        "Your Overview",
        "A summary of your interview activity."
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card(
            "Total Interviews",
            total_interviews,
        )

    with col2:
        render_metric_card(
            "Completed",
            completed,
        )

    with col3:
        render_metric_card(
            "In Progress",
            in_progress,
        )

    with col4:
        render_metric_card(
            "Average Score",
            f"{average_score}/10" if evaluated_sessions else "N/A",
        )

    st.divider()

    # Recent interview sessions.
    render_section_header(
        "Recent Interviews",
        "Your latest interview sessions."
    )

    if not sessions:
        render_empty_state(
            "No interviews yet",
            "Start your first interview to see your activity here."
        )

    else:
        recent_sessions = sessions[:5]

        display_rows = []

        for session in recent_sessions:
            display_rows.append({
                "Role": session["role"],
                "Experience": session["experience_level"],
                "Difficulty": session["difficulty"],
                "Status": session["status"].replace(
                    "_", " "
                ).title(),
                "Questions": session["questions_count"],
                "Created": session["created_at"][:16].replace(
                    "T", " "
                ),
            })

        st.dataframe(
            display_rows,
            use_container_width=True,
            hide_index=True,
        )

    st.caption(
        f"Abandoned interviews: {abandoned}"
    )
