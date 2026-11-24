"""
AI Answer Evaluation and Feedback Engine.
Implements 4-dimensional scoring, sequence-aware evidence quote validation,
canonical weighted scoring, and defensive JSON response parsing.
"""

import re
import difflib
import logging
from typing import Tuple, Optional, List, Dict, Any
from pathlib import Path

from src.config import SCORING_WEIGHTS, DATABASE_PATH
from src.models.evaluation import DimensionScores, EvidencePoint, EvaluationResult
from src.services.openrouter_client import OpenRouterClient, OpenRouterAPIError
from src.core.prompt_templates import build_evaluation_messages
from src.storage.db import save_evaluation

logger = logging.getLogger(__name__)


def validate_evidence_quote(quote: str, candidate_answer: str, threshold: float = 0.80) -> Tuple[bool, str]:
    """
    Sequence-aware verification of evidence quotes.
    Uses the longest contiguous matching token sequence divided by quote token count
    as the partial-match criterion, requiring minimum 3-word quote and 80% threshold.

    Returns:
        Tuple of (is_valid: bool, display_quote: str)
    """
    if not quote or not candidate_answer:
        return False, "[No evidence cited]"

    # Normalize by lowercase and removing punctuation
    def tokenize(text: str) -> List[str]:
        clean = re.sub(r"[^\w\s]", "", text.lower())
        return clean.split()

    quote_tokens = tokenize(quote)
    answer_tokens = tokenize(candidate_answer)

    # Disallow trivial 1-2 word snippets
    if len(quote_tokens) < 3:
        norm_q = " ".join(quote_tokens)
        norm_a = " ".join(answer_tokens)
        if norm_q and norm_q in norm_a:
            return True, f'"{quote.strip()}"'
        return False, "[Unverified: Quote too short or not found verbatim]"

    # Direct contiguous phrase match (Fast Path)
    norm_q = " ".join(quote_tokens)
    norm_a = " ".join(answer_tokens)
    if norm_q in norm_a:
        return True, f'"{quote.strip()}"'

    # Sequence-aware token matching
    matcher = difflib.SequenceMatcher(None, quote_tokens, answer_tokens)
    match = matcher.find_longest_match(0, len(quote_tokens), 0, len(answer_tokens))

    # Criterion: longest contiguous sequence of tokens divided by total quote tokens
    contiguous_ratio = match.size / len(quote_tokens)

    if contiguous_ratio >= threshold:
        return True, f'"{quote.strip()}"'

    # Rejection: Fabricated quote, scrambled words, or insufficient overlap
    return False, "[AI Summary: Quote could not be verified from your answer]"


def parse_dimension_score(val: Any) -> Optional[float]:
    """
    Parses and clamps a dimension score to [0.0, 10.0].
    Returns None if the value is missing, invalid, or unparseable.
    Does NOT silently default to 5.0.
    """
    if val is None:
        return None

    try:
        if isinstance(val, str):
            val = val.split("/")[0].strip()
        num = float(val)
        return max(0.0, min(10.0, round(num, 1)))
    except (ValueError, TypeError):
        return None


def calculate_weighted_score(category: str, scores: DimensionScores) -> Optional[float]:
    """
    Calculates the canonical weighted score using SCORING_WEIGHTS.
    Returns None if any required dimension score is missing/invalid.
    """
    if (
        scores.relevance is None or
        scores.technical is None or
        scores.communication is None or
        scores.structure is None
    ):
        return None

    weights = SCORING_WEIGHTS.get(category, SCORING_WEIGHTS["Technical & Domain"])

    overall = (
        scores.relevance * weights["relevance"] +
        scores.technical * weights["technical"] +
        scores.communication * weights["communication"] +
        scores.structure * weights["structure"]
    )
    return round(overall, 1)


