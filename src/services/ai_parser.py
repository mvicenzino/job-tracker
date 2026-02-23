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

    client = anthropic.Anthropic(timeout=30.0)
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


COVER_LETTER_PROMPT = """You are an expert career coach and professional writer. Write a compelling, personalized cover letter for the candidate.

Guidelines:
- Keep it concise (250-350 words)
- Open with a strong hook that shows genuine interest in the role
- Highlight 2-3 specific experiences/skills from the resume that directly match the job requirements
- Use concrete examples and metrics where possible
- Show knowledge of the company (if provided)
- Close with enthusiasm and a clear call to action
- Maintain a professional but personable tone
- Do NOT use generic phrases like "I am writing to express my interest" or "I believe I would be a great fit"
- Do NOT start with "Dear Hiring Manager" - just start with the body

Return ONLY the cover letter text, no additional formatting or explanation."""


def generate_cover_letter(resume_text: str, job_description: str, job_title: str = None, company_name: str = None) -> str:
    """Generate a tailored cover letter based on resume and job description.

    Args:
        resume_text: The candidate's resume content
        job_description: The job posting description/requirements
        job_title: Optional job title for context
        company_name: Optional company name for context

    Returns:
        A string containing the generated cover letter

    Raises:
        RuntimeError: If the API call fails
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

    user_message = f"""Write a cover letter for this candidate applying to this job:

{context}

=== JOB DESCRIPTION ===
{job_description}

=== CANDIDATE RESUME ===
{resume_text}

Write a compelling cover letter that highlights the candidate's most relevant qualifications."""

    client = anthropic.Anthropic(timeout=30.0)
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1024,
        temperature=0.7,  # Slightly creative for better writing
        system=COVER_LETTER_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
        ],
    )

    return message.content[0].text.strip()


INTERVIEW_PREP_PROMPT = """You are a world-class interview coach who has prepared thousands of candidates for roles at top companies. You combine deep technical knowledge with behavioral interview expertise and the STAR method.

Your task: Generate the most comprehensive, personalized interview preparation package possible. Every piece of advice must be grounded in the SPECIFIC details from the candidate's resume and the SPECIFIC requirements from the job description. Never give generic advice.

Return a JSON object with EXACTLY this structure:

{
  "questions": [
    {
      "question": "The exact question an interviewer would ask",
      "category": "behavioral|technical|system_design|leadership|culture_fit",
      "difficulty": "warm_up|standard|deep_dive",
      "why_asked": "What the interviewer is really evaluating with this question",
      "answer_strategy": "Concise coaching on how to answer using candidate's specific experience",
      "star_example": {
        "situation": "Reference a specific role/project/context from the resume",
        "task": "What challenge or responsibility they faced",
        "action": "Specific actions they took (from resume details)",
        "result": "Quantifiable outcome to highlight"
      },
      "follow_ups": ["Likely follow-up question 1", "Likely follow-up question 2"]
    }
  ],
  "talking_points": [
    {
      "point": "A key strength or differentiator",
      "evidence": "Specific resume item that proves this (company, project, metric)",
      "relevance": "Why this matters for this specific role's requirements",
      "how_to_weave_in": "Natural way to bring this up during the interview"
    }
  ],
  "questions_to_ask": [
    {
      "question": "A thoughtful, specific question",
      "category": "role|team|culture|growth|technical",
      "why_it_impresses": "Why this question signals you're a strong candidate"
    }
  ],
  "company_brief": {
    "description": "What the company does and their market position",
    "culture_signals": "What the job description reveals about company culture and values",
    "focus_areas": "Current business priorities and strategic direction evident from the JD",
    "recent_context": "Any hints about current challenges, growth, or initiatives"
  },
  "red_flags": [
    {
      "concern": "A potential gap or objection a hiring manager might raise",
      "reframe": "How to proactively address this and turn it into a positive"
    }
  ],
  "closing_strategy": {
    "elevator_pitch": "A compelling 30-second 'Tell me about yourself' answer tailored to this role",
    "closing_statement": "A strong closing statement for the end of the interview",
    "differentiators": ["3 things that set this candidate apart for THIS specific role"]
  }
}

REQUIREMENTS:
- Generate 8-10 interview questions with this mix:
  * 2-3 behavioral (past experience using STAR)
  * 2-3 technical (role-specific knowledge/skills)
  * 1-2 system design or problem-solving (if technical role)
  * 1-2 leadership/collaboration
  * 1 culture fit
- Every question MUST have a complete star_example using ACTUAL details from the resume
- Include 2 follow-up questions per main question
- difficulty should progress: start with warm_up, mostly standard, end with deep_dive
- Generate 5-6 talking points, each backed by specific resume evidence
- Generate 5 questions to ask, covering different categories
- Identify 3-4 potential red flags/gaps and how to address each
- The elevator_pitch must reference the candidate's top 2-3 relevant achievements
- The closing_statement should tie the candidate's experience to the company's needs
- Be HYPER-SPECIFIC: use real company names, project names, technologies, and metrics from the resume
- Return ONLY valid JSON, no markdown fences or extra text"""


def generate_interview_prep(resume_text: str, job_description: str, job_title: str = None, company_name: str = None) -> dict:
    """Generate comprehensive interview preparation materials using AI.

    Uses Claude Sonnet for deep analysis of resume-to-job alignment, producing
    STAR-framework answers, objection handling, and closing strategy.

    Args:
        resume_text: The candidate's resume content
        job_description: The job posting description/requirements
        job_title: Optional job title for context
        company_name: Optional company name for context

    Returns:
        A dict with comprehensive interview prep materials

    Raises:
        RuntimeError: If the API call fails or response can't be parsed
    """
    import anthropic

    # Build context header
    context_parts = []
    if job_title:
        context_parts.append(f"Job Title: {job_title}")
    if company_name:
        context_parts.append(f"Company: {company_name}")
    context = "\n".join(context_parts) if context_parts else ""

    # Allow more text for deeper analysis
    resume_text = resume_text[:8000] if resume_text else ""
    job_description = job_description[:8000] if job_description else ""

    user_message = f"""Generate a comprehensive interview preparation package for this candidate and role.

{context}

=== JOB DESCRIPTION ===
{job_description}

=== CANDIDATE RESUME ===
{resume_text}

Analyze the alignment deeply. For every question, map it to specific resume experience. For every talking point, cite specific evidence. Make the prep so personalized that the candidate feels like they have an unfair advantage."""

    client = anthropic.Anthropic(timeout=30.0)
    message = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=4096,
        temperature=0.3,
        system=INTERVIEW_PREP_PROMPT,
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

    # Validate and ensure required fields exist with proper types
    if not isinstance(data.get("questions"), list):
        data["questions"] = []
    if not isinstance(data.get("talking_points"), list):
        data["talking_points"] = []
    if not isinstance(data.get("questions_to_ask"), list):
        data["questions_to_ask"] = []
    if not isinstance(data.get("company_brief"), dict):
        data["company_brief"] = {}
    if not isinstance(data.get("red_flags"), list):
        data["red_flags"] = []
    if not isinstance(data.get("closing_strategy"), dict):
        data["closing_strategy"] = {}

    # Ensure question objects have required sub-fields
    for q in data["questions"]:
        if not isinstance(q.get("star_example"), dict):
            q["star_example"] = {}
        if not isinstance(q.get("follow_ups"), list):
            q["follow_ups"] = []
        if not q.get("difficulty"):
            q["difficulty"] = "standard"
        if not q.get("category"):
            q["category"] = "behavioral"

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

    client = anthropic.Anthropic(timeout=30.0)
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
