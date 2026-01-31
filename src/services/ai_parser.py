"""AI-powered job description parser using Claude Haiku."""
import json
import os
import re


def is_ai_parsing_available() -> bool:
    """Check if the ANTHROPIC_API_KEY environment variable is set."""
    return bool(os.environ.get('ANTHROPIC_API_KEY'))


SYSTEM_PROMPT = """You are a job description parser. Extract structured data from the provided job description text and return ONLY valid JSON with these fields:

{
  "company_name": "string or null",
  "job_title": "string or null",
  "description": "string or null - brief summary of the role",
  "requirements": "string or null - key requirements/qualifications as a comma-separated list",
  "salary_min": "integer or null - annual salary lower bound",
  "salary_max": "integer or null - annual salary upper bound",
  "salary_currency": "string - 3-letter currency code, default USD",
  "location": "string or null - city/state/country",
  "remote_type": "string or null - one of: remote, hybrid, onsite",
  "source": "string or null - platform or source if mentioned"
}

Rules:
- Return ONLY the JSON object, no markdown fences or explanation.
- For salary, convert to annual integers (e.g., "$150k" = 150000, "$75/hr" = 156000).
- If a field is not found, use null.
- remote_type must be exactly one of: remote, hybrid, onsite, or null.
- salary_currency should be a 3-letter code like USD, EUR, GBP."""


def parse_job_description(raw_text: str) -> dict:
    """Parse a job description using Claude Haiku and return structured data.

    Args:
        raw_text: The raw job description text to parse.

    Returns:
        A dict with extracted fields.

    Raises:
        RuntimeError: If the API call fails or response can't be parsed.
    """
    import anthropic

    # Truncate to 8000 chars to stay within reasonable limits
    text = raw_text[:8000]

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1024,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": text}
        ],
    )

    response_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
    response_text = re.sub(r'\s*```$', '', response_text)
    response_text = response_text.strip()

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse AI response as JSON: {e}")

    # Validate and coerce fields
    valid_remote_types = {"remote", "hybrid", "onsite"}
    if data.get("remote_type") and data["remote_type"] not in valid_remote_types:
        data["remote_type"] = None

    for field in ("salary_min", "salary_max"):
        val = data.get(field)
        if val is not None:
            try:
                data[field] = int(val)
            except (ValueError, TypeError):
                data[field] = None

    if not data.get("salary_currency"):
        data["salary_currency"] = "USD"

    return data
