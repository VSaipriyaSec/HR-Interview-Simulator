"""
SQLite Database Storage Layer for HR Interview Simulator.
Handles persistent storage for sessions, questions, answers, evaluations,
and token usage analytics with proper connection lifecycle management.
"""

import sqlite3
import json
from contextlib import contextmanager
from typing import List, Optional, Dict, Any, Generator
from pathlib import Path
from datetime import datetime

from src.config import DATABASE_PATH
from src.models.interview import InterviewSession, InterviewQuestion, TokenUsageRecord
from src.models.evaluation import EvaluationResult, DimensionScores, EvidencePoint


@contextmanager
def get_db(db_path: Path = DATABASE_PATH) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager that yields an active SQLite connection
    and guarantees commit and close upon exit.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path = DATABASE_PATH) -> None:
    """Initializes the database schema if tables do not already exist."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Sessions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                experience_level TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                resume_summary TEXT
            );
        """)

        # Questions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                question_index INTEGER NOT NULL,
                category TEXT NOT NULL,
                question_text TEXT NOT NULL,
                is_follow_up INTEGER DEFAULT 0,
                parent_question_id TEXT,
                target_competency TEXT,
                user_answer TEXT,
                answered_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );
        """)

        # Evaluations Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id TEXT PRIMARY KEY,
                question_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                relevance_score REAL,
                technical_score REAL,
                communication_score REAL,
                structure_score REAL,
                overall_score REAL,
                strengths_json TEXT,
                weaknesses_json TEXT,
                actionable_tips_json TEXT,
                model_answer TEXT,
                is_valid INTEGER DEFAULT 1,
                error_message TEXT,
                evaluated_at TEXT NOT NULL,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );
        """)

        # Token Usage Observability Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                model_name TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                estimated_cost REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE SET NULL
            );
        """)


def save_session(session: InterviewSession, db_path: Path = DATABASE_PATH) -> None:
    """Inserts or replaces an interview session record."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (
                session_id, role, experience_level, difficulty,
                total_questions, status, created_at, completed_at, resume_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            session.session_id,
            session.role,
            session.experience_level,
            session.difficulty,
            session.total_questions,
            session.status,
            session.created_at,
            session.completed_at,
            session.resume_summary
        ))


def update_session_status(session_id: str, status: str, db_path: Path = DATABASE_PATH) -> None:
    """Updates session completion status and timestamp."""
    completed_at = datetime.now().isoformat() if status == "completed" else None
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions
            SET status = ?, completed_at = COALESCE(?, completed_at)
            WHERE session_id = ?;
        """, (status, completed_at, session_id))


def save_question(session_id: str, question: InterviewQuestion, db_path: Path = DATABASE_PATH) -> None:
    """Inserts or updates a question in the database."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO questions (
                id, session_id, question_index, category, question_text,
                is_follow_up, parent_question_id, target_competency,
                user_answer, answered_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            question.id,
            session_id,
            question.question_index,
            question.category,
            question.question_text,
            1 if question.is_follow_up else 0,
            question.parent_question_id,
            question.target_competency,
            question.user_answer,
            question.answered_at
        ))


def update_question_answer(question_id: str, user_answer: str, db_path: Path = DATABASE_PATH) -> None:
    """Records the candidate's answer and submission timestamp."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE questions
            SET user_answer = ?, answered_at = ?
            WHERE id = ?;
        """, (user_answer, datetime.now().isoformat(), question_id))


def save_evaluation(eval_res: EvaluationResult, db_path: Path = DATABASE_PATH) -> None:
    """Inserts or updates an evaluation record."""
    strengths_json = json.dumps([sp.to_dict() for sp in eval_res.strengths])
    weaknesses_json = json.dumps([wp.to_dict() for wp in eval_res.weaknesses])
    tips_json = json.dumps(eval_res.actionable_tips)

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO evaluations (
                id, question_id, session_id,
                relevance_score, technical_score, communication_score, structure_score,
                overall_score, strengths_json, weaknesses_json, actionable_tips_json,
                model_answer, is_valid, error_message, evaluated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            eval_res.id,
            eval_res.question_id,
            eval_res.session_id,
            eval_res.scores.relevance,
            eval_res.scores.technical,
            eval_res.scores.communication,
            eval_res.scores.structure,
            eval_res.scores.overall,
            strengths_json,
            weaknesses_json,
            tips_json,
            eval_res.model_answer,
            1 if eval_res.is_valid else 0,
            eval_res.error_message,
            eval_res.evaluated_at
        ))


