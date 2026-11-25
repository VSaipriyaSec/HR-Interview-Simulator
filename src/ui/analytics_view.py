import streamlit as st
import pandas as pd

from src.storage.db import (
    get_all_sessions,
    get_session_score_summary,
)


def show_analytics():
    st.title("History & Analytics")

    user = st.session_state.get("user")
    if not user:
        st.warning("Please login to continue.")
        return

    try:
        sessions = get_all_sessions(limit=100, user_id=user["id"])
    except Exception as error:
        st.error(f"Unable to load interview history: {error}")
        return

    if not sessions:
        st.info("No interview history available yet.")
        return

    completed = sum(
        1 for session in sessions
        if session.get("status") == "completed"
    )

    total = len(sessions)

    scores = []
    for session in sessions:
        summary = get_session_score_summary(
            session["session_id"], user_id=user["id"]
        )
        if summary["valid_eval_count"] > 0:
            scores.append({
                "Interview": session.get("role", "Interview"),
                "Score": summary["avg_overall"],
            })

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Interviews", total)
    col2.metric("Completed", completed)
    col3.metric(
        "Average Score",
        f"{sum(s['Score'] for s in scores) / len(scores):.1f}"
        if scores else "N/A"
    )

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Interview Status")
        st.vega_lite_chart(
            pd.DataFrame({
                "Status": ["Completed", "In Progress"],
                "Count": [completed, total - completed],
            }),
            {
                "mark": {"type": "arc", "innerRadius": 50},
                "encoding": {
                    "theta": {"field": "Count", "type": "quantitative"},
                    "color": {"field": "Status", "type": "nominal"},
                    "tooltip": ["Status", "Count"],
                },
            },
            use_container_width=True,
        )

    with right:
        st.subheader("Interview Scores")
        if scores:
            st.bar_chart(
                pd.DataFrame(scores).set_index("Interview")["Score"]
            )
        else:
            st.info("No evaluated interviews available yet.")

    st.divider()
    st.subheader("Interview History")

    history = [
        {
            "Role": s.get("role", ""),
            "Experience": s.get("experience_level", ""),
            "Difficulty": s.get("difficulty", ""),
            "Status": s.get("status", ""),
            "Date": s.get("created_at", ""),
        }
        for s in sessions
    ]

    st.dataframe(history, use_container_width=True, hide_index=True)