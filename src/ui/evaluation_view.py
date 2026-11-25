
import streamlit as st

from src.storage.db import (
    get_session,
    get_session_evaluations,
)

from src.ui.components import (
    render_section_header,
    render_score_card,
    render_empty_state,
)


def show_evaluation():
    """Display the logged-in user's evaluation report."""

    st.title("Evaluation & Feedback")
    st.caption(
        "Understand your interview performance and identify areas to improve."
    )

    st.divider()

    # Get the logged-in user's ID.
    user_id = st.session_state["user"]["id"]

    # 1. Check for an active or selected interview session.

    session_id = st.session_state.get("selected_session_id")

    if not session_id:
        active_session = st.session_state.get("interview_session")

        if active_session:
            session_id = active_session.session_id

    if not session_id:
        st.info(
            "No interview selected. Complete an interview or select "
            "a previous interview from History & Analytics."
        )
        return

    # 2. Retrieve only this user's session.

    session = get_session(
        session_id,
        user_id=user_id,
    )

    if session is None:
        st.error("The selected interview could not be found.")
        return

    st.subheader(session.role)

    st.caption(
        f"{session.experience_level} | "
        f"{session.difficulty} Difficulty"
    )

    # 3. Retrieve only this user's evaluation results.

    evaluations = get_session_evaluations(
        session_id,
        user_id=user_id,
    )

    valid_evaluations = [
        evaluation
        for evaluation in evaluations
        if evaluation.is_valid
    ]

    if not valid_evaluations:
        render_empty_state(
            "No evaluation results available",
            "There are no valid AI evaluation results for this interview yet."
        )
        return

    # 4. Calculate average scores.

    dimensions = [
        ("Relevance", "relevance"),
        ("Technical", "technical"),
        ("Communication", "communication"),
        ("Structure", "structure"),
    ]

    average_scores = {}

    for label, attribute in dimensions:
        values = [
            getattr(evaluation.scores, attribute)
            for evaluation in valid_evaluations
            if getattr(evaluation.scores, attribute) is not None
        ]

        average_scores[label] = (
            round(sum(values) / len(values), 1)
            if values else None
        )

    overall_values = [
        evaluation.scores.overall
        for evaluation in valid_evaluations
        if evaluation.scores.overall is not None
    ]

    overall_average = (
        round(sum(overall_values) / len(overall_values), 1)
        if overall_values else None
    )

    # 5. Overall performance summary.

    render_section_header(
        "Overall Performance",
        "Your average performance across evaluated answers."
    )

    st.metric(
        "Overall Interview Score",
        f"{overall_average}/10" if overall_average is not None else "N/A"
    )

    st.caption(
        f"{len(valid_evaluations)} valid evaluations available."
    )

    # 6. Four-dimensional score breakdown.

    st.subheader("Performance Breakdown")

    columns = st.columns(4)

    for column, (label, _) in zip(columns, dimensions):
        with column:
            render_score_card(
                label,
                average_scores[label]
            )

    chart_values = {
        label: score
        for label, score in average_scores.items()
        if score is not None
    }

    if chart_values:
        st.bar_chart(
            {"Score": chart_values},
            y_label="Score out of 10",
        )

    st.divider()

    # 7. Individual answer evaluations.

    render_section_header(
        "Question-wise Feedback",
        "Review your answer and AI feedback for each question."
    )

    for index, evaluation in enumerate(
        valid_evaluations,
        start=1,
    ):

        question = next(
            (
                item for item in session.questions
                if item.id == evaluation.question_id
            ),
            None,
        )

        question_title = (
            question.question_text
            if question
            else f"Question {index}"
        )

        with st.expander(
            f"Question {index}: {question_title[:100]}"
        ):

            if question:
                st.markdown("**Interview Question**")
                st.write(question.question_text)

                st.markdown("**Your Answer**")
                st.write(
                    question.user_answer
                    or "No answer was saved for this question."
                )

            st.divider()

            st.subheader("Scores")

            score_columns = st.columns(4)

            score_attributes = [
                ("Relevance", evaluation.scores.relevance),
                ("Technical", evaluation.scores.technical),
                ("Communication", evaluation.scores.communication),
                ("Structure", evaluation.scores.structure),
            ]

            for column, (label, score) in zip(
                score_columns,
                score_attributes,
            ):
                with column:
                    render_score_card(label, score)

            st.metric(
                "Overall Score",
                (
                    f"{evaluation.scores.overall}/10"
                    if evaluation.scores.overall is not None
                    else "N/A"
                )
            )

            # Strengths

            st.subheader("Strengths")

            if evaluation.strengths:
                for item in evaluation.strengths:
                    st.markdown(f"**✓ {item.point}**")

                    if item.evidence_quote:
                        st.caption(
                            f'Evidence: "{item.evidence_quote}"'
                        )

                    if not item.is_verified:
                        st.caption(
                            "Evidence could not be fully verified."
                        )
            else:
                st.caption("No specific strengths were returned.")

            # Weaknesses

            st.subheader("Areas to Improve")

            if evaluation.weaknesses:
                for item in evaluation.weaknesses:
                    st.markdown(f"**• {item.point}**")

                    if item.evidence_quote:
                        st.caption(
                            f'Evidence: "{item.evidence_quote}"'
                        )

                    if item.suggestion:
                        st.info(item.suggestion)
            else:
                st.caption("No specific weaknesses were returned.")

            # Actionable tips

            st.subheader("Actionable Tips")

            if evaluation.actionable_tips:
                for tip_index, tip in enumerate(
                    evaluation.actionable_tips,
                    start=1,
                ):
                    st.markdown(f"{tip_index}. {tip}")
            else:
                st.caption("No additional tips were returned.")

            # Model answer

            if evaluation.model_answer:
                with st.expander("View Example Strong Answer"):
                    st.write(evaluation.model_answer)

            st.caption(
                f"Evaluated at: {evaluation.evaluated_at}"
            )
