"""
OpenRouter API Client Service.
Provides robust HTTP communication, retry logic, timeout enforcement,
structured JSON response validation, and token usage/cost tracking.
"""

import time
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests

from src.config import DEFAULT_MODEL, DEFAULT_TIMEOUT_SECONDS, DATABASE_PATH
from src.storage.db import log_token_usage

logger = logging.getLogger(__name__)


class OpenRouterAPIError(Exception):
    """Base exception for OpenRouter API interactions."""
    pass


class AuthenticationError(OpenRouterAPIError):
    """Raised when the API key is missing or invalid (HTTP 401)."""
    pass


class RateLimitError(OpenRouterAPIError):
    """Raised when request rate limit or token quota is exceeded (HTTP 429)."""
    pass


class APIConnectionError(OpenRouterAPIError):
    """Raised on connection timeout or network unreachability."""
    pass


class InvalidResponseError(OpenRouterAPIError):
    """Raised when the API returns an unexpected or malformed payload."""
    pass


class OpenRouterClient:
    """Client for querying models via the OpenRouter API."""

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = 2,
        db_path: Path = DATABASE_PATH
    ):
        if not api_key or not api_key.strip():
            raise AuthenticationError("OpenRouter API key is missing. Please configure secrets.toml.")

        self.api_key = api_key.strip()
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.db_path = db_path

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/VSaipriyaSec/HR-Interview-Simulator",
            "X-Title": "HR Interview Simulator AI"
        }

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        require_json: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 800
    ) -> Dict[str, Any]:
        """
        Sends a chat completion request with retry handling and token tracking.
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if require_json:
            payload["response_format"] = {"type": "json_object"}

        last_exception = None

        for attempt in range(1, self.max_retries + 2):
            try:
                response = requests.post(
                    url=self.API_URL,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout
                )

                # HTTP Status handling
                if response.status_code == 401:
                    raise AuthenticationError("Invalid OpenRouter API Key. HTTP 401 Unauthorized.")
                elif response.status_code == 429:
                    if attempt <= self.max_retries:
                        time.sleep(2 * attempt)
                        continue
                    raise RateLimitError("OpenRouter rate limit or credit quota exceeded. HTTP 429.")
                elif response.status_code >= 500:
                    if attempt <= self.max_retries:
                        time.sleep(2 * attempt)
                        continue
                    raise APIConnectionError(f"OpenRouter server error (HTTP {response.status_code}).")

                response.raise_for_status()
                data = response.json()

                if "choices" not in data or not data["choices"]:
                    raise InvalidResponseError("Malformed API response: 'choices' field missing or empty.")

                raw_content = data["choices"][0]["message"]["content"]

                # Extract Usage and Cost
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
                cost = usage.get("cost", 0.0)

                # Persist token analytics to SQLite
                log_token_usage(
                    session_id=session_id,
                    model_name=self.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=cost,
                    db_path=self.db_path
                )

                # Parse JSON if required
                if require_json:
                    parsed_content = self._defensive_json_parse(raw_content)
                    return {
                        "content": parsed_content,
                        "raw_json": True,
                        "usage": usage,
                        "raw_text": raw_content
                    }

                return {
                    "content": raw_content,
                    "raw_json": False,
                    "usage": usage,
                    "raw_text": raw_content
                }

            except requests.exceptions.Timeout as e:
                last_exception = APIConnectionError(f"Request timed out after {self.timeout}s.")
                if attempt <= self.max_retries:
                    time.sleep(1.5 * attempt)
                    continue
            except requests.exceptions.RequestException as e:
                last_exception = APIConnectionError(f"Network error: {str(e)}")
                if attempt <= self.max_retries:
                    time.sleep(1.5 * attempt)
                    continue
            except (KeyError, json.JSONDecodeError) as e:
                raise InvalidResponseError(f"Failed to parse OpenRouter response: {str(e)}")

        if last_exception:
            raise last_exception
        raise APIConnectionError("Failed to reach OpenRouter API after maximum retries.")

    @staticmethod
    def _defensive_json_parse(text: str) -> Dict[str, Any]:
        """
        Robustly parses JSON even if wrapped with markdown ticks or whitespace.
        Example: ```json { ... } ``` -> { ... }
        """
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json"):].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as err:
            logger.warning("Direct JSON decode failed, attempting fallback regex extract.")
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                substring = cleaned[start:end + 1]
                try:
                    return json.loads(substring)
                except json.JSONDecodeError:
                    pass
            raise InvalidResponseError(f"Model response could not be parsed as valid JSON: {cleaned[:100]}... Error: {str(err)}")
