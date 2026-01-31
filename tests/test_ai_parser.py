"""Tests for the AI job description parser."""
import json
import pytest
from unittest.mock import patch, MagicMock

from src.services.ai_parser import (
    is_ai_parsing_available,
    parse_job_description,
)


class TestIsAiParsingAvailable:
    def test_returns_true_when_key_set(self):
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-test-123'}):
            assert is_ai_parsing_available() is True

    def test_returns_false_when_key_missing(self):
        with patch.dict('os.environ', {}, clear=True):
            assert is_ai_parsing_available() is False

    def test_returns_false_when_key_empty(self):
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': ''}):
            assert is_ai_parsing_available() is False


def _mock_anthropic_response(response_text):
    """Create a mock Anthropic message response."""
    mock_content = MagicMock()
    mock_content.text = response_text
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    return mock_message


def _make_mock_client(response_text):
    """Create a mock Anthropic client that returns given response text."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_anthropic_response(response_text)
    return mock_client


class TestParseJobDescription:
    @patch('anthropic.Anthropic')
    def test_basic_parsing(self, mock_anthropic_cls):
        response_data = {
            "company_name": "Acme Corp",
            "job_title": "Senior Engineer",
            "description": "Build things",
            "requirements": "Python, SQL",
            "salary_min": 150000,
            "salary_max": 200000,
            "salary_currency": "USD",
            "location": "San Francisco, CA",
            "remote_type": "hybrid",
            "source": "LinkedIn"
        }
        mock_anthropic_cls.return_value = _make_mock_client(json.dumps(response_data))

        result = parse_job_description("This is a test job description that is long enough.")

        assert result["company_name"] == "Acme Corp"
        assert result["job_title"] == "Senior Engineer"
        assert result["salary_min"] == 150000
        assert result["salary_max"] == 200000
        assert result["remote_type"] == "hybrid"

    @patch('anthropic.Anthropic')
    def test_strips_markdown_fences(self, mock_anthropic_cls):
        response_data = {
            "company_name": "Test Co",
            "job_title": "Dev",
            "description": None,
            "requirements": None,
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "USD",
            "location": None,
            "remote_type": None,
            "source": None
        }
        fenced = "```json\n" + json.dumps(response_data) + "\n```"
        mock_anthropic_cls.return_value = _make_mock_client(fenced)

        result = parse_job_description("A long enough job description for testing.")

        assert result["company_name"] == "Test Co"

    @patch('anthropic.Anthropic')
    def test_invalid_remote_type_set_to_none(self, mock_anthropic_cls):
        response_data = {
            "company_name": "Test",
            "job_title": "Test",
            "description": None,
            "requirements": None,
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "USD",
            "location": None,
            "remote_type": "work-from-home",
            "source": None
        }
        mock_anthropic_cls.return_value = _make_mock_client(json.dumps(response_data))

        result = parse_job_description("A long enough job description for testing.")

        assert result["remote_type"] is None

    @patch('anthropic.Anthropic')
    def test_salary_coercion(self, mock_anthropic_cls):
        response_data = {
            "company_name": "Test",
            "job_title": "Test",
            "description": None,
            "requirements": None,
            "salary_min": "120000",
            "salary_max": "not-a-number",
            "salary_currency": None,
            "location": None,
            "remote_type": None,
            "source": None
        }
        mock_anthropic_cls.return_value = _make_mock_client(json.dumps(response_data))

        result = parse_job_description("A long enough job description for testing.")

        assert result["salary_min"] == 120000
        assert result["salary_max"] is None
        assert result["salary_currency"] == "USD"

    @patch('anthropic.Anthropic')
    def test_invalid_json_raises_runtime_error(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _make_mock_client("not valid json at all")

        with pytest.raises(RuntimeError, match="Failed to parse AI response"):
            parse_job_description("A long enough job description for testing.")

    @patch('anthropic.Anthropic')
    def test_truncates_long_input(self, mock_anthropic_cls):
        response_data = {
            "company_name": "Test",
            "job_title": "Test",
            "description": None,
            "requirements": None,
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "USD",
            "location": None,
            "remote_type": None,
            "source": None
        }
        mock_client = _make_mock_client(json.dumps(response_data))
        mock_anthropic_cls.return_value = mock_client

        long_text = "x" * 10000
        parse_job_description(long_text)

        # Verify the text passed to the API was truncated
        call_args = mock_client.messages.create.call_args
        sent_text = call_args[1]['messages'][0]['content']
        assert len(sent_text) == 8000
