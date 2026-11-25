
"""
SQLite Database Storage Layer for HR Interview Simulator.
Supports authenticated users and isolated interview history.
"""

import sqlite3
import json
from contextlib import contextmanager
from typing import List, Optional, Dict, Any, Generator
from pathlib import Path
from datetime import datetime

from src.config import DATABASE_PATH
from src.models.interview import (
    InterviewSession,
    InterviewQuestion,
    TokenUsageRecord,
)
from src.models.evaluation import (
    EvaluationResult,
    DimensionScores,
    EvidencePoint,
)


@contextmanager
def get_db(db_path: Path = DATABASE_PATH) -> Generator[sqlite3.Connection, None, None]:
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
    """Create tables and safely migrate existing databases."""

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

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
                resume_summary TEXT,
                user_id INTEGER REFERENCES users(id)
            );
        """)

        session_columns = {
            row["name"]
            for row in cursor.execute(
                "PRAGMA table_info(sessions)"
            ).fetchall()
        }

        if "user_id" not in session_columns:
            cursor.execute("""
                ALTER TABLE sessions
                ADD COLUMN user_id INTEGER REFERENCES users(id);
            """)

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
                FOREIGN KEY (session_id)
                    REFERENCES sessions(session_id) ON DELETE CASCADE
            );
        """)

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
                FOREIGN KEY (question_id)
                    REFERENCES questions(id) ON DELETE CASCADE,
                FOREIGN KEY (session_id)
                    REFERENCES sessions(session_id) ON DELETE CASCADE
            );
        """)

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
                FOREIGN KEY (session_id)
                    REFERENCES sessions(session_id) ON DELETE SET NULL
            );
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id
            ON sessions(user_id);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_questions_session_id
            ON questions(session_id);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_evaluations_session_id
            ON evaluations(session_id);
        """)


def _require_user(user_id: Optional[int]) -> int:
    if user_id is None:
        raise ValueError("A logged-in user is required.")
    return int(user_id)


def _verify_session_owner(
    conn: sqlite3.Connection,
    session_id: str,
    user_id: int,
) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM sessions
        WHERE session_id = ? AND user_id = ?
        """,
        (session_id, user_id),
    ).fetchone()

    return row is not None


def save_session(
    session: InterviewSession,
    db_path: Path = DATABASE_PATH,
    user_id: Optional[int] = None,
) -> None:
    """Create a session belonging to the authenticated user."""

    owner_id = _require_user(user_id)
    session.user_id = owner_id

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        user_exists = cursor.execute(
            "SELECT 1 FROM users WHERE id = ?",
            (owner_id,),
        ).fetchone()

        if not user_exists:
            raise ValueError("The authenticated user does not exist.")

        cursor.execute("""
            INSERT INTO sessions (
                session_id, role, experience_level, difficulty,
                total_questions, status, created_at, completed_at,
                resume_summary, user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.session_id,
            session.role,
            session.experience_level,
            session.difficulty,
            session.total_questions,
            session.status,
            session.created_at,
            session.completed_at,
            session.resume_summary,
            owner_id,
        ))


def update_session_status(
    session_id: str,
    status: str,
    db_path: Path = DATABASE_PATH,
    user_id: Optional[int] = None,
) -> None:
    owner_id = _require_user(user_id)
    completed_at = (
        datetime.now().isoformat()
        if status == "completed"
        else None
    )

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions
            SET status = ?,
                completed_at = COALESCE(?, completed_at)
            WHERE session_id = ? AND user_id = ?
        """, (
            status,
            completed_at,
            session_id,
            owner_id,
        ))

        if cursor.rowcount == 0:
            raise ValueError("Session not found or access denied.")


def save_question(
    session_id: str,
    question: InterviewQuestion,
    db_path: Path = DATABASE_PATH,
    user_id: Optional[int] = None,
) -> None:
    owner_id = _require_user(user_id)

    with get_db(db_path) as conn:
        if not _verify_session_owner(conn, session_id, owner_id):
            raise ValueError("Session not found or access denied.")

        conn.execute("""
            INSERT INTO questions (
                id, session_id, question_index, category,
                question_text, is_follow_up, parent_question_id,
                target_competency, user_answer, answered_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                question_index = excluded.question_index,
                category = excluded.category,
                question_text = excluded.question_text,
                is_follow_up = excluded.is_follow_up,
                parent_question_id = excluded.parent_question_id,
                target_competency = excluded.target_competency
        """, (
            question.id,
            session_id,
            question.question_index,
            question.category,
            question.question_text,
            int(question.is_follow_up),
            question.parent_question_id,
            question.target_competency,
            question.user_answer,
            question.answered_at,
        ))


def update_question_answer(
    question_id: str,
    user_answer: str,
    db_path: Path = DATABASE_PATH,
    user_id: Optional[int] = None,
) -> None:
    owner_id = _require_user(user_id)

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE questions
            SET user_answer = ?, answered_at = ?
            WHERE id = ?
            AND session_id IN (
                SELECT session_id FROM sessions WHERE user_id = ?
            )
        """, (
            user_answer,
            datetime.now().isoformat(),
            question_id,
            owner_id,
        ))

        if cursor.rowcount == 0:
            raise ValueError("Question not found or access denied.")


