
"""
Core AI Interview Engine.
Orchestrates interview sessions, determines question progression across categories,
generates dynamic follow-ups, and integrates with OpenRouter with fallback safety.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.config import (
    QUESTION_CATEGORIES,
    DATA_DIR,
    DEFAULT_MODEL,
    DATABASE_PATH,
)
from src.models.interview import InterviewSession, InterviewQuestion
from src.services.openrouter_client import OpenRouterClient, OpenRouterAPIError
from src.core.prompt_templates import (
    build_question_generation_messages,
    build_follow_up_messages,
)
from src.storage.db import (
    save_session,
    save_question,
    update_question_answer,
    update_session_status,
)

logger = logging.getLogger(__name__)


class InterviewEngine:
    """Manages the lifecycle of an AI-powered interview session."""

    def __init__(
        self,
        client: Optional[OpenRouterClient] = None,
        db_path: Path = DATABASE_PATH,
    ):
        self.client = client
        self.db_path = db_path
        self._seed_questions = self._load_seed_questions()

    @staticmethod
    def _load_seed_questions() -> Dict[str, Any]:
        """Loads fallback questions from default_questions.json."""

        seed_path = DATA_DIR / "default_questions.json"

        if seed_path.exists():
            try:
                with open(seed_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as error:
                logger.error(
                    f"Failed to load seed questions: {error}"
                )

        return {}

    def create_session(
        self,
        role: str,
        experience_level: str,
        difficulty: str,
        total_questions: int = 5,
        resume_summary: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> InterviewSession:
        """Creates and persists a session for the authenticated user."""

        if user_id is None:
            raise ValueError(
                "A logged-in user is required to create an interview."
            )

        session = InterviewSession(
            user_id=user_id,
            role=role,
            experience_level=experience_level,
            difficulty=difficulty,
            total_questions=total_questions,
            resume_summary=resume_summary,
        )

        save_session(
            session,
            self.db_path,
            user_id=user_id,
        )

        return session

    def _determine_category_for_step(
        self,
        question_index: int,
        total_questions: int,
    ) -> str:
        """
        Calculates an optimal category mix:
        - 1st question: HR & Background
        - Middle questions: Technical & Domain
        - Later questions: Behavioral (STAR Method)
        """

        if question_index == 1:
            return "HR & Background"

        elif question_index == total_questions:
            return "Behavioral (STAR Method)"

        else:
            if question_index % 2 == 0:
                return "Technical & Domain"

            return "Behavioral (STAR Method)"

    def generate_next_question(
        self,
        session: InterviewSession,
        forced_category: Optional[str] = None,
    ) -> InterviewQuestion:
        """Generates the next question using AI or fallback questions."""

        if session.user_id is None:
            raise ValueError("Session has no authenticated owner.")

        next_index = len(session.questions) + 1

        category = (
            forced_category
            or self._determine_category_for_step(
                next_index,
                session.total_questions,
            )
        )

        prev_questions = [
            question.question_text
            for question in session.questions
        ]

        question_text = ""
        target_competency = "General Competency"
        context_hint = ""

        if self.client:
            try:
                messages = build_question_generation_messages(
                    role=session.role,
                    experience_level=session.experience_level,
                    difficulty=session.difficulty,
                    category=category,
                    question_index=next_index,
                    total_questions=session.total_questions,
                    previous_questions=prev_questions,
                    resume_context=session.resume_summary,
                )

                result = self.client.generate_chat_completion(
                    messages=messages,
                    session_id=session.session_id,
                    require_json=True,
                )

                content = result["content"]

                if isinstance(content, dict):
                    question_text = content.get("question", "")
                    category = content.get("category", category)
                    target_competency = content.get(
                        "target_competency",
                        "General",
                    )
                    context_hint = content.get("context_hint", "")

            except OpenRouterAPIError as error:
                logger.warning(
                    f"OpenRouter API call failed ({error}). "
                    "Using fallback question."
                )

        if not question_text:
            question_text = self._get_fallback_question(
                session.role,
                category,
                prev_questions,
            )

        question = InterviewQuestion(
            question_index=next_index,
            category=category,
            question_text=question_text,
            is_follow_up=False,
            target_competency=target_competency,
        )

        save_question(
            session.session_id,
            question,
            self.db_path,
            user_id=session.user_id,
        )

        session.questions.append(question)
        session.current_question_index = len(session.questions)

        return question

    def generate_follow_up_question(
        self,
        session: InterviewSession,
        parent_question: InterviewQuestion,
        candidate_answer: str,
    ) -> InterviewQuestion:
        """Generates a targeted follow-up question."""

        if session.user_id is None:
            raise ValueError("Session has no authenticated owner.")

        next_index = len(session.questions) + 1
        follow_up_text = ""
        target_competency = parent_question.target_competency

        if self.client and candidate_answer.strip():
            try:
                messages = build_follow_up_messages(
                    role=session.role,
                    experience_level=session.experience_level,
                    difficulty=session.difficulty,
                    current_question=parent_question.question_text,
                    candidate_answer=candidate_answer,
                    target_competency=target_competency,
                )

                result = self.client.generate_chat_completion(
                    messages=messages,
                    session_id=session.session_id,
                    require_json=True,
                )

                content = result["content"]

                if isinstance(content, dict):
                    follow_up_text = content.get("question", "")
                    target_competency = content.get(
                        "target_competency",
                        target_competency,
                    )

            except OpenRouterAPIError as error:
                logger.warning(
                    f"Follow-up generation failed ({error}). "
                    "Using generic follow-up."
                )

        if not follow_up_text:
            follow_up_text = (
                f"You mentioned key points in your previous answer "
                f"regarding {target_competency}. "
                "Could you walk me through a specific challenge "
                "you faced while implementing that, and how you "
                "measured the final outcome?"
            )

        question = InterviewQuestion(
            question_index=next_index,
            category="Follow-Up (Deep Dive)",
            question_text=follow_up_text,
            is_follow_up=True,
            parent_question_id=parent_question.id,
            target_competency=target_competency,
        )

        save_question(
            session.session_id,
            question,
            self.db_path,
            user_id=session.user_id,
        )

        session.questions.append(question)
        session.current_question_index = len(session.questions)

        return question

    def record_answer(
        self,
        session: InterviewSession,
        question_id: str,
        user_answer: str,
    ) -> None:
        """Records the candidate's answer in memory and SQLite."""

        if session.user_id is None:
            raise ValueError("Session has no authenticated owner.")

        question_found = False

        for question in session.questions:
            if question.id == question_id:
                update_question_answer(
                    question_id,
                    user_answer,
                    self.db_path,
                    user_id=session.user_id,
                )

                question.user_answer = user_answer
                question_found = True
                break

        if not question_found:
            raise ValueError("Question does not belong to this session.")

        all_answered = all(
            question.user_answer is not None
            for question in session.questions
        )

        if (
            all_answered
            and len(session.questions) >= session.total_questions
        ):
            session.status = "completed"

            update_session_status(
                session.session_id,
                "completed",
                self.db_path,
                user_id=session.user_id,
            )

    def _get_fallback_question(
        self,
        role: str,
        category: str,
        previous_questions: List[str],
    ) -> str:
        """Returns a seed question ensuring no direct repetition."""

        role_questions = self._seed_questions.get(
            role,
            self._seed_questions.get("General", {}),
        )

        cat_questions = role_questions.get(
            category,
            [
                "Could you explain an impactful engineering "
                "problem you recently solved?"
            ],
        )

        for question in cat_questions:
            if question not in previous_questions:
                return question

        return cat_questions[0]
