
"""
AI Answer Evaluation and Feedback Engine.
Implements 4-dimensional scoring, sequence-aware evidence quote validation,
canonical weighted scoring, and defensive JSON response parsing.
"""

import re
import difflib
import logging
from typing import Tuple, Optional, List, Any
from pathlib import Path

from src.config import SCORING_WEIGHTS, DATABASE_PATH
from src.models.evaluation import (
    DimensionScores,
    EvidencePoint,
    EvaluationResult,
)
from src.services.openrouter_client import (
    OpenRouterClient,
    OpenRouterAPIError,
)
from src.core.prompt_templates import build_evaluation_messages
from src.storage.db import save_evaluation

logger = logging.getLogger(__name__)


def validate_evidence_quote(
    quote: str,
    candidate_answer: str,
    threshold: float = 0.80,
) -> Tuple[bool, str]:
    """Verifies whether an evidence quote appears in the candidate answer."""

    if not quote or not candidate_answer:
        return False, "[No evidence cited]"

    def tokenize(text: str) -> List[str]:
        clean = re.sub(r"[^\w\s]", "", text.lower())
        return clean.split()

    quote_tokens = tokenize(quote)
    answer_tokens = tokenize(candidate_answer)

    if len(quote_tokens) < 3:
        norm_q = " ".join(quote_tokens)
        norm_a = " ".join(answer_tokens)

        if norm_q and norm_q in norm_a:
            return True, f'"{quote.strip()}"'

        return False, "[Unverified: Quote too short or not found verbatim]"

    norm_q = " ".join(quote_tokens)
    norm_a = " ".join(answer_tokens)

    if norm_q in norm_a:
        return True, f'"{quote.strip()}"'

    matcher = difflib.SequenceMatcher(
        None,
        quote_tokens,
        answer_tokens,
    )

    match = matcher.find_longest_match(
        0,
        len(quote_tokens),
        0,
        len(answer_tokens),
    )

    contiguous_ratio = match.size / len(quote_tokens)

    if contiguous_ratio >= threshold:
        return True, f'"{quote.strip()}"'

    return False, "[AI Summary: Quote could not be verified from your answer]"


def parse_dimension_score(val: Any) -> Optional[float]:
    """Parses and clamps a dimension score to [0.0, 10.0]."""

    if val is None:
        return None

    try:
        if isinstance(val, str):
            val = val.split("/")[0].strip()

        num = float(val)
        return max(0.0, min(10.0, round(num, 1)))

    except (ValueError, TypeError):
        return None


def calculate_weighted_score(
    category: str,
    scores: DimensionScores,
) -> Optional[float]:
    """Calculates the canonical weighted evaluation score."""

    if (
        scores.relevance is None
        or scores.technical is None
        or scores.communication is None
        or scores.structure is None
    ):
        return None

    weights = SCORING_WEIGHTS.get(
        category,
        SCORING_WEIGHTS["Technical & Domain"],
    )

    overall = (
        scores.relevance * weights["relevance"]
        + scores.technical * weights["technical"]
        + scores.communication * weights["communication"]
        + scores.structure * weights["structure"]
    )

    return round(overall, 1)