def save_evaluation(
    eval_res: EvaluationResult,
    db_path: Path = DATABASE_PATH,
    user_id: Optional[int] = None,
) -> None:
    owner_id = _require_user(user_id)

    strengths_json = json.dumps([
        item.to_dict() for item in eval_res.strengths
    ])
    weaknesses_json = json.dumps([
        item.to_dict() for item in eval_res.weaknesses
    ])
    tips_json = json.dumps(eval_res.actionable_tips)

    with get_db(db_path) as conn:
        if not _verify_session_owner(
            conn, eval_res.session_id, owner_id
        ):
            raise ValueError("Session not found or access denied.")

        question_exists = conn.execute("""
            SELECT 1 FROM questions
            WHERE id = ? AND session_id = ?
        """, (
            eval_res.question_id,
            eval_res.session_id,
        )).fetchone()

        if not question_exists:
            raise ValueError("Evaluation question does not belong to this session.")

        conn.execute("""
            INSERT INTO evaluations (
                id, question_id, session_id,
                relevance_score, technical_score,
                communication_score, structure_score,
                overall_score, strengths_json, weaknesses_json,
                actionable_tips_json, model_answer,
                is_valid, error_message, evaluated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                question_id = excluded.question_id,
                session_id = excluded.session_id,
                relevance_score = excluded.relevance_score,
                technical_score = excluded.technical_score,
                communication_score = excluded.communication_score,
                structure_score = excluded.structure_score,
                overall_score = excluded.overall_score,
                strengths_json = excluded.strengths_json,
                weaknesses_json = excluded.weaknesses_json,
                actionable_tips_json = excluded.actionable_tips_json,
                model_answer = excluded.model_answer,
                is_valid = excluded.is_valid,
                error_message = excluded.error_message,
                evaluated_at = excluded.evaluated_at
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
            int(eval_res.is_valid),
            eval_res.error_message,
            eval_res.evaluated_at,
        ))


def _evaluation_from_row(row: sqlite3.Row) -> EvaluationResult:
    try:
        strengths = [
            EvidencePoint(**item)
            for item in json.loads(row["strengths_json"] or "[]")
        ]
    except (ValueError, TypeError, KeyError):
        strengths = []

    try:
        weaknesses = [
            EvidencePoint(**item)
            for item in json.loads(row["weaknesses_json"] or "[]")
        ]
    except (ValueError, TypeError, KeyError):
        weaknesses = []

    try:
        tips = json.loads(row["actionable_tips_json"] or "[]")
    except (ValueError, TypeError):
        tips = []

    scores = DimensionScores(
        relevance=row["relevance_score"],
        technical=row["technical_score"],
        communication=row["communication_score"],
        structure=row["structure_score"],
        overall=row["overall_score"],
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
        evaluated_at=row["evaluated_at"],
    )


def get_evaluation_for_question(
    question_id: str,
    db_path: Path = DATABASE_PATH,
    user_id: Optional[int] = None,
) -> Optional[EvaluationResult]:
    owner_id = _require_user(user_id)

    with get_db(db_path) as conn:
        row = conn.execute("""
            SELECT e.*
            FROM evaluations e
            JOIN sessions s ON s.session_id = e.session_id
            WHERE e.question_id = ? AND s.user_id = ?
        """, (
            question_id,
            owner_id,
        )).fetchone()

    return _evaluation_from_row(row) if row else None


def get_session_evaluations(
    session_id: str,
    db_path: Path = DATABASE_PATH,
    user_id: Optional[int] = None,
) -> List[EvaluationResult]:
    owner_id = _require_user(user_id)

    with get_db(db_path) as conn:
        rows = conn.execute("""
            SELECT e.*
            FROM evaluations e
            JOIN sessions s ON s.session_id = e.session_id
            WHERE e.session_id = ? AND s.user_id = ?
            ORDER BY e.evaluated_at
        """, (
            session_id,
            owner_id,
        )).fetchall()

    return [_evaluation_from_row(row) for row in rows]


def get_session_score_summary(
    session_id: str,
    db_path: Path = DATABASE_PATH,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    owner_id = _require_user(user_id)

    empty = {
        "valid_eval_count": 0,
        "avg_relevance": 0.0,
        "avg_technical": 0.0,
        "avg_communication": 0.0,
        "avg_structure": 0.0,
        "avg_overall": 0.0,
    }

    with get_db(db_path) as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) AS valid_eval_count,
                AVG(e.relevance_score) AS avg_relevance,
                AVG(e.technical_score) AS avg_technical,
                AVG(e.communication_score) AS avg_communication,
                AVG(e.structure_score) AS avg_structure,
                AVG(e.overall_score) AS avg_overall
            FROM evaluations e
            JOIN sessions s ON s.session_id = e.session_id
            WHERE e.session_id = ?
            AND s.user_id = ?
            AND e.is_valid = 1
        """, (
            session_id,
            owner_id,
        )).fetchone()

    if not row or row["valid_eval_count"] == 0:
        return empty

    return {
        "valid_eval_count": row["valid_eval_count"],
        "avg_relevance": round(row["avg_relevance"] or 0.0, 1),
        "avg_technical": round(row["avg_technical"] or 0.0, 1),
        "avg_communication": round(row["avg_communication"] or 0.0, 1),
        "avg_structure": round(row["avg_structure"] or 0.0, 1),
        "avg_overall": round(row["avg_overall"] or 0.0, 1),
    }


