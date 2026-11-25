
"""
Comprehensive Automated Unit Tests for Stage 3: AI Evaluation & Feedback Engine.
Tests sequence-aware quote matching, invalid score flagging, canonical weights,
and SQLite persistence.
"""

import sys
import gc
import sqlite3
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.interview import InterviewSession, InterviewQuestion
from src.models.evaluation import DimensionScores, EvidencePoint, EvaluationResult
from src.core.evaluator import (
    validate_evidence_quote,
    parse_dimension_score,
    calculate_weighted_score,
    AnswerEvaluator,
)
from src.storage.db import (
    init_db,
    save_session,
    save_question,
    save_evaluation,
    get_evaluation_for_question,
    get_session_evaluations,
    get_session_score_summary,
)


class TestStage3EvaluationEngine(unittest.TestCase):

    def setUp(self):
        """Create an isolated temporary database and test user."""

        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_stage3.db"

        init_db(self.db_path)

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                ("Stage 3 Test User", "stage3@example.com", "test_hash"),
            )
            self.user_id = cursor.lastrowid

    def tearDown(self):
        """Release database connections and clean temporary files."""

        gc.collect()

        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    # 1. Evidence Quote Validation Tests

    def test_quote_verbatim_match(self):
        answer = "I implemented database indexing using B-Trees to optimize slow customer queries."
        quote = "database indexing using B-Trees to optimize"

        valid, display = validate_evidence_quote(quote, answer)

        self.assertTrue(valid)
        self.assertIn("database indexing", display)

    def test_quote_reordered_words_rejection(self):
        answer = "I used MySQL and Express to build the backend."
        quote = "backend the build to Express and MySQL used I"

        valid, display = validate_evidence_quote(quote, answer)

        self.assertFalse(valid)
        self.assertIn("AI Summary", display)

    def test_quote_repeated_words_rejection(self):
        answer = "I developed the application in Python."
        quote = "Python Python Python Python"

        valid, display = validate_evidence_quote(quote, answer)

        self.assertFalse(valid)
        self.assertIn("AI Summary", display)

    def test_quote_negation_rejection(self):
        answer = "I did not use MongoDB because our data was strictly relational."
        quote = "I did use MongoDB because our data"

        valid, display = validate_evidence_quote(quote, answer)

        self.assertFalse(valid)
        self.assertIn("AI Summary", display)

    def test_quote_fabricated_hallucination_rejection(self):
        answer = "I created automated unit tests using PyTest to ensure code quality."
        quote = "The candidate managed five junior developers and led daily standup meetings"

        valid, display = validate_evidence_quote(quote, answer)

        self.assertFalse(valid)
        self.assertIn("AI Summary", display)

    def test_quote_short_length_threshold(self):
        answer = "I used Java and Spring Boot for building REST APIs."

        valid1, _ = validate_evidence_quote("Java", answer)
        self.assertTrue(valid1)

        valid2, _ = validate_evidence_quote("Ruby Rails", answer)
        self.assertFalse(valid2)

    # 2. Score Parsing and Clamping Tests

    def test_parse_dimension_score_valid_values(self):
        self.assertEqual(parse_dimension_score(8), 8.0)
        self.assertEqual(parse_dimension_score(8.5), 8.5)
        self.assertEqual(parse_dimension_score("9.2"), 9.2)
        self.assertEqual(parse_dimension_score("7/10"), 7.0)
        self.assertEqual(parse_dimension_score("10.0/10"), 10.0)

    def test_parse_dimension_score_clamping(self):
        self.assertEqual(parse_dimension_score(13.5), 10.0)
        self.assertEqual(parse_dimension_score(-4.0), 0.0)

    def test_parse_dimension_score_invalid_returns_none(self):
        self.assertIsNone(parse_dimension_score("N/A"))
        self.assertIsNone(parse_dimension_score(None))
        self.assertIsNone(parse_dimension_score("invalid_text"))
        self.assertIsNone(parse_dimension_score(""))

    # 3. Canonical Weighted Score Calculations

    def test_canonical_weights_technical_domain(self):
        scores = DimensionScores(
            relevance=8.0,
            technical=9.0,
            communication=7.0,
            structure=6.0,
        )

        overall = calculate_weighted_score("Technical & Domain", scores)

        self.assertEqual(overall, 7.8)

    def test_canonical_weights_behavioral_star(self):
        scores = DimensionScores(
            relevance=8.0,
            technical=6.0,
            communication=9.0,
            structure=5.0,
        )

        overall = calculate_weighted_score(
            "Behavioral (STAR Method)", scores
        )

        self.assertEqual(overall, 6.9)

    def test_canonical_weights_hr_background(self):
        scores = DimensionScores(
            relevance=8.0,
            technical=7.0,
            communication=9.0,
            structure=8.0,
        )

        overall = calculate_weighted_score("HR & Background", scores)

        self.assertEqual(overall, 8.2)

    def test_weighted_score_with_missing_dimension_returns_none(self):
        scores = DimensionScores(
            relevance=8.0,
            technical=None,
            communication=7.0,
            structure=6.0,
        )

        self.assertIsNone(
            calculate_weighted_score("Technical & Domain", scores)
        )

    # 4. Input Guardrails Tests

    def test_evaluator_input_validation(self):
        evaluator = AnswerEvaluator(
            client=None,
            db_path=self.db_path,
        )

        valid, msg = evaluator.validate_input("")
        self.assertFalse(valid)
        self.assertIn("empty", msg.lower())

        valid2, msg2 = evaluator.validate_input("I like coding.")
        self.assertFalse(valid2)
        self.assertIn("too brief", msg2.lower())

        valid3, msg3 = evaluator.validate_input(
            "I solved database deadlocks using explicit row locking."
        )
        self.assertTrue(valid3)
        self.assertEqual(msg3, "")

    # 5. SQLite Persistence and Summary Aggregations

    def test_database_evaluation_crud_and_summary(self):

        session = InterviewSession(
            session_id="eval_sess_01",
            role="Software Engineer",
            experience_level="Fresher",
            difficulty="Medium",
            total_questions=2,
        )

        save_session(
            session,
            self.db_path,
            user_id=self.user_id,
        )

        q1 = InterviewQuestion(
            id="q_eval_01",
            question_index=1,
            category="Technical & Domain",
            question_text="Explain indexing in SQL.",
            user_answer="Indexing creates a B-Tree structure for faster lookups.",
        )

        save_question(
            "eval_sess_01",
            q1,
            self.db_path,
            user_id=self.user_id,
        )

        scores1 = DimensionScores(
            relevance=8.0,
            technical=8.0,
            communication=8.0,
            structure=8.0,
            overall=8.0,
        )

        strengths1 = [
            EvidencePoint(
                point="Clear B-Tree concept",
                evidence_quote='"creates a B-Tree structure"',
                is_verified=True,
            )
        ]

        weaknesses1 = [
            EvidencePoint(
                point="Didn't mention write penalty",
                evidence_quote="[AI Summary]",
                is_verified=False,
                suggestion="Explain write overhead",
            )
        ]

        eval_result1 = EvaluationResult(
            id="eval_res_01",
            question_id="q_eval_01",
            session_id="eval_sess_01",
            scores=scores1,
            strengths=strengths1,
            weaknesses=weaknesses1,
            actionable_tips=[
                "Discuss clustered vs non-clustered index"
            ],
            model_answer="A complete answer would discuss B-Trees...",
            is_valid=True,
        )

        save_evaluation(
            eval_result1,
            self.db_path,
            user_id=self.user_id,
        )

        loaded = get_evaluation_for_question(
            "q_eval_01",
            self.db_path,
            user_id=self.user_id,
        )

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.scores.overall, 8.0)
        self.assertEqual(loaded.scores.technical, 8.0)
        self.assertEqual(len(loaded.strengths), 1)
        self.assertTrue(loaded.strengths[0].is_verified)
        self.assertEqual(len(loaded.weaknesses), 1)
        self.assertFalse(loaded.weaknesses[0].is_verified)

        evaluations = get_session_evaluations(
            "eval_sess_01",
            self.db_path,
            user_id=self.user_id,
        )

        self.assertEqual(len(evaluations), 1)

        summary = get_session_score_summary(
            "eval_sess_01",
            self.db_path,
            user_id=self.user_id,
        )

        self.assertEqual(summary["valid_eval_count"], 1)
        self.assertEqual(summary["avg_overall"], 8.0)
        self.assertEqual(summary["avg_technical"], 8.0)


if __name__ == "__main__":
    unittest.main()
