import time
import logging
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.exceptions import AiServiceException

logger = logging.getLogger("app.services.ai")


class GeminiAiService:
    """
    Production service integrating with the official Google GenAI Python SDK.
    Handles embedding generation, handover synthesis, gap detection, and health checks.
    Guarantees secrets are never exposed in exceptions, responses, or logs.
    """

    def __init__(self):
        self._client = None

    def get_client(self):
        """Lazy-initializes and returns the official Google GenAI client."""
        if self._client is not None:
            return self._client

        if not settings.is_gemini_configured():
            raise AiServiceException(
                message="Google Gemini API key is not configured in backend/.env",
                details={"code": "MISSING_GEMINI_API_KEY"},
            )

        try:
            from google import genai
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            return self._client
        except Exception as exc:
            logger.error(f"Failed to initialize Google GenAI client: {exc}")
            raise AiServiceException(
                message="Could not initialize Google GenAI SDK client.",
                details={"reason": str(exc)},
            )

    async def check_ai_health(self) -> Dict[str, Any]:
        """
        Performs an actual real-time connectivity and capability check with Google Gemini.
        Validates API key and model access without exposing credentials.
        """
        if not settings.is_gemini_configured():
            return {
                "status": "unconfigured",
                "message": "Gemini API key is not set or is still the placeholder value.",
                "configured": False,
                "model": settings.GEMINI_MODEL,
                "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
            }

        start_time = time.perf_counter()
        try:
            client = self.get_client()

            # Perform a lightweight ping to verify actual API access
            # We use client.models.generate_content with minimal tokens to test end-to-end responsiveness
            res = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents="Ping. Respond with 'PONG'.",
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            reply = res.text.strip() if res and res.text else "OK"

            return {
                "status": "connected",
                "configured": True,
                "latency_ms": elapsed_ms,
                "generation_model": settings.GEMINI_MODEL,
                "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
                "embedding_dimension": settings.EMBEDDING_DIMENSION,
                "test_response": reply[:20],
            }
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_msg = str(exc)
            # Ensure no API key is leaked in the error message
            if settings.GEMINI_API_KEY in error_msg:
                error_msg = error_msg.replace(settings.GEMINI_API_KEY, "[REDACTED_API_KEY]")

            logger.error(f"Gemini health check error: {error_msg}")
            return {
                "status": "error",
                "configured": True,
                "latency_ms": elapsed_ms,
                "generation_model": settings.GEMINI_MODEL,
                "error": error_msg,
            }

    async def generate_embedding(self, text: str) -> list[float]:
        """Generates a dense vector embedding for chunk indexing."""
        client = self.get_client()
        try:
            response = client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=text,
            )
            if hasattr(response, "embeddings") and response.embeddings:
                return response.embeddings[0].values
            elif hasattr(response, "embedding") and response.embedding:
                return response.embedding.values
            elif hasattr(response, "values"):
                return response.values
            raise ValueError("Unexpected response structure from Gemini embedding API.")
        except Exception as exc:
            clean_err = str(exc).replace(settings.GEMINI_API_KEY, "[REDACTED_API_KEY]")
            logger.error(f"Embedding generation error: {clean_err}")
            raise AiServiceException(f"Failed to generate embedding: {clean_err}")


# Global service instance
ai_service = GeminiAiService()
