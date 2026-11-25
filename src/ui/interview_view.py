
    # import streamlit as st

    # from src.config import DEFAULT_MODEL
    # from src.core.interview_engine import InterviewEngine
    # from src.core.evaluator import AnswerEvaluator
    # from src.services.openrouter_client import (
    #     OpenRouterClient,
    #     AuthenticationError,
    # )
    # from src.storage.db import init_db
    # from src.ui.components import (
    #     render_section_header,
    #     render_progress,
    #     render_score_card,
    #     render_empty_state,
    # )


    # # --------------------------------------------------
    # # 1. CREATE AI SERVICES
    # # --------------------------------------------------

    # def _create_ai_services():
    #     """Create one OpenRouter client for interview and evaluation."""

    #     api_key = st.secrets.get("API_KEY", "")

    #     client = OpenRouterClient(
    #         api_key=api_key,
    #         model=DEFAULT_MODEL,
    #     )

    #     engine = InterviewEngine(client=client)
    #     evaluator = AnswerEvaluator(client=client)

    #     return engine, evaluator


    # # --------------------------------------------------
    # # 2. START A NEW INTERVIEW
    # # --------------------------------------------------

    # def _start_interview():
    #     """Create and initialize a new interview session."""

    #     setup = st.session_state.get("interview_setup")

    #     if not setup:
    #         st.error("Interview setup not found. Please configure your interview first.")
    #         st.session_state["page"] = "setup"
    #         st.rerun()
    #         return

    #     try:
    #         init_db()

    #         engine, evaluator = _create_ai_services()

    #         session = engine.create_session(
    #             role=setup["role"],
    #             experience_level=setup["experience_level"],
    #             difficulty=setup["difficulty"],
    #             total_questions=setup["total_questions"],
    #             resume_summary=setup.get("resume_summary"),
    #         )

    #         st.session_state["interview_engine"] = engine
    #         st.session_state["answer_evaluator"] = evaluator
    #         st.session_state["interview_session"] = session

    #         st.session_state["current_question"] = None
    #         st.session_state["current_answer"] = ""
    #         st.session_state["current_evaluation"] = None

    #         st.session_state["evaluated_question_ids"] = []
    #         st.session_state["evaluation_in_progress"] = False
    #         st.session_state["evaluation_error"] = None

    #         st.session_state["page"] = "interview"

    #         st.rerun()

    #     except AuthenticationError as error:
    #         st.error(f"OpenRouter configuration error: {error}")

    #     except Exception as error:
    #         st.error(f"Unable to start the interview: {error}")


    # # --------------------------------------------------
    # # 3. GENERATE OR REUSE CURRENT QUESTION
    # # --------------------------------------------------

    # def _get_current_question():
    #     """Return the existing question or generate the next question."""

    #     question = st.session_state.get("current_question")

    #     if question is not None:
    #         return question

    #     session = st.session_state.get("interview_session")
    #     engine = st.session_state.get("interview_engine")

    #     if session is None or engine is None:
    #         return None

    #     if session.status == "completed":
    #         return None

    #     if len(session.questions) >= session.total_questions:
    #         return None

    #     try:
    #         question = engine.generate_next_question(session)

    #         st.session_state["current_question"] = question
    #         st.session_state["current_answer"] = ""
    #         st.session_state["current_evaluation"] = None

    #         return question

    #     except Exception as error:
    #         st.error(f"Unable to generate the next question: {error}")
    #         return None


    # # --------------------------------------------------
    # # 4. SUBMIT AND EVALUATE ANSWER
    # # --------------------------------------------------

    # def _submit_answer(question, answer):
    #     """Save the candidate answer and request AI evaluation."""

    #     session = st.session_state.get("interview_session")
    #     engine = st.session_state.get("interview_engine")
    #     evaluator = st.session_state.get("answer_evaluator")

    #     if session is None or engine is None or evaluator is None:
    #         st.error("Interview session is not initialized.")
    #         return

    #     answer = answer.strip()

    #     # Validate before saving the answer.
    #     is_valid, error_message = evaluator.validate_input(answer)

    #     if not is_valid:
    #         st.warning(error_message)
    #         return

    #     evaluated_ids = st.session_state.get(
    #         "evaluated_question_ids", []
    #     )

    #     if question.id in evaluated_ids:
    #         st.warning("This question has already been evaluated.")
    #         return

    #     if st.session_state.get("evaluation_in_progress"):
    #         st.warning("Evaluation is already in progress.")
    #         return

    #     st.session_state["evaluation_in_progress"] = True

    #     try:
    #         with st.spinner("Saving your answer and evaluating it with AI..."):

    #             # Save answer in memory and SQLite.
    #             engine.record_answer(
    #                 session,
    #                 question.id,
    #                 answer,
    #             )

    #             # Evaluate the answer.
    #             result = evaluator.evaluate(
    #                 role=session.role,
    #                 experience_level=session.experience_level,
    #                 difficulty=session.difficulty,
    #                 category=question.category,
    #                 question_id=question.id,
    #                 question_text=question.question_text,
    #                 candidate_answer=answer,
    #                 session_id=session.session_id,
    #                 is_follow_up=question.is_follow_up,
    #             )

    #         if not result.is_valid:
    #         st.session_state["current_answer"] = answer
    #         st.session_state["current_evaluation"] = None
    #         st.session_state["evaluation_error"] = (
    #             result.error_message or "Evaluation failed. You can retry."
    #         )
    #         return

    #         st.session_state["current_answer"] = answer
    #         st.session_state["current_evaluation"] = result
    #         st.session_state["evaluation_error"] = None

    #         evaluated_ids.append(question.id)

    #         st.session_state["evaluated_question_ids"] = evaluated_ids

    #         st.success("Your answer has been evaluated successfully!")

    #     except Exception as error:
    #         st.session_state["current_answer"] = answer

    #         st.error(f"Unable to evaluate your answer: {error}")

    #     finally:
    #         st.session_state["evaluation_in_progress"] = False


    # # --------------------------------------------------
    # # 5. DISPLAY EVALUATION RESULTS
    # # --------------------------------------------------

    # def _render_evaluation(result):
    #     """Display scores, strengths, weaknesses and suggestions."""

    #     if result is None:
    #         return

    #     if not result.is_valid:
    #         st.error(result.error_message or "Evaluation is unavailable.")
    #         return

    #     st.divider()

    #     render_section_header(
    #         "Your Evaluation",
    #         "AI-powered feedback on your interview answer.",
    #     )

    #     scores = result.scores

    #     # Overall score
    #     overall = scores.overall

    #     st.metric(
    #         label="Overall Score",
    #         value=f"{overall:.1f}/10" if overall is not None else "N/A",
    #     )

    #     # Four dimension scores
    #     st.subheader("Performance Breakdown")

    #     columns = st.columns(4)

    #     dimensions = [
    #         ("Relevance", scores.relevance),
    #         ("Technical", scores.technical),
    #         ("Communication", scores.communication),
    #         ("Structure", scores.structure),
    #     ]

    #     for column, (label, score) in zip(columns, dimensions):
    #         with column:
    #             render_score_card(label, score)

    #     # Strengths
    #     st.subheader("Your Strengths")

    #     if result.strengths:
    #         for item in result.strengths:
    #             st.markdown(f"**✓ {item.point}**")

    #             if item.evidence_quote:
    #                 st.caption(f'Evidence: "{item.evidence_quote}"')

    #             if not item.is_verified:
    #                 st.caption("Evidence could not be fully verified.")

    #     else:
    #         render_empty_state(
    #             "No strengths identified",
    #             "The evaluator did not return specific strengths.",
    #         )

    #     # Weaknesses
    #     st.subheader("Areas to Improve")

    #     if result.weaknesses:
    #         for item in result.weaknesses:
    #             st.markdown(f"**• {item.point}**")

    #             if item.evidence_quote:
    #                 st.caption(f'Evidence: "{item.evidence_quote}"')

    #             if item.suggestion:
    #                 st.info(item.suggestion)

    #     else:
    #         render_empty_state(
    #             "No specific weaknesses returned",
    #             "Keep practising to improve your answers.",
    #         )

    #     # Actionable tips
    #     st.subheader("Actionable Improvement Tips")

    #     if result.actionable_tips:
    #         for index, tip in enumerate(result.actionable_tips, start=1):
    #             st.markdown(f"{index}. {tip}")

    #     else:
    #         st.caption("No additional tips were returned.")

    #     # Model answer
    #     if result.model_answer:
    #         with st.expander("View an Example of a Strong Answer"):
    #             st.write(result.model_answer)


    # # --------------------------------------------------
    # # 6. DISPLAY INTERVIEW COMPLETION
    # # --------------------------------------------------

    # def _render_completion(session):
    #     """Display the interview completion screen."""

    #     st.success("Congratulations! Your interview is completed.")

    #     st.title("Interview Completed")

    #     st.write(
    #         "You have completed all the configured interview questions."
    #     )

    #     st.metric(
    #         "Questions Answered",
    #         f"{len(session.questions)} / {session.total_questions}",
    #     )

    #     st.divider()

    #     st.subheader("What happens next?")

    #     st.write(
    #         "Your interview answers and valid evaluation results "
    #         "are stored in the project database."
    #     )

    #     if st.button("Back to Dashboard", type="primary"):
    #         st.session_state["page"] = "dashboard"
    #         st.rerun()


    # # --------------------------------------------------
    # # 7. MAIN INTERVIEW SCREEN
    # # --------------------------------------------------

    # def show_interview():
    #     """Render the complete interview room."""

    #     session = st.session_state.get("interview_session")

    #     # No active interview.
    #     if session is None:
    #         st.warning("No active interview session found.")

    #         if st.button("Start Interview", type="primary"):
    #             _start_interview()

    #         return

    #     st.title("Live Interview Room")

    #     st.caption(
    #         f"{session.role} | "
    #         f"{session.experience_level} | "
    #         f"{session.difficulty} Difficulty"
    #     )

    #     st.divider()

    #     # Get current question.
    #     question = _get_current_question()

    #     # No more questions.
    #     if question is None:

    #         if session.status == "completed":
    #             _render_completion(session)
    #         else:
    #             st.info(
    #                 "No question is currently available. "
    #                 "Please check the interview state."
    #             )

    #         return

    #     # Progress.
    #     question_number = question.question_index
    #     total_questions = session.total_questions

    #     st.subheader(
    #         f"Question {question_number} of {total_questions}"
    #     )

    #     render_progress(
    #         min(question_number - 1, total_questions),
    #         total_questions,
    #     )

    #     st.caption(f"Category: {question.category}")

    #     # Question.
    #     st.markdown("### Interview Question")

    #     st.markdown(
    #         f"**{question.question_text}**"
    #     )

    #     st.divider()

    #     # Check existing evaluation.
    #     result = st.session_state.get("current_evaluation")

    #     # Answer input and submission.
    #     if result is None:

    #         st.subheader("Your Answer")

    #     if st.session_state.get("evaluation_error"):
    #         st.error(st.session_state["evaluation_error"])

    #         answer = st.text_area(
    #             "Write your response below",
    #             value=st.session_state.get("current_answer", ""),
    #             height=200,
    #             placeholder="Type your interview answer here...",
    #             key=f"answer_{question.id}",
    #         )

    #         if st.button(
    #             "Submit Answer & Evaluate",
    #             type="primary",
    #             use_container_width=True,
    #             disabled=st.session_state.get("evaluation_in_progress", False),
    #         ):
    #             st.session_state["current_answer"] = answer

    #             _submit_answer(question, answer)

    #             st.rerun()

    #     # Display successful evaluation.
    #     else:

    #         _render_evaluation(result)

    #         st.divider()

    #         # Continue only after successful evaluation.
    #         if session.status == "completed":

    #             _render_completion(session)

    #         else:

    #             if st.button(
    #                 "Next Question",
    #                 type="primary",
    #                 use_container_width=True,
    #             ):

    #                 st.session_state["current_question"] = None
    #                 st.session_state["current_answer"] = ""
    #                 st.session_state["current_evaluation"] = None

    #                 st.rerun()