class AnswerEvaluator:
    """Evaluates candidate answers against rubrics with evidence validation."""

    MIN_WORDS_REQUIRED = 5

    def __init__(self, client: Optional[OpenRouterClient] = None, db_path: Path = DATABASE_PATH):
        self.client = client
        self.db_path = db_path

    def validate_input(self, answer: str) -> Tuple[bool, str]:
        """
        Validates candidate answer input before sending to LLM.
        """
        if not answer or not answer.strip():
            return False, "Answer cannot be empty. Please provide your response."

        word_count = len(answer.strip().split())
        if word_count < self.MIN_WORDS_REQUIRED:
            return False, f"Answer is too brief ({word_count} words). Please answer in at least 5 words for evaluation."

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
        is_follow_up: bool = False
    ) -> EvaluationResult:
        """
        Evaluates a candidate answer.
        Returns an EvaluationResult object with validated scores and evidence.
        """
        # 1. Guardrail Input Validation
        is_valid_input, error_msg = self.validate_input(candidate_answer)
        if not is_valid_input:
            result = EvaluationResult(
                question_id=question_id,
                session_id=session_id,
                is_valid=False,
                error_message=error_msg
            )
            return result

        if not self.client:
            return EvaluationResult(
                question_id=question_id,
                session_id=session_id,
                is_valid=False,
                error_message="OpenRouter client is not configured for evaluation."
            )

        # 2. Build Prompt Messages
        messages = build_evaluation_messages(
            role=role,
            experience_level=experience_level,
            difficulty=difficulty,
            category=category,
            question_text=question_text,
            candidate_answer=candidate_answer,
            is_follow_up=is_follow_up
        )

        # 3. Call LLM (Allocating sufficient token budget for complete evaluation JSON)
        try:
            response = self.client.generate_chat_completion(
                messages=messages,
                session_id=session_id,
                require_json=True,
                max_tokens=1800
            )
            raw_data = response.get("content", {})
        except OpenRouterAPIError as err:
            logger.error(f"Evaluation API call failed: {err}")
            return EvaluationResult(
                question_id=question_id,
                session_id=session_id,
                is_valid=False,
                error_message=f"API evaluation failed: {str(err)}"
            )

        if not isinstance(raw_data, dict):
            return EvaluationResult(
                question_id=question_id,
                session_id=session_id,
                is_valid=False,
                error_message="AI returned malformed or non-dictionary response."
            )

        # 4. Parse Dimension Scores
        relevance = parse_dimension_score(raw_data.get("relevance_score"))
        technical = parse_dimension_score(raw_data.get("technical_score"))
        communication = parse_dimension_score(raw_data.get("communication_score"))
        structure = parse_dimension_score(raw_data.get("structure_score"))

        scores = DimensionScores(
            relevance=relevance,
            technical=technical,
            communication=communication,
            structure=structure
        )

        overall = calculate_weighted_score(category, scores)
        scores.overall = overall

        # Check if all scores parsed successfully
        if overall is None:
            return EvaluationResult(
                question_id=question_id,
                session_id=session_id,
                scores=scores,
                is_valid=False,
                error_message="One or more required evaluation scores could not be parsed."
            )

        # 5. Extract & Validate Strengths with Evidence
        strengths = []
        for item in raw_data.get("strengths", []):
            if isinstance(item, dict):
                point = item.get("point", "")
                raw_quote = item.get("evidence_quote", "")
                verified, display_quote = validate_evidence_quote(raw_quote, candidate_answer)
                strengths.append(EvidencePoint(
                    point=point,
                    evidence_quote=display_quote,
                    is_verified=verified
                ))

        # 6. Extract & Validate Weaknesses with Evidence
        weaknesses = []
        for item in raw_data.get("weaknesses", []):
            if isinstance(item, dict):
                point = item.get("point", "")
                raw_quote = item.get("evidence_quote", "")
                suggestion = item.get("suggestion", "")
                verified, display_quote = validate_evidence_quote(raw_quote, candidate_answer)
                weaknesses.append(EvidencePoint(
                    point=point,
                    evidence_quote=display_quote,
                    is_verified=verified,
                    suggestion=suggestion
                ))

        actionable_tips = raw_data.get("actionable_tips", [])
        if not isinstance(actionable_tips, list):
            actionable_tips = [str(actionable_tips)]

        model_answer = raw_data.get("model_answer", "")

        # 7. Assemble Complete Result
        result = EvaluationResult(
            question_id=question_id,
            session_id=session_id,
            scores=scores,
            strengths=strengths,
            weaknesses=weaknesses,
            actionable_tips=actionable_tips,
            model_answer=model_answer,
            is_valid=True
        )

        # 8. Persist to SQLite
        try:
            save_evaluation(result, self.db_path)
        except Exception as e:
            logger.warning(f"Could not persist evaluation to SQLite: {e}")

        return result
