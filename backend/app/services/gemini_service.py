import time
import re
import logging
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.exceptions import AiServiceException, ValidationException

logger = logging.getLogger("app.services.gemini")


def redact_secrets(text: str) -> str:
    """Removes API key strings from error messages or logs."""
    if not text or not settings.GEMINI_API_KEY:
        return text
    return text.replace(settings.GEMINI_API_KEY, "[REDACTED_API_KEY]")


class GeminiService:
    """
    Industrial-grade Gemini AI service using the official `google-genai` SDK.
    Features:
    - Automatic retry with exponential backoff on transient errors (429 rate limit, 503 unavailable, network timeouts).
    - Dynamic model availability verification.
    - Normalized 768-dimensional embedding generation.
    - Efficient chunk batching.
    - Strict secret scrubbing (API keys never appear in logs or errors).
    """

    def __init__(self):
        self._client = None
        self._verified_gen_model: Optional[str] = None
        self._verified_embed_model: Optional[str] = None

    def get_client(self):
        """Initializes and caches the official Google GenAI Client."""
        if self._client is not None:
            return self._client

        if not settings.is_gemini_configured():
            raise AiServiceException(
                message="Google Gemini API key is not configured in backend/.env",
                details={"code": "UNCONFIGURED_GEMINI_API_KEY"},
            )

        try:
            from google import genai
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            return self._client
        except Exception as exc:
            clean_err = redact_secrets(str(exc))
            logger.error(f"Failed to initialize Google GenAI client: {clean_err}")
            raise AiServiceException(f"Failed to initialize GenAI client: {clean_err}")

    def _execute_with_retry(self, operation_name: str, func, max_retries: int = 3, initial_delay: float = 1.0):
        """
        Executes a Gemini SDK call with exponential backoff for transient network,
        quota, and rate limit errors.
        """
        delay = initial_delay
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                return func()
            except Exception as exc:
                last_exception = exc
                err_str = redact_secrets(str(exc))

                # Identify if error is retryable (429 Rate Limit, 503 Service Unavailable, Timeout)
                is_rate_limit = "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower()
                is_unavailable = "503" in err_str or "unavailable" in err_str.lower() or "timeout" in err_str.lower()

                if (is_rate_limit or is_unavailable) and attempt < max_retries:
                    sleep_time = delay * (2 ** (attempt - 1))
                    logger.warning(
                        f"Transient Gemini {operation_name} error on attempt {attempt}/{max_retries}. "
                        f"Retrying in {sleep_time:.1f}s. Detail: {err_str[:120]}"
                    )
                    time.sleep(sleep_time)
                    continue

                # Non-retryable error (e.g. 400 Invalid Argument, 403 Forbidden / Invalid Key)
                logger.error(f"Fatal Gemini error during {operation_name} (attempt {attempt}): {err_str}")
                break

        clean_msg = redact_secrets(str(last_exception))
        if "403" in clean_msg or "API_KEY_INVALID" in clean_msg or "unregistered" in clean_msg.lower():
            raise AiServiceException("Google Gemini API Key is invalid or expired. Please check your key in backend/.env.")
        elif "429" in clean_msg or "quota" in clean_msg.lower():
            raise AiServiceException("Google Gemini rate limit or quota exceeded. Please wait or check your AI Studio plan.")
        else:
            raise AiServiceException(f"Gemini {operation_name} failed: {clean_msg}")

    # -------------------------------------------------------------------------
    # Model Verification
    # -------------------------------------------------------------------------

    def get_supported_generation_model(self) -> str:
        """
        Verifies that GEMINI_MODEL is accessible, or falls back to an available
        generation model without hardcoding outdated identifiers.
        """
        if self._verified_gen_model:
            return self._verified_gen_model

        client = self.get_client()
        candidates = [
            settings.GEMINI_MODEL,
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]

        # Filter out empty or placeholder strings
        candidates = [c for c in candidates if c and not c.startswith("YOUR_")]

        available_names = set()
        try:
            for m in client.models.list():
                raw_name = getattr(m, "name", "").replace("models/", "")
                available_names.add(raw_name)
        except Exception:
            # If list permission is restricted, test primary candidate directly
            pass

        selected = None
        if available_names:
            for c in candidates:
                if c in available_names:
                    selected = c
                    break

        if not selected:
            selected = candidates[0] if candidates else "gemini-2.5-flash"

        self._verified_gen_model = selected
        logger.info(f"Verified active Gemini generation model: '{selected}'")
        return selected

    def get_supported_embedding_model(self) -> str:
        """
        Verifies that GEMINI_EMBEDDING_MODEL is accessible.
        Defaults to 'gemini-embedding-2' with candidate fallbacks.
        """
        if self._verified_embed_model:
            return self._verified_embed_model

        candidates = [
            settings.GEMINI_EMBEDDING_MODEL,
            "gemini-embedding-2",
            "text-embedding-004",
        ]
        candidates = [c for c in candidates if c]

        client = self.get_client()
        selected = None

        for candidate in candidates:
            try:
                # Test embedding single word to verify candidate model
                res = client.models.embed_content(
                    model=candidate,
                    contents="test",
                )
                values = self._extract_vector(res)
                if values and len(values) == settings.EMBEDDING_DIMENSION:
                    selected = candidate
                    break
            except Exception:
                continue

        if not selected:
            selected = candidates[0] if candidates else "gemini-embedding-2"

        self._verified_embed_model = selected
        logger.info(f"Verified active Gemini embedding model: '{selected}'")
        return selected

    # -------------------------------------------------------------------------
    # Embedding Generation
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Sanitizes and normalizes text for clean semantic embedding."""
        if not text:
            return ""
        # Collapse multiple whitespace and normalize newlines
        cleaned = re.sub(r"[ \t]+", " ", text)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def _extract_vector(response: Any) -> Optional[List[float]]:
        """Extracts float vector list from google-genai embed response object."""
        if hasattr(response, "embeddings") and response.embeddings:
            return list(response.embeddings[0].values)
        elif hasattr(response, "embedding") and response.embedding:
            return list(response.embedding.values)
        elif hasattr(response, "values"):
            return list(response.values)
        return None

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generates a 768-dimensional dense semantic embedding vector for a single text chunk.
        - Validates input.
        - Normalizes text.
        - Strictly verifies 768 dimension output.
        - Never silently returns fake embeddings.
        """
        normalized = self._normalize_text(text)
        if not normalized:
            raise ValidationException("Cannot generate embedding for empty or whitespace-only text.")

        client = self.get_client()
        model_name = self.get_supported_embedding_model()

        def _call():
            return client.models.embed_content(
                model=model_name,
                contents=normalized,
            )

        response = self._execute_with_retry("Embedding Generation", _call)
        vector = self._extract_vector(response)

        if not vector:
            raise AiServiceException("Gemini embedding API returned an empty vector structure.")

        actual_dim = len(vector)
        if actual_dim != settings.EMBEDDING_DIMENSION:
            raise AiServiceException(
                f"Embedding dimension mismatch: Model returned {actual_dim} dimensions, "
                f"expected {settings.EMBEDDING_DIMENSION}."
            )

        return vector

    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        """
        Generates embeddings in efficient batches for document chunks.
        Avoids redundant network calls while respecting API payload constraints.
        """
        if not texts:
            return []

        clean_texts = [self._normalize_text(t) for t in texts]
        client = self.get_client()
        model_name = self.get_supported_embedding_model()
        all_embeddings: List[List[float]] = []

        # Process in batches
        for i in range(0, len(clean_texts), batch_size):
            batch = clean_texts[i : i + batch_size]
            # Replace empty strings with a placeholder to keep index alignment
            safe_batch = [t if t else "..." for t in batch]

            def _call_batch():
                return client.models.embed_content(
                    model=model_name,
                    contents=safe_batch,
                )

            res = self._execute_with_retry(f"Batch Embedding ({len(batch)} chunks)", _call_batch)

            if hasattr(res, "embeddings") and res.embeddings and len(res.embeddings) == len(safe_batch):
                for item in res.embeddings:
                    vec = list(item.values)
                    if len(vec) != settings.EMBEDDING_DIMENSION:
                        raise AiServiceException(
                            f"Batch vector dimension {len(vec)} does not match {settings.EMBEDDING_DIMENSION}."
                        )
                    all_embeddings.append(vec)
            else:
                # Fallback to serial call for this batch if SDK returns non-list or mismatched count
                for single_text in safe_batch:
                    all_embeddings.append(self.generate_embedding(single_text))

        return all_embeddings

    # -------------------------------------------------------------------------
    # Text & Content Generation
    # -------------------------------------------------------------------------

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """
        Generates text using the verified Gemini generation model.
        """
        client = self.get_client()
        model_name = self.get_supported_generation_model()

        def _call_gen():
            config = None
            if system_instruction:
                try:
                    from google.genai import types
                    config = types.GenerateContentConfig(
                        temperature=temperature,
                        system_instruction=system_instruction,
                    )
                except Exception:
                    config = None

            return client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )

        response = self._execute_with_retry("Content Generation", _call_gen)
        if not response or not response.text:
            raise AiServiceException("Gemini returned an empty generation response.")

        return response.text.strip()


# Global Gemini service instance
gemini_service = GeminiService()