import streamlit as st

from src.config import DEFAULT_MODEL
from src.core.interview_engine import InterviewEngine
from src.core.evaluator import AnswerEvaluator
from src.services.openrouter_client import (
    OpenRouterClient,
    AuthenticationError,
)
from src.storage.db import init_db
from src.ui.components import (
    render_section_header,
    render_progress,
    render_score_card,
    render_empty_state,
)


# --------------------------------------------------
# 1. CREATE AI SERVICES
# --------------------------------------------------

def _create_ai_services():
    """Create one OpenRouter client for interview and evaluation."""

    api_key = st.secrets.get("API_KEY", "")

    client = OpenRouterClient(
        api_key=api_key,
        model=DEFAULT_MODEL,
    )

    engine = InterviewEngine(client=client)
    evaluator = AnswerEvaluator(client=client)

    return engine, evaluator


# --------------------------------------------------
# 2. START A NEW INTERVIEW
# --------------------------------------------------

def _start_interview():
    """Create and initialize a new interview session."""

    setup = st.session_state.get("interview_setup")

    if not setup:
        st.error(
            "Interview setup not found. Please configure your interview first."
        )
        st.session_state["page"] = "setup"
        st.rerun()
        return

    try:
        init_db()

        engine, evaluator = _create_ai_services()

        current_user = st.session_state.get("user")

        if not current_user or not current_user.get("id"):
            st.error("Please log in before starting an interview.")
            st.session_state.clear()
            st.rerun()
            return

        session = engine.create_session(
            role=setup["role"],
            experience_level=setup["experience_level"],
            difficulty=setup["difficulty"],
            total_questions=setup["total_questions"],
            resume_summary=setup.get("resume_summary"),
            user_id=current_user["id"],
        )

        st.session_state["interview_engine"] = engine
        st.session_state["answer_evaluator"] = evaluator
        st.session_state["interview_session"] = session

        st.session_state["current_question"] = None
        st.session_state["current_answer"] = ""
        st.session_state["current_evaluation"] = None

        st.session_state["evaluated_question_ids"] = []
        st.session_state["evaluation_in_progress"] = False
        st.session_state["evaluation_error"] = None

        st.session_state["page"] = "interview"

        st.rerun()

    except AuthenticationError as error:
        st.error(f"OpenRouter configuration error: {error}")

    except Exception as error:
        st.error(f"Unable to start the interview: {error}")


