"""
Secure Resume Processing Service.
Handles file validation, size limits, in-memory text extraction,
and privacy safeguards (PII scrubbing: phone, email, addresses).
"""

import re
import io
import logging
from typing import Tuple, Optional
from src.config import MAX_RESUME_FILE_SIZE_MB, ALLOWED_RESUME_EXTENSIONS

logger = logging.getLogger(__name__)

# Try importing pypdf safely
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


class ResumeValidationError(Exception):
    """Raised when uploaded resume fails size or format validation."""
    pass


class ResumeParser:
    """Service to safely parse and sanitize candidate resumes."""

    # Privacy Scrubbing Regexes
    EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
    URL_REGEX = re.compile(r"https?://\S+|www\.\S+")

    @classmethod
    def validate_file(cls, filename: str, file_bytes: bytes) -> None:
        """
        Validates file extension and size.
        Raises ResumeValidationError on violation.
        """
        # Check Extension
        dot_idx = filename.rfind(".")
        if dot_idx == -1:
            raise ResumeValidationError("File must have a valid extension (.pdf, .txt, .md).")

        ext = filename[dot_idx:].lower()
        if ext not in ALLOWED_RESUME_EXTENSIONS:
            allowed = ", ".join(ALLOWED_RESUME_EXTENSIONS)
            raise ResumeValidationError(f"Unsupported file type '{ext}'. Allowed types: {allowed}")

        # Check File Size
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > MAX_RESUME_FILE_SIZE_MB:
            raise ResumeValidationError(
                f"File size ({size_mb:.2f} MB) exceeds maximum allowed limit of {MAX_RESUME_FILE_SIZE_MB} MB."
            )

        if len(file_bytes.strip()) == 0:
            raise ResumeValidationError("Uploaded file is empty.")

    @classmethod
    def extract_text(cls, filename: str, file_bytes: bytes) -> str:
        """
        Extracts raw text from bytes in-memory.
        Supports PDF, TXT, and MD formats.
        """
        cls.validate_file(filename, file_bytes)
        ext = filename[filename.rfind("."):].lower()

        extracted_text = ""

        if ext in [".txt", ".md"]:
            try:
                extracted_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                extracted_text = file_bytes.decode("latin-1", errors="replace")

        elif ext == ".pdf":
            if not PYPDF_AVAILABLE:
                raise ResumeValidationError(
                    "PDF processing library ('pypdf') is not installed in the environment. "
                    "Please upload a .txt or .md resume, or install 'pypdf'."
                )
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                pages_text = []
                for i, page in enumerate(reader.pages):
                    page_content = page.extract_text()
                    if page_content:
                        pages_text.append(page_content)
                extracted_text = "\n".join(pages_text)
            except Exception as e:
                raise ResumeValidationError(f"Could not parse PDF content: {str(e)}")

        if not extracted_text.strip():
            raise ResumeValidationError("No readable text could be extracted from the resume.")

        return extracted_text

    @classmethod
    def sanitize_pii(cls, text: str) -> str:
        """
        Redacts sensitive Personally Identifiable Information (PII)
        such as email addresses, phone numbers, and direct URLs
        before passing text into LLM prompts.
        """
        # Redact emails
        sanitized = cls.EMAIL_REGEX.sub("[EMAIL_REDACTED]", text)
        # Redact phones
        sanitized = cls.PHONE_REGEX.sub("[PHONE_REDACTED]", sanitized)
        # Redact direct URLs
        sanitized = cls.URL_REGEX.sub("[URL_REDACTED]", sanitized)
        return sanitized

    @classmethod
    def process_resume(cls, filename: str, file_bytes: bytes, max_chars: int = 2500) -> Tuple[str, str]:
        """
        Full pipeline: Validate -> Extract -> Sanitize -> Truncate.
        Returns:
            Tuple of (sanitized_text, short_summary_preview)
        """
        raw_text = cls.extract_text(filename, file_bytes)
        clean_text = cls.sanitize_pii(raw_text)

        # Truncate to maximum characters to safeguard token budget
        truncated = clean_text[:max_chars].strip()

        # Generate a brief 2-line preview for UI presentation
        first_lines = [line.strip() for line in truncated.split("\n") if line.strip()][:3]
        preview = " | ".join(first_lines)[:180] + "..."

        return truncated, preview
