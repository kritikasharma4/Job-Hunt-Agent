"""
Unit tests for OllamaProvider implementation.

Tests cover:
- Basic generation
- Structured JSON output
- Error handling
- Health checks
- Input validation
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from config.settings import LLMConfig
from llm.ollama_provider import OllamaProvider


class TestOllamaProviderInitialization:
    """Tests for OllamaProvider initialization."""

    def test_provider_initialization(self):
        """Test basic provider initialization."""
        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        assert provider.config.model == "llama3"
        assert provider.config.provider == "ollama"
        assert provider.base_url == "http://localhost:11434"
        assert provider.generate_endpoint == "http://localhost:11434/api/generate"

    def test_provider_with_custom_config(self):
        """Test provider with custom temperature and max_tokens."""
        config = LLMConfig(
            provider="ollama",
            model="llama3",
            temperature=0.5,
            max_tokens=1024,
        )
        provider = OllamaProvider(config)

        assert provider.config.temperature == 0.5
        assert provider.config.max_tokens == 1024


class TestGenerateMethod:
    """Tests for the generate() method."""

    @patch("llm.ollama_provider.requests.Session.post")
    def test_generate_basic(self, mock_post):
        """Test basic text generation."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Hello, world!"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        result = provider.generate("What is AI?")

        assert result == "Hello, world!"
        mock_post.assert_called_once()

    @patch("llm.ollama_provider.requests.Session.post")
    def test_generate_with_system_prompt(self, mock_post):
        """Test generation with system prompt."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "I am an AI assistant."}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        result = provider.generate(
            "What are you?",
            system_prompt="You are a helpful AI assistant."
        )

        assert result == "I am an AI assistant."
        # Verify system prompt was included in request
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert "You are a helpful AI assistant." in payload["prompt"]

    @patch("llm.ollama_provider.requests.Session.post")
    def test_generate_with_custom_temperature(self, mock_post):
        """Test generation with custom temperature override."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Response"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3", temperature=0.7)
        provider = OllamaProvider(config)

        provider.generate("Test prompt", temperature=0.3)

        # Verify custom temperature was used
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert payload["temperature"] == 0.3

    def test_generate_empty_prompt_raises_error(self):
        """Test that empty prompts raise ValueError."""
        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            provider.generate("")

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            provider.generate("   ")

    @patch("llm.ollama_provider.requests.Session.post")
    def test_generate_connection_error(self, mock_post):
        """Test ConnectionError when Ollama service is down."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        with pytest.raises(ConnectionError, match="Ollama service not running"):
            provider.generate("Test prompt")

    @patch("llm.ollama_provider.requests.Session.post")
    def test_generate_timeout_error(self, mock_post):
        """Test timeout handling."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        config = LLMConfig(provider="ollama", model="llama3", timeout=10)
        provider = OllamaProvider(config)

        with pytest.raises(RuntimeError, match="timed out"):
            provider.generate("Test prompt")

    @patch("llm.ollama_provider.requests.Session.post")
    def test_generate_empty_response(self, mock_post):
        """Test handling of empty model response."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": ""}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        with pytest.raises(RuntimeError, match="empty response"):
            provider.generate("Test prompt")

    @patch("llm.ollama_provider.requests.Session.post")
    def test_generate_invalid_json_response(self, mock_post):
        """Test handling of invalid JSON in response."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        with pytest.raises(RuntimeError, match="Invalid response"):
            provider.generate("Test prompt")


class TestGenerateStructuredOutput:
    """Tests for generate_with_structured_output() method."""

    @patch("llm.ollama_provider.requests.Session.post")
    def test_generate_structured_valid_json(self, mock_post):
        """Test structured output generation with valid JSON."""
        mock_response = Mock()
        json_response = {"task": "analyze", "score": 0.9, "reasoning": "Good match"}
        mock_response.json.return_value = {"response": json.dumps(json_response)}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        schema = {"task": "string", "score": "float", "reasoning": "string"}
        result = provider.generate_with_structured_output(
            "Analyze this job",
            output_schema=schema
        )

        assert result["task"] == "analyze"
        assert result["score"] == 0.9
        assert result["reasoning"] == "Good match"

    @patch("llm.ollama_provider.requests.Session.post")
    def test_generate_structured_json_with_extra_text(self, mock_post):
        """Test extraction of JSON when model adds extra text."""
        mock_response = Mock()
        # Model output with extra text
        response_text = (
            'Here is the analysis:\n'
            '{"task": "match", "score": 0.85}\n'
            'This is a good match.'
        )
        mock_response.json.return_value = {"response": response_text}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        schema = {"task": "string", "score": "float"}
        result = provider.generate_with_structured_output(
            "Analyze",
            output_schema=schema
        )

        assert result["task"] == "match"
        assert result["score"] == 0.85

    def test_generate_structured_invalid_schema(self):
        """Test that invalid schema raises error."""
        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        with pytest.raises(ValueError, match="output_schema must be"):
            provider.generate_with_structured_output("Prompt", output_schema={})

        with pytest.raises(ValueError, match="output_schema must be"):
            provider.generate_with_structured_output("Prompt", output_schema=None)


