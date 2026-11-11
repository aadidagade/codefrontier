"""
Unit tests for Step 7: GeminiService, embeddings, and vector operations.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.gemini_service import GeminiService, redact_secrets
from app.core.exceptions import ValidationException, AiServiceException
from app.core.config import settings


class DummyEmbeddingValues:
    def __init__(self, values):
        self.values = values


class DummyEmbedResponse:
    def __init__(self, vectors):
        self.embeddings = [DummyEmbeddingValues(v) for v in vectors]


class DummyGenerateResponse:
    def __init__(self, text):
        self.text = text


def test_text_normalization():
    service = GeminiService()
    raw = "  This   has  multiple   spaces \n\n\n\n and excess newlines.  "
    normalized = service._normalize_text(raw)
    assert normalized == "This has multiple spaces \n\n and excess newlines."


def test_empty_text_raises_validation_error():
    service = GeminiService()
    with pytest.raises(ValidationException):
        service.generate_embedding("   \n\t  ")


def test_secret_redaction():
    fake_key = "AIzaSyFakeSecretKey12345"
    with patch.object(settings, "GEMINI_API_KEY", fake_key):
        err_msg = f"Error calling Gemini with key {fake_key} at endpoint."
        redacted = redact_secrets(err_msg)
        assert fake_key not in redacted
        assert "[REDACTED_API_KEY]" in redacted


def test_generate_embedding_success():
    service = GeminiService()
    mock_client = MagicMock()
    mock_vector = [0.01] * 768
    mock_client.models.embed_content.return_value = DummyEmbedResponse([mock_vector])

    with patch.object(service, "get_client", return_value=mock_client), \
         patch.object(service, "get_supported_embedding_model", return_value="gemini-embedding-2"):
        vec = service.generate_embedding("Valid document chunk text")
        assert len(vec) == 768
        assert vec == mock_vector


def test_generate_embedding_dimension_mismatch():
    service = GeminiService()
    mock_client = MagicMock()
    # Wrong dimension: 512 instead of 768
    wrong_dim_vector = [0.01] * 512
    mock_client.models.embed_content.return_value = DummyEmbedResponse([wrong_dim_vector])

    with patch.object(service, "get_client", return_value=mock_client), \
         patch.object(service, "get_supported_embedding_model", return_value="gemini-embedding-2"):
        with pytest.raises(AiServiceException) as exc_info:
            service.generate_embedding("Valid document chunk text")
        assert "dimension mismatch" in str(exc_info.value).lower()


def test_batch_embeddings():
    service = GeminiService()
    mock_client = MagicMock()
    mock_vector_1 = [0.1] * 768
    mock_vector_2 = [0.2] * 768
    mock_client.models.embed_content.return_value = DummyEmbedResponse([mock_vector_1, mock_vector_2])

    with patch.object(service, "get_client", return_value=mock_client), \
         patch.object(service, "get_supported_embedding_model", return_value="gemini-embedding-2"):
        results = service.generate_embeddings_batch(["Chunk one content", "Chunk two content"])
        assert len(results) == 2
        assert len(results[0]) == 768
        assert len(results[1]) == 768


def test_generate_content_success():
    service = GeminiService()
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = DummyGenerateResponse("Synthesized handover summary")

    with patch.object(service, "get_client", return_value=mock_client), \
         patch.object(service, "get_supported_generation_model", return_value="gemini-2.5-flash"):
        res = service.generate_content("Synthesize handover")
        assert res == "Synthesized handover summary"


def test_retry_on_transient_error():
    service = GeminiService()
    mock_client = MagicMock()
    # First call raises transient 429 quota error, second succeeds
    mock_client.models.generate_content.side_effect = [
        Exception("429 ResourceExhausted: rate limit exceeded"),
        DummyGenerateResponse("Recovered response after backoff"),
    ]

    with patch.object(service, "get_client", return_value=mock_client), \
         patch.object(service, "get_supported_generation_model", return_value="gemini-2.5-flash"), \
         patch("time.sleep", return_value=None):  # Avoid waiting in unit tests
        res = service.generate_content("Prompt")
        assert res == "Recovered response after backoff"