def log_token_usage(
    session_id: Optional[str],
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: float,
    db_path: Path = DATABASE_PATH,
) -> None:
    with get_db(db_path) as conn:
        if session_id is not None:
            exists = conn.execute(
                "SELECT 1 FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if not exists:
                raise ValueError("Cannot log tokens for an unknown session.")

        conn.execute("""
            INSERT INTO token_usage (
                session_id, model_name, prompt_tokens,
                completion_tokens, total_tokens,
                estimated_cost, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            model_name,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            estimated_cost,
            datetime.now().isoformat(),
        ))


def get_session(
    session_id: str,
    db_path: Path = DATABASE_PATH,
    user_id: Optional[int] = None,
) -> Optional[InterviewSession]:
    owner_id = _require_user(user_id)

    with get_db(db_path) as conn:
        row = conn.execute("""
            SELECT * FROM sessions
            WHERE session_id = ? AND user_id = ?
        """, (
            session_id,
            owner_id,
        )).fetchone()

        if not row:
            return None

        question_rows = conn.execute("""
            SELECT * FROM questions
            WHERE session_id = ?
            ORDER BY question_index ASC
        """, (session_id,)).fetchall()

    questions = [
        InterviewQuestion(
            id=q["id"],
            question_index=q["question_index"],
            category=q["category"],
            question_text=q["question_text"],
            is_follow_up=bool(q["is_follow_up"]),
            parent_question_id=q["parent_question_id"],
            target_competency=q["target_competency"],
            user_answer=q["user_answer"],
            answered_at=q["answered_at"],
        )
        for q in question_rows
    ]

    return InterviewSession(
        session_id=row["session_id"],
        user_id=row["user_id"],
        role=row["role"],
        experience_level=row["experience_level"],
        difficulty=row["difficulty"],
        total_questions=row["total_questions"],
        current_question_index=len(questions),
        status=row["status"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        resume_summary=row["resume_summary"],
        questions=questions,
    )


def get_all_sessions(
    limit: int = 50,
    db_path: Path = DATABASE_PATH,
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    owner_id = _require_user(user_id)

    with get_db(db_path) as conn:
        rows = conn.execute("""
            SELECT s.*, COUNT(q.id) AS questions_count
            FROM sessions s
            LEFT JOIN questions q ON s.session_id = q.session_id
            WHERE s.user_id = ?
            GROUP BY s.session_id
            ORDER BY s.created_at DESC
            LIMIT ?
        """, (
            owner_id,
            limit,
        )).fetchall()

    return [dict(row) for row in rows]


def get_token_analytics(
    db_path: Path = DATABASE_PATH,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    owner_id = _require_user(user_id)

    with get_db(db_path) as conn:
        row = conn.execute("""
            SELECT
                COUNT(t.id) AS total_calls,
                COALESCE(SUM(t.prompt_tokens), 0) AS total_prompt_tokens,
                COALESCE(SUM(t.completion_tokens), 0) AS total_completion_tokens,
                COALESCE(SUM(t.total_tokens), 0) AS grand_total_tokens,
                COALESCE(SUM(t.estimated_cost), 0.0) AS grand_total_cost
            FROM token_usage t
            JOIN sessions s ON s.session_id = t.session_id
            WHERE s.user_id = ?
        """, (owner_id,)).fetchone()

    return dict(row) if row else {
        "total_calls": 0,
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "grand_total_tokens": 0,
        "grand_total_cost": 0.0,
    }
