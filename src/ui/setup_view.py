
import streamlit as st

from src.config import (
    ROLES,
    EXPERIENCE_LEVELS,
    DIFFICULTIES,
    QUESTION_COUNT_OPTIONS,
    ALLOWED_RESUME_EXTENSIONS,
    MAX_RESUME_FILE_SIZE_MB,
)

from src.services.resume_parser import (
    ResumeParser,
    ResumeValidationError,
)

from src.ui.interview_view import _start_interview


def show_setup():
    """Displays the interview configuration screen."""

    st.title("Interview Setup")
    st.caption(
        "Configure your interview preferences before you begin."
    )

    st.divider()

    with st.form("interview_setup_form"):

        st.subheader("Job Preferences")

        role = st.selectbox(
            "Job Role",
            options=ROLES,
            index=0,
        )

        experience = st.selectbox(
            "Experience Level",
            options=EXPERIENCE_LEVELS,
            index=0,
        )

        difficulty = st.selectbox(
            "Interview Difficulty",
            options=DIFFICULTIES,
            index=1,
        )

        question_count = st.selectbox(
            "Number of Questions",
            options=QUESTION_COUNT_OPTIONS,
            index=1,
        )

        st.divider()

        st.subheader("Resume (Optional)")

        st.caption(
            "Upload a PDF, TXT, or MD resume. "
            f"Maximum size: {MAX_RESUME_FILE_SIZE_MB} MB."
        )

        resume_file = st.file_uploader(
            "Upload your resume",
            type=[
                extension.lstrip(".")
                for extension in ALLOWED_RESUME_EXTENSIONS
            ],
            accept_multiple_files=False,
        )

        submitted = st.form_submit_button(
            "Continue to Interview",
            type="primary",
            use_container_width=True,
        )

    if submitted:

        resume_summary = None

        if resume_file is not None:
            try:
                resume_text, resume_preview = ResumeParser.process_resume(
                    resume_file.name,
                    resume_file.getvalue(),
                )

                st.session_state["resume_preview"] = resume_preview

                resume_summary = resume_text

            except ResumeValidationError as error:
                st.error(f"Resume error: {error}")
                return

            except Exception:
                st.error(
                    "Unable to process the uploaded resume. "
                    "Please try another file."
                )
                return

        st.session_state["interview_setup"] = {
            "role": role,
            "experience_level": experience,
            "difficulty": difficulty,
            "total_questions": question_count,
            "resume_summary": resume_summary,
        }

        _start_interview()
