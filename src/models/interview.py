
"""
Interview Domain Data Models.
Uses Python dataclasses for type safety, validation, and serialization.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


@dataclass
class TokenUsageRecord:
    """Tracks token consumption and API costs for observability."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InterviewQuestion:
    """Represents an interview question generated for the candidate."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question_index: int = 1
    category: str = "HR & Background"
    question_text: str = ""
    is_follow_up: bool = False
    parent_question_id: Optional[str] = None
    target_competency: str = "General"
    user_answer: Optional[str] = None
    answered_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InterviewSession:
    """Represents a complete interview session with settings and progress."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[int] = None
    role: str = "Software Engineer"
    experience_level: str = "Fresher / Entry Level (0 - 1 years)"
    difficulty: str = "Medium"
    total_questions: int = 5
    current_question_index: int = 0
    status: str = "in_progress"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    resume_summary: Optional[str] = None
    questions: List[InterviewQuestion] = field(default_factory=list)
    total_tokens: TokenUsageRecord = field(default_factory=TokenUsageRecord)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_finished(self) -> bool:
        """Checks if all planned questions have been asked."""
        return len(self.questions) >= self.total_questions