class AnswerEvaluator:
    """Evaluates candidate answers against rubrics with evidence validation."""

    MIN_WORDS_REQUIRED = 5

    def __init__(
        self,
        client: Optional[OpenRouterClient] = None,
        db_path: Path = DATABASE_PATH,
    ):
        self.client = client
        self.db_path = db_path

    def validate_input(self, answer: str) -> Tuple[bool, str]:
        """Validates candidate answer input before sending it to the LLM."""

        if not answer or not answer.strip():
            return False, "Answer cannot be empty. Please provide your response."

        word_count = len(answer.strip().split())

        if word_count < self.MIN_WORDS_REQUIRED:
            return (
                False,
                f"Answer is too brief ({word_count} words). "
                "Please answer in at least 5 words for evaluation.",
            )

        return True, ""

    def evaluate(
        self,
        role: str,
        experience_level: str,
        difficulty: str,
        category: str,
        question_id: str,
        question_text: str,
        candidate_answer: str,
        session_id: str = "",
        is_follow_up: bool = False,
        user_id: Optional[int] = None,
    ) -> EvaluationResult:
        """Evaluates an answer and saves it under the authenticated user."""

        if user_id is None:
            raise ValueError(
                "A logged-in user is required to evaluate an answer."
            )

        is_valid_input, error_msg = self.validate_input(candidate_answer)

        if not is_valid_input:
            return EvaluationResult(
                question_id=question_id,
                session_id=session_id,
                is_valid=False,
                error_message=error_msg,
            )

        if not self.client:
            return EvaluationResult(
                question_id=question_id,
                session_id=session_id,
                is_valid=False,
                error_message=(
                    "OpenRouter client is not configured for evaluation."
                ),
            )

        messages = build_evaluation_messages(
            role=role,
            experience_level=experience_level,
            difficulty=difficulty,
            category=category,
            question_text=question_text,
            candidate_answer=candidate_answer,
            is_follow_up=is_follow_up,
        )

        try:
            response = self.client.generate_chat_completion(
                messages=messages,
                session_id=session_id,
                require_json=True,
                temperature=0.2,
                max_tokens=1000,
            )

            raw_data = response.get("content", {})

        except OpenRouterAPIError as error:
            logger.error(f"Evaluation API call failed: {error}")

            return EvaluationResult(
                question_id=question_id,
                session_id=session_id,
                is_valid=False,
                error_message=f"API evaluation failed: {str(error)}",
            )

        if not isinstance(raw_data, dict):
            return EvaluationResult(
                question_id=question_id,
                session_id=session_id,
                is_valid=False,
                error_message=(
                    "AI returned malformed or non-dictionary response."
                ),
            )

        relevance = parse_dimension_score(
            raw_data.get("relevance_score")
        )
        technical = parse_dimension_score(
            raw_data.get("technical_score")
        )
        communication = parse_dimension_score(
            raw_data.get("communication_score")
        )
        structure = parse_dimension_score(
            raw_data.get("structure_score")
        )

        scores = DimensionScores(
            relevance=relevance,
            technical=technical,
            communication=communication,
            structure=structure,
        )

        overall = calculate_weighted_score(category, scores)
        scores.overall = overall

        if overall is None:
            return EvaluationResult(
                question_id=question_id,
                session_id=session_id,
                scores=scores,
                is_valid=False,
                error_message=(
                    "One or more required evaluation scores "
                    "could not be parsed."
                ),
            )

        strengths = []

        for item in raw_data.get("strengths", []):
            if isinstance(item, dict):
                point = item.get("point", "")
                raw_quote = item.get("evidence_quote", "")

                verified, display_quote = validate_evidence_quote(
                    raw_quote,
                    candidate_answer,
                )

                strengths.append(
                    EvidencePoint(
                        point=point,
                        evidence_quote=display_quote,
                        is_verified=verified,
                    )
                )

        weaknesses = []

        for item in raw_data.get("weaknesses", []):
            if isinstance(item, dict):
                point = item.get("point", "")
                raw_quote = item.get("evidence_quote", "")
                suggestion = item.get("suggestion", "")

                verified, display_quote = validate_evidence_quote(
                    raw_quote,
                    candidate_answer,
                )

                weaknesses.append(
                    EvidencePoint(
                        point=point,
                        evidence_quote=display_quote,
                        is_verified=verified,
                        suggestion=suggestion,
                    )
                )

        actionable_tips = raw_data.get("actionable_tips", [])

        if not isinstance(actionable_tips, list):
            actionable_tips = [str(actionable_tips)]

        model_answer = raw_data.get("model_answer", "")

        result = EvaluationResult(
            question_id=question_id,
            session_id=session_id,
            scores=scores,
            strengths=strengths,
            weaknesses=weaknesses,
            actionable_tips=actionable_tips,
            model_answer=model_answer,
            is_valid=True,
        )

        try:
            save_evaluation(
                result,
                self.db_path,
                user_id=user_id,
            )

        except Exception as error:
            logger.error(
                f"Could not persist evaluation to SQLite: {error}"
            )

            result.is_valid = False
            result.error_message = (
                "Evaluation was generated but could not be saved. "
                "Please try again."
            )

        return result
