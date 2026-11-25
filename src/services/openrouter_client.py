
"""
OpenRouter API Client.
Handles API requests, JSON validation, limited retries,
and token usage tracking.
"""

import json
import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

import requests

from src.config import DEFAULT_MODEL, DEFAULT_TIMEOUT_SECONDS, DATABASE_PATH
from src.storage.db import log_token_usage

logger = logging.getLogger(__name__)


class OpenRouterAPIError(Exception):
    pass


class AuthenticationError(OpenRouterAPIError):
    pass


class RateLimitError(OpenRouterAPIError):
    pass


class APIConnectionError(OpenRouterAPIError):
    pass


class InvalidResponseError(OpenRouterAPIError):
    pass


class OpenRouterClient:
    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = 1,
        db_path: Path = DATABASE_PATH
    ):
        if not api_key or not api_key.strip():
            raise AuthenticationError(
                "OpenRouter API key is missing. Configure secrets.toml."
            )

        self.api_key = api_key.strip()
        self.model = model
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.db_path = db_path

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": (
                "https://github.com/VSaipriyaSec/HR-Interview-Simulator"
            ),
            "X-Title": "HR Interview Simulator AI"
        }

    @staticmethod
    def _defensive_json_parse(text: str) -> Dict[str, Any]:
        """Parse JSON, including responses wrapped in markdown fences."""

        if not isinstance(text, str) or not text.strip():
            raise InvalidResponseError("AI returned an empty response.")

        cleaned = text.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")

            if start == -1 or end <= start:
                raise InvalidResponseError(
                    "AI response did not contain a valid JSON object."
                )

            try:
                parsed = json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError as err:
                raise InvalidResponseError(
                    "Model response could not be parsed as valid JSON."
                ) from err

        if not isinstance(parsed, dict):
            raise InvalidResponseError(
                "AI response must be a JSON object."
            )

        return parsed

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        require_json: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 800
    ) -> Dict[str, Any]:

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if require_json:
            payload["response_format"] = {"type": "json_object"}

        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    self.API_URL,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout
                )

                if response.status_code == 401:
                    raise AuthenticationError(
                        "Invalid OpenRouter API key (HTTP 401)."
                    )

                if response.status_code == 429:
                    raise RateLimitError(
                        "OpenRouter rate limit or quota exceeded (HTTP 429)."
                    )

                if response.status_code >= 500:
                    raise APIConnectionError(
                        f"OpenRouter server error (HTTP {response.status_code})."
                    )

                response.raise_for_status()
                data = response.json()

                choices = data.get("choices")
                if not choices:
                    raise InvalidResponseError(
                        "OpenRouter returned no response choices."
                    )

                message = choices[0].get("message", {})
                raw_content = message.get("content")

                # Some providers return content as a list of text blocks.
                if isinstance(raw_content, list):
                    raw_content = "".join(
                        block.get("text", "")
                        for block in raw_content
                        if isinstance(block, dict)
                    )

                if not isinstance(raw_content, str) or not raw_content.strip():
                    raise InvalidResponseError(
                        "AI returned empty or unsupported response content."
                    )

                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get(
                    "total_tokens",
                    prompt_tokens + completion_tokens
                )
                cost = usage.get("cost", 0.0)

                if require_json:
                    try:
                        parsed_content = self._defensive_json_parse(
                            raw_content
                        )
                    except InvalidResponseError as err:
                        last_error = err
                        logger.warning(
                            "Invalid JSON response on attempt %s.",
                            attempt + 1
                        )

                        if attempt < self.max_retries:
                            time.sleep(0.5)
                            continue

                        raise

                else:
                    parsed_content = raw_content

                try:
                    log_token_usage(
                        session_id=session_id,
                        model_name=self.model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        estimated_cost=cost,
                        db_path=self.db_path
                    )
                except Exception:
                    logger.warning(
                        "Token usage could not be saved.",
                        exc_info=True
                    )

                return {
                    "content": parsed_content,
                    "raw_json": require_json,
                    "usage": usage,
                    "raw_text": raw_content
                }

            except (
                AuthenticationError,
                RateLimitError,
                InvalidResponseError
            ):
                raise

            except requests.exceptions.Timeout as err:
                last_error = APIConnectionError(
                    f"Request timed out after {self.timeout} seconds."
                )
                logger.warning("OpenRouter request timed out.")

            except requests.exceptions.RequestException as err:
                last_error = APIConnectionError(
                    f"OpenRouter network error: {str(err)}"
                )
                logger.warning("OpenRouter network request failed.")

            except (KeyError, ValueError) as err:
                last_error = InvalidResponseError(
                    "OpenRouter returned an unexpected response structure."
                )
                logger.warning("Unexpected OpenRouter response: %s", err)

            except APIConnectionError as err:
                last_error = err

            if attempt < self.max_retries:
                time.sleep(0.5)

        if last_error:
            raise last_error

        raise APIConnectionError(
            "OpenRouter request failed."
        )
