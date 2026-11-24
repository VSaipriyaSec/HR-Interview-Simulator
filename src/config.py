"""
Application Configuration and Constants.
Defines supported interview roles, experience levels, question categories,
difficulty levels, and API settings.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = BASE_DIR / "interview_history.db"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Supported Roles
ROLES = [
    "Software Engineer",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Data Analyst",
    "Machine Learning / AI Engineer",
    "Cloud / DevOps Engineer",
    "Human Resources (HR) Executive",
    "Product Manager"
]

# Experience Levels
EXPERIENCE_LEVELS = [
    "Fresher / Entry Level (0 - 1 years)",
    "Junior (1 - 3 years)",
    "Mid-Level (3 - 5 years)",
    "Senior (5+ years)"
]

# Interview Difficulties
DIFFICULTIES = [
    "Easy",
    "Medium",
    "Hard"
]

# Question Categories
QUESTION_CATEGORIES = [
    "HR & Background",
    "Technical & Domain",
    "Behavioral (STAR Method)"
]

# Default Question Count Options
QUESTION_COUNT_OPTIONS = [3, 5, 8, 10]

# API Defaults
DEFAULT_MODEL = "openrouter/auto"
DEFAULT_TIMEOUT_SECONDS = 30
MAX_RESUME_FILE_SIZE_MB = 2.0
ALLOWED_RESUME_EXTENSIONS = [".pdf", ".txt", ".md"]

# Token Budget Limits
DEFAULT_MAX_TOKENS = 800
DEFAULT_TEMPERATURE = 0.7

# Canonical Scoring Weights (Must sum to 1.00 for each category)
SCORING_WEIGHTS = {
    "Technical & Domain": {
        "relevance": 0.20,
        "technical": 0.40,
        "communication": 0.20,
        "structure": 0.20,
    },
    "Behavioral (STAR Method)": {
        "relevance": 0.20,
        "technical": 0.10,
        "communication": 0.30,
        "structure": 0.40,
    },
    "HR & Background": {
        "relevance": 0.30,
        "technical": 0.15,
        "communication": 0.30,
        "structure": 0.25,
    }
}