# --------------------------------------------------
# 3. GENERATE OR REUSE CURRENT QUESTION
# --------------------------------------------------

def _get_current_question():
    """Return the existing question or generate the next question."""

    question = st.session_state.get("current_question")

    if question is not None:
        return question

    session = st.session_state.get("interview_session")
    engine = st.session_state.get("interview_engine")

    if session is None or engine is None:
        return None

    if session.status == "completed":
        return None

    if len(session.questions) >= session.total_questions:
        return None

    try:
        question = engine.generate_next_question(session)

        st.session_state["current_question"] = question
        st.session_state["current_answer"] = ""
        st.session_state["current_evaluation"] = None
        st.session_state["evaluation_error"] = None

        return question

    except Exception as error:
        st.error(f"Unable to generate the next question: {error}")
        return None


# --------------------------------------------------
# 4. SUBMIT AND EVALUATE ANSWER
# --------------------------------------------------

def _submit_answer(question, answer):
    """Save the candidate answer and request AI evaluation."""

    session = st.session_state.get("interview_session")
    engine = st.session_state.get("interview_engine")
    evaluator = st.session_state.get("answer_evaluator")

    if session is None or engine is None or evaluator is None:
        st.session_state["evaluation_error"] = (
            "Interview session is not initialized."
        )
        return

    answer = answer.strip()

    # Validate the answer before saving.
    is_valid, error_message = evaluator.validate_input(answer)

    if not is_valid:
        st.session_state["evaluation_error"] = error_message
        return

    evaluated_ids = st.session_state.get(
        "evaluated_question_ids", []
    )

    # Prevent duplicate evaluations.
    if question.id in evaluated_ids:
        st.session_state["evaluation_error"] = (
            "This question has already been evaluated."
        )
        return

    # Prevent simultaneous evaluation.
    if st.session_state.get("evaluation_in_progress"):
        st.session_state["evaluation_error"] = (
            "Evaluation is already in progress."
        )
        return

    st.session_state["evaluation_in_progress"] = True
    st.session_state["evaluation_error"] = None

    # Preserve the answer before making the API request.
    st.session_state["current_answer"] = answer

    try:
        with st.spinner(
            "Saving your answer and evaluating it with AI..."
        ):

            # Save answer in memory and SQLite.
            engine.record_answer(
                session,
                question.id,
                answer,
            )

            # Request AI evaluation.
            result = evaluator.evaluate(
                role=session.role,
                experience_level=session.experience_level,
                difficulty=session.difficulty,
                category=question.category,
                question_id=question.id,
                question_text=question.question_text,
                candidate_answer=answer,
                session_id=session.session_id,
                is_follow_up=question.is_follow_up,
                user_id=session.user_id,
            )

        # Handle an unsuccessful evaluation.
        if not result.is_valid:
            st.session_state["current_evaluation"] = None

            st.session_state["evaluation_error"] = (
                result.error_message
                or "Evaluation failed. Please try again."
            )
            return

        # Store successful evaluation.
        st.session_state["current_evaluation"] = result
        st.session_state["evaluation_error"] = None

        if question.id not in evaluated_ids:
            evaluated_ids.append(question.id)

        st.session_state["evaluated_question_ids"] = evaluated_ids

    except Exception as error:
        st.session_state["current_evaluation"] = None

        st.session_state["evaluation_error"] = (
            f"Unable to evaluate your answer: {error}"
        )

    finally:
        st.session_state["evaluation_in_progress"] = False