class TestValidateCredentials:
    """Tests for validate_credentials() method."""

    @patch("llm.ollama_provider.requests.Session.get")
    def test_validate_credentials_success(self, mock_get):
        """Test successful credential validation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:latest"},
                {"name": "mistral:latest"},
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        assert provider.validate_credentials() is True

    @patch("llm.ollama_provider.requests.Session.get")
    def test_validate_credentials_model_not_found(self, mock_get):
        """Test validation when model is not available."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "mistral:latest"},
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        assert provider.validate_credentials() is False

    @patch("llm.ollama_provider.requests.Session.get")
    def test_validate_credentials_service_down(self, mock_get):
        """Test validation when Ollama service is down."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        assert provider.validate_credentials() is False

    @patch("llm.ollama_provider.requests.Session.get")
    def test_validate_credentials_timeout(self, mock_get):
        """Test validation with timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        assert provider.validate_credentials() is False


class TestHealthCheck:
    """Tests for health_check() method."""

    @patch("llm.ollama_provider.requests.Session.get")
    def test_health_check_all_good(self, mock_get):
        """Test health check when everything is working."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:latest"},
                {"name": "mistral:latest"},
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        health = provider.health_check()

        assert health["service_running"] is True
        assert health["model_available"] is True
        assert health["error"] is None
        assert len(health["available_models"]) == 2

    @patch("llm.ollama_provider.requests.Session.get")
    def test_health_check_service_down(self, mock_get):
        """Test health check when service is not running."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        health = provider.health_check()

        assert health["service_running"] is False
        assert health["model_available"] is False
        assert health["error"] is not None

    @patch("llm.ollama_provider.requests.Session.get")
    def test_health_check_model_not_available(self, mock_get):
        """Test health check when model is not loaded."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "mistral:latest"},
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        health = provider.health_check()

        assert health["service_running"] is True
        assert health["model_available"] is False


class TestExtractJsonFromResponse:
    """Tests for _extract_json_from_response() static method."""

    def test_extract_json_direct_json_object(self):
        """Test extraction of direct JSON object."""
        response = '{"key": "value", "number": 42}'
        result = OllamaProvider._extract_json_from_response(response)

        assert result["key"] == "value"
        assert result["number"] == 42

    def test_extract_json_with_surrounding_text(self):
        """Test extraction with surrounding text."""
        response = 'Here is the result: {"status": "success"} Thanks!'
        result = OllamaProvider._extract_json_from_response(response)

        assert result["status"] == "success"

    def test_extract_json_array(self):
        """Test extraction of JSON array."""
        response = '[{"id": 1}, {"id": 2}]'
        result = OllamaProvider._extract_json_from_response(response)

        assert "results" in result
        assert len(result["results"]) == 2

    def test_extract_json_empty_response(self):
        """Test extraction with empty response."""
        with pytest.raises(ValueError, match="empty"):
            OllamaProvider._extract_json_from_response("")

    def test_extract_json_invalid_json(self):
        """Test extraction with invalid JSON."""
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            OllamaProvider._extract_json_from_response("This is not JSON at all")

    def test_extract_json_whitespace_handling(self):
        """Test JSON extraction with extra whitespace."""
        response = '   {"trimmed": true}   \n'
        result = OllamaProvider._extract_json_from_response(response)

        assert result["trimmed"] is True


class TestPullModel:
    """Tests for pull_model() method."""

    @patch("llm.ollama_provider.requests.Session.post")
    def test_pull_model_success(self, mock_post):
        """Test successful model pull."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        result = provider.pull_model("mistral")

        assert result is True
        mock_post.assert_called_once()

    @patch("llm.ollama_provider.requests.Session.post")
    def test_pull_model_failure(self, mock_post):
        """Test failed model pull."""
        mock_post.side_effect = requests.exceptions.RequestException("Pull failed")

        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        result = provider.pull_model("nonexistent")

        assert result is False

    def test_pull_model_empty_name(self):
        """Test pull with empty model name."""
        config = LLMConfig(provider="ollama", model="llama3")
        provider = OllamaProvider(config)

        with pytest.raises(ValueError, match="Model name cannot be empty"):
            provider.pull_model("")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
