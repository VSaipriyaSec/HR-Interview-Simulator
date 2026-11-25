"""
Comprehensive Test Suite for Stage 2.
Tests database persistence, resume parsing, privacy sanitization,
JSON parsing, prompt templates, and interview engine sequencing.
"""

import os
import sys
import gc
import sqlite3
import tempfile
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.interview import InterviewSession, InterviewQuestion, TokenUsageRecord
from src.storage.db import (
    init_db,
    save_session,
    save_question,
    update_question_answer,
    update_session_status,
    log_token_usage,
    get_session,
    get_all_sessions,
    get_token_analytics
)
from src.services.resume_parser import ResumeParser, ResumeValidationError
from src.services.openrouter_client import OpenRouterClient, InvalidResponseError
from src.core.prompt_templates import (
    build_question_generation_messages,
    build_follow_up_messages,
    get_interviewer_system_prompt
)
from src.core.interview_engine import InterviewEngine


class TestStage2Engine(unittest.TestCase):

    def setUp(self):
        """Create an isolated temporary database and test user."""

        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_history.db"

        init_db(self.db_path)

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                ("Test User", "stage2@example.com", "test_hash"),
            )
            self.user_id = cursor.lastrowid

    def tearDown(self):
        """Cleans up temporary test files with garbage collection."""
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            # On Windows, background lock might take milliseconds to release
            pass

    # 1. Models & Dataclasses Tests
    def test_interview_session_dataclass(self):
        session = InterviewSession(
            role="Software Engineer",
            experience_level="Fresher / Entry Level (0 - 1 years)",
            difficulty="Medium",
            total_questions=3,
        )
        self.assertEqual(session.role, "Software Engineer")
        self.assertEqual(session.status, "in_progress")
        self.assertFalse(session.is_finished)
        self.assertIn("session_id", session.to_dict())

    # 2. SQLite Database Persistence Tests
    def test_database_crud_operations(self):
        session = InterviewSession(
            session_id="test_sess_001",
            role="Backend Developer",
            experience_level="Junior (1 - 3 years)",
            difficulty="Hard",
            total_questions=2
        )
        save_session(session, self.db_path, user_id=self.user_id)

        # Retrieve and verify
        loaded = get_session("test_sess_001", self.db_path, user_id=self.user_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.role, "Backend Developer")
        self.assertEqual(loaded.total_questions, 2)

        # Add a question
        q1 = InterviewQuestion(
            id="q_001",
            question_index=1,
            category="Technical & Domain",
            question_text="Explain database connection pooling.",
            target_competency="Database Architecture"
        )
        save_question("test_sess_001", q1, self.db_path, user_id=self.user_id)

        # Record answer
        update_question_answer("q_001", "Connection pooling maintains active DB connections...", self.db_path, user_id=self.user_id)

        # Check session reload with question
        reloaded = get_session("test_sess_001", self.db_path, user_id=self.user_id)
        self.assertEqual(len(reloaded.questions), 1)
        self.assertEqual(reloaded.questions[0].user_answer, "Connection pooling maintains active DB connections...")

        # Update session status
        update_session_status("test_sess_001", "completed", self.db_path, user_id=self.user_id)
        completed_session = get_session("test_sess_001", self.db_path, user_id=self.user_id)
        self.assertEqual(completed_session.status, "completed")
        self.assertIsNotNone(completed_session.completed_at)

    def test_token_usage_logging_and_analytics(self):
        # First create session to satisfy FK constraint
        session = InterviewSession(
            session_id="test_sess_token",
            role="Data Analyst",
            experience_level="Fresher",
            difficulty="Easy",
            total_questions=1
        )
        save_session(session, self.db_path, user_id=self.user_id)

        log_token_usage(
            session_id="test_sess_token",
            model_name="openrouter/auto",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.00045,
            db_path=self.db_path
        )
        stats = get_token_analytics(self.db_path, user_id=self.user_id)
        self.assertEqual(stats["total_calls"], 1)
        self.assertEqual(stats["total_prompt_tokens"], 100)
        self.assertEqual(stats["total_completion_tokens"], 50)
        self.assertEqual(stats["grand_total_tokens"], 150)
        self.assertAlmostEqual(stats["grand_total_cost"], 0.00045)

    # 3. Resume Processing & Privacy Sanitization Tests
    def test_resume_parser_txt(self):
        sample_resume = (
            "John Doe\n"
            "Email: john.doe@example.com\n"
            "Phone: +1-555-123-4567\n"
            "Skills: Python, Streamlit, SQL, Git\n"
            "Projects: Built an HR Management System using Node.js and MySQL."
        )
        file_bytes = sample_resume.encode("utf-8")
        clean_text, preview = ResumeParser.process_resume("my_resume.txt", file_bytes)

        # Check PII redaction
        self.assertNotIn("john.doe@example.com", clean_text)
        self.assertIn("[EMAIL_REDACTED]", clean_text)
        self.assertNotIn("+1-555-123-4567", clean_text)
        self.assertIn("[PHONE_REDACTED]", clean_text)

        # Check valid skills preserved
        self.assertIn("Python", clean_text)
        self.assertIn("Node.js", clean_text)

    def test_resume_parser_size_limit_rejection(self):
        huge_bytes = b"X" * (3 * 1024 * 1024)  # 3 MB
        with self.assertRaises(ResumeValidationError):
            ResumeParser.validate_file("large_resume.txt", huge_bytes)

    def test_resume_parser_invalid_extension(self):
        with self.assertRaises(ResumeValidationError):
            ResumeParser.validate_file("resume.exe", b"binary content")

    # 4. OpenRouter JSON Parser Tests
    def test_defensive_json_parse(self):
        # Clean JSON
        res1 = OpenRouterClient._defensive_json_parse('{"question": "What is REST?", "score": 9}')
        self.assertEqual(res1["question"], "What is REST?")

        # Markdown wrapped JSON
        res2 = OpenRouterClient._defensive_json_parse('```json\n{"question": "Explain Star schema", "category": "Tech"}\n```')
        self.assertEqual(res2["question"], "Explain Star schema")

        # Invalid JSON
        with self.assertRaises(InvalidResponseError):
            OpenRouterClient._defensive_json_parse("This is plain text with no json")

    # 5. Prompt Generation Tests
    def test_prompt_builder_structure(self):
        messages = build_question_generation_messages(
            role="Data Analyst",
            experience_level="Fresher",
            difficulty="Easy",
            category="Technical & Domain",
            question_index=1,
            total_questions=5,
            previous_questions=[],
            resume_context="Skills: SQL, Pandas, Excel"
        )
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("Data Analyst", messages[1]["content"])
        self.assertIn("Skills: SQL, Pandas, Excel", messages[1]["content"])

    # 6. Interview Engine Offline Fallback & Sequencing
    def test_interview_engine_offline_sequencing(self):
        engine = InterviewEngine(client=None, db_path=self.db_path)
        session = engine.create_session(
            role="Software Engineer",
            experience_level="Fresher / Entry Level (0 - 1 years)",
            difficulty="Easy",
            total_questions=3,
            user_id=self.user_id,
        )
        # Q1 should be HR
        q1 = engine.generate_next_question(session)
        self.assertEqual(q1.question_index, 1)
        self.assertEqual(q1.category, "HR & Background")
        self.assertTrue(len(q1.question_text) > 5)

        # Answer Q1
        engine.record_answer(session, q1.id, "I love solving problems with software.")

        # Q2 should be Technical
        q2 = engine.generate_next_question(session)
        self.assertEqual(q2.question_index, 2)
        self.assertEqual(q2.category, "Technical & Domain")

        # Answer Q2
        engine.record_answer(session, q2.id, "REST uses standard HTTP methods.")

        # Q3 should be Behavioral
        q3 = engine.generate_next_question(session)
        self.assertEqual(q3.question_index, 3)
        self.assertEqual(q3.category, "Behavioral (STAR Method)")

        # Answer Q3
        engine.record_answer(session, q3.id, "In my team project I handled merge conflicts.")
        self.assertEqual(session.status, "completed")


if __name__ == "__main__":
    unittest.main()