# --------------------------------------------------
# 5. DISPLAY EVALUATION RESULTS
# --------------------------------------------------

def _render_evaluation(result):
    """Display scores, strengths, weaknesses and suggestions."""

    if result is None:
        return

    if not result.is_valid:
        st.error(
            result.error_message or "Evaluation is unavailable."
        )
        return

    st.divider()

    render_section_header(
        "Your Evaluation",
        "AI-powered feedback on your interview answer.",
    )

    scores = result.scores

    # Overall score.
    overall = scores.overall

    st.metric(
        label="Overall Score",
        value=f"{overall:.1f}/10" if overall is not None else "N/A",
    )

    # Four dimension scores.
    st.subheader("Performance Breakdown")

    columns = st.columns(4)

    dimensions = [
        ("Relevance", scores.relevance),
        ("Technical", scores.technical),
        ("Communication", scores.communication),
        ("Structure", scores.structure),
    ]

    for column, (label, score) in zip(columns, dimensions):
        with column:
            render_score_card(label, score)

    # Strengths.
    st.subheader("Your Strengths")

    if result.strengths:
        for item in result.strengths:
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
        render_empty_state(
            "No strengths identified",
            "The evaluator did not return specific strengths.",
        )

    # Weaknesses.
    st.subheader("Areas to Improve")

    if result.weaknesses:
        for item in result.weaknesses:
            st.markdown(f"**• {item.point}**")

            if item.evidence_quote:
                st.caption(
                    f'Evidence: "{item.evidence_quote}"'
                )

            if item.suggestion:
                st.info(item.suggestion)

    else:
        render_empty_state(
            "No specific weaknesses returned",
            "Keep practising to improve your answers.",
        )

    # Actionable tips.
    st.subheader("Actionable Improvement Tips")

    if result.actionable_tips:
        for index, tip in enumerate(
            result.actionable_tips,
            start=1,
        ):
            st.markdown(f"{index}. {tip}")

    else:
        st.caption("No additional tips were returned.")

    # Model answer.
    if result.model_answer:
        with st.expander("View an Example of a Strong Answer"):
            st.write(result.model_answer)