def get_evaluation_for_question(question_id: str, db_path: Path = DATABASE_PATH) -> Optional[EvaluationResult]:
    """Retrieves the evaluation for a specific question."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evaluations WHERE question_id = ?;", (question_id,))
        row = cursor.fetchone()
        if not row:
            return None

        # Parse strengths & weaknesses
        try:
            raw_s = json.loads(row["strengths_json"]) if row["strengths_json"] else []
            strengths = [EvidencePoint(**item) for item in raw_s]
        except Exception:
            strengths = []

        try:
            raw_w = json.loads(row["weaknesses_json"]) if row["weaknesses_json"] else []
            weaknesses = [EvidencePoint(**item) for item in raw_w]
        except Exception:
            weaknesses = []

        try:
            tips = json.loads(row["actionable_tips_json"]) if row["actionable_tips_json"] else []
        except Exception:
            tips = []

        scores = DimensionScores(
            relevance=row["relevance_score"],
            technical=row["technical_score"],
            communication=row["communication_score"],
            structure=row["structure_score"],
            overall=row["overall_score"]
        )

        return EvaluationResult(
            id=row["id"],
            question_id=row["question_id"],
            session_id=row["session_id"],
            scores=scores,
            strengths=strengths,
            weaknesses=weaknesses,
            actionable_tips=tips,
            model_answer=row["model_answer"] or "",
            is_valid=bool(row["is_valid"]),
            error_message=row["error_message"],
            evaluated_at=row["evaluated_at"]
        )


def get_session_evaluations(session_id: str, db_path: Path = DATABASE_PATH) -> List[EvaluationResult]:
    """Retrieves all evaluations recorded for a session."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT question_id FROM evaluations WHERE session_id = ?;", (session_id,))
        rows = cursor.fetchall()

    evaluations = []
    for r in rows:
        ev = get_evaluation_for_question(r["question_id"], db_path)
        if ev:
            evaluations.append(ev)
    return evaluations


def get_session_score_summary(session_id: str, db_path: Path = DATABASE_PATH) -> Dict[str, Any]:
    """
    Computes average performance metrics across all valid evaluations in a session.
    """
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as valid_eval_count,
                AVG(relevance_score) as avg_relevance,
                AVG(technical_score) as avg_technical,
                AVG(communication_score) as avg_communication,
                AVG(structure_score) as avg_structure,
                AVG(overall_score) as avg_overall
            FROM evaluations
            WHERE session_id = ? AND is_valid = 1;
        """, (session_id,))
        row = cursor.fetchone()

        if not row or row["valid_eval_count"] == 0:
            return {
                "valid_eval_count": 0,
                "avg_relevance": 0.0,
                "avg_technical": 0.0,
                "avg_communication": 0.0,
                "avg_structure": 0.0,
                "avg_overall": 0.0
            }

        return {
            "valid_eval_count": row["valid_eval_count"],
            "avg_relevance": round(row["avg_relevance"] or 0.0, 1),
            "avg_technical": round(row["avg_technical"] or 0.0, 1),
            "avg_communication": round(row["avg_communication"] or 0.0, 1),
            "avg_structure": round(row["avg_structure"] or 0.0, 1),
            "avg_overall": round(row["avg_overall"] or 0.0, 1)
        }


def log_token_usage(
    session_id: Optional[str],
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: float,
    db_path: Path = DATABASE_PATH
) -> None:
    """Records token consumption and cost for a network call."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO token_usage (
                session_id, model_name, prompt_tokens, completion_tokens,
                total_tokens, estimated_cost, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            session_id,
            model_name,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            estimated_cost,
            datetime.now().isoformat()
        ))


def get_session(session_id: str, db_path: Path = DATABASE_PATH) -> Optional[InterviewSession]:
    """Retrieves a full session with its questions from the database."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?;", (session_id,))
        row = cursor.fetchone()
        if not row:
            return None

        # Load questions
        cursor.execute("SELECT * FROM questions WHERE session_id = ? ORDER BY question_index ASC;", (session_id,))
        question_rows = cursor.fetchall()

        questions = []
        for q in question_rows:
            questions.append(InterviewQuestion(
                id=q["id"],
                question_index=q["question_index"],
                category=q["category"],
                question_text=q["question_text"],
                is_follow_up=bool(q["is_follow_up"]),
                parent_question_id=q["parent_question_id"],
                target_competency=q["target_competency"],
                user_answer=q["user_answer"],
                answered_at=q["answered_at"]
            ))

        return InterviewSession(
            session_id=row["session_id"],
            role=row["role"],
            experience_level=row["experience_level"],
            difficulty=row["difficulty"],
            total_questions=row["total_questions"],
            current_question_index=len(questions),
            status=row["status"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            resume_summary=row["resume_summary"],
            questions=questions
        )


def get_all_sessions(limit: int = 50, db_path: Path = DATABASE_PATH) -> List[Dict[str, Any]]:
    """Retrieves recent session summaries for the history dashboard."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, COUNT(q.id) as questions_count
            FROM sessions s
            LEFT JOIN questions q ON s.session_id = q.session_id
            GROUP BY s.session_id
            ORDER BY s.created_at DESC
            LIMIT ?;
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_token_analytics(db_path: Path = DATABASE_PATH) -> Dict[str, Any]:
    """Aggregates total tokens used and total spend across all sessions."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total_calls,
                COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
                COALESCE(SUM(total_tokens), 0) as grand_total_tokens,
                COALESCE(SUM(estimated_cost), 0.0) as grand_total_cost
            FROM token_usage;
        """)
        row = cursor.fetchone()
        return dict(row) if row else {
            "total_calls": 0, "total_prompt_tokens": 0,
            "total_completion_tokens": 0, "grand_total_tokens": 0, "grand_total_cost": 0.0
        }
