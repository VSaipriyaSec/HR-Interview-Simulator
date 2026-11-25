"""
Evaluation Domain Data Models.
Defines structured classes for 4-dimensional scores, evidence points,
and complete interview answer evaluations.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


@dataclass
class DimensionScores:
    """Stores the individual 4-dimension scores and calculated overall score."""
    relevance: Optional[float] = None
    technical: Optional[float] = None
    communication: Optional[float] = None
    structure: Optional[float] = None
    overall: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidencePoint:
    """Represents an evaluation observation tied to candidate text."""
    point: str = ""
    evidence_quote: str = ""
    is_verified: bool = False
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationResult:
    """Complete evaluation report for a candidate's answer."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question_id: str = ""
    session_id: str = ""
    scores: DimensionScores = field(default_factory=DimensionScores)
    strengths: List[EvidencePoint] = field(default_factory=list)
    weaknesses: List[EvidencePoint] = field(default_factory=list)
    actionable_tips: List[str] = field(default_factory=list)
    model_answer: str = ""
    is_valid: bool = True
    error_message: Optional[str] = None
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