# --------------------------------------------------
# 6. DISPLAY INTERVIEW COMPLETION
# --------------------------------------------------

def _render_completion(session):
    """Display the interview completion screen."""

    st.success("Congratulations! Your interview is completed.")

    st.title("Interview Completed")

    st.write(
        "You have completed all the configured interview questions."
    )

    st.metric(
        "Questions Answered",
        f"{len(session.questions)} / {session.total_questions}",
    )

    st.divider()

    st.subheader("What happens next?")

    st.write(
        "Your interview answers and valid evaluation results "
        "are stored in the project database."
    )

    if st.button("Back to Dashboard", type="primary"):
        st.session_state["page"] = "dashboard"
        st.rerun()


# --------------------------------------------------
# 7. MAIN INTERVIEW SCREEN
# --------------------------------------------------

def show_interview():
    """Render the complete interview room."""

    session = st.session_state.get("interview_session")

    # No active interview.
    if session is None:
        st.warning("No active interview session found.")

        if st.button("Start Interview", type="primary"):
            _start_interview()

        return

    st.title("Live Interview Room")

    st.caption(
        f"{session.role} | "
        f"{session.experience_level} | "
        f"{session.difficulty} Difficulty"
    )

    st.divider()

    # Get current question.
    question = _get_current_question()

    # No more questions.
    if question is None:

        if session.status == "completed":
            _render_completion(session)

        else:
            st.info(
                "No question is currently available. "
                "Please check the interview state."
            )

        return

    # Progress.
    question_number = question.question_index
    total_questions = session.total_questions

    st.subheader(
        f"Question {question_number} of {total_questions}"
    )

    render_progress(
        min(question_number - 1, total_questions),
        total_questions,
    )

    st.caption(f"Category: {question.category}")

    # Display question.
    st.markdown("### Interview Question")
    st.markdown(f"**{question.question_text}**")

    st.divider()

    # Get existing evaluation.
    result = st.session_state.get("current_evaluation")

    # Answer input and submission.
    if result is None:

        st.subheader("Your Answer")

        # Display any saved error.
        evaluation_error = st.session_state.get(
            "evaluation_error"
        )

        if evaluation_error:
            st.error(evaluation_error)

        answer = st.text_area(
            "Write your response below",
            value=st.session_state.get("current_answer", ""),
            height=200,
            placeholder="Type your interview answer here...",
            key=f"answer_{question.id}",
        )

        if st.button(
            "Submit Answer & Evaluate",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.get(
                "evaluation_in_progress", False
            ),
        ):
            st.session_state["current_answer"] = answer

            _submit_answer(question, answer)

            st.rerun()

    # Display successful evaluation.
    else:

        _render_evaluation(result)

        st.divider()

        if session.status == "completed":

            _render_completion(session)

        else:

            if st.button(
                "Next Question",
                type="primary",
                use_container_width=True,
            ):

                st.session_state["current_question"] = None
                st.session_state["current_answer"] = ""
                st.session_state["current_evaluation"] = None
                st.session_state["evaluation_error"] = None

                st.rerun()
