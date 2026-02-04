"""AI-powered job description parser and resume analyzer using Claude."""
import json
import os
import re


def is_ai_parsing_available() -> bool:
    """Check if the ANTHROPIC_API_KEY environment variable is set."""
    return bool(os.environ.get('ANTHROPIC_API_KEY'))


RESUME_ALIGNMENT_PROMPT = """You are an expert career coach and resume analyst. Analyze how well the candidate's resume aligns with the job requirements.

Provide your analysis as a JSON object with these fields:

{
  "match_score": 0-100 integer representing overall fit,
  "summary": "2-3 sentence overview of the match",
  "matching_skills": ["list of skills/qualifications from resume that match job requirements"],
  "missing_skills": ["list of key requirements from job that are missing or weak in resume"],
  "suggestions": [
    {
      "priority": "high|medium|low",
      "suggestion": "specific, actionable suggestion to improve resume for this role"
    }
  ],
  "keywords_to_add": ["specific keywords/phrases from job description to consider adding"],
  "strengths": ["what makes this candidate a good fit"],
  "concerns": ["potential concerns a hiring manager might have"]
}

Rules:
- Be specific and actionable in suggestions
- Match score: 80+ = strong match, 60-79 = good with gaps, 40-59 = stretch, <40 = significant gaps
- Focus on the most impactful improvements (max 5 suggestions)
- Keywords should be actual phrases from the job description
- Return ONLY valid JSON, no markdown fences"""


def analyze_resume_job_fit(resume_text: str, job_description: str, job_title: str = None, company_name: str = None) -> dict:
    """Analyze how well a resume matches a job description.

    Args:
        resume_text: The candidate's resume content
        job_description: The job posting description/requirements
        job_title: Optional job title for context
        company_name: Optional company name for context

    Returns:
        A dict with match analysis including score, skills, gaps, and suggestions

    Raises:
        RuntimeError: If the API call fails or response can't be parsed
    """
    import anthropic

    # Build context
    context_parts = []
    if job_title:
        context_parts.append(f"Job Title: {job_title}")
    if company_name:
        context_parts.append(f"Company: {company_name}")
    context = "\n".join(context_parts) if context_parts else ""

    # Truncate inputs to stay within limits
    resume_text = resume_text[:6000] if resume_text else ""
    job_description = job_description[:6000] if job_description else ""

    user_message = f"""Analyze this resume against the job description:

{context}

=== JOB DESCRIPTION ===
{job_description}

=== CANDIDATE RESUME ===
{resume_text}

Provide your analysis as JSON."""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=2048,
        temperature=0,
        system=RESUME_ALIGNMENT_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
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

    # Validate match_score
    score = data.get("match_score", 50)
    try:
        data["match_score"] = max(0, min(100, int(score)))
    except (ValueError, TypeError):
        data["match_score"] = 50

    # Ensure lists exist
    for field in ["matching_skills", "missing_skills", "keywords_to_add", "strengths", "concerns"]:
        if not isinstance(data.get(field), list):
            data[field] = []

    if not isinstance(data.get("suggestions"), list):
        data["suggestions"] = []

    return data


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
