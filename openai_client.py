import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

PROMPTS_DIR = BASE_DIR / "prompts"
DEFAULT_ANALYSIS_PROMPT_PATH = PROMPTS_DIR / "analysis_prompt.md"
DEFAULT_BID_PROMPT_PATH = PROMPTS_DIR / "bid_prompt.md"


def _load_analysis_prompt() -> str:
    try:
        with DEFAULT_ANALYSIS_PROMPT_PATH.open("r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback minimal prompt if the template is missing
        return (
            "You are an assistant that summarizes and scores freelance projects. "
            "Return JSON with keys: summary, category, rough_score, reasons, risks.\n"
            "Project JSON: {PROJECT_JSON}"
        )


def _load_bid_prompt() -> str:
    try:
        with DEFAULT_BID_PROMPT_PATH.open("r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return (
            "You are generating a JSON object with fields proposal_text, "
            "milestone_plan, free_demo_offered, free_demo_reason based on a project "
            "and an existing analysis. Use plain text, no markdown."
        )


def _get_client() -> OpenAI:
    # The OpenAI client will read OPENAI_API_KEY from the environment/.env
    return OpenAI()


def _extract_json_dict(content: str) -> Dict[str, Any] | None:
    """Try to extract a JSON object from the model output.

    Handles plain JSON as well as content wrapped in ```json fences.
    """

    text = content.strip()

    # First try direct JSON parsing.
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Strip Markdown ```json fences if present.
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Try parsing again after stripping fences.
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # As a last resort, extract the first {...} block.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        json_str = text[start : end + 1]
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


def analyze_project_with_gpt35(
    project: Dict[str, Any],
    model: str | None = None,
) -> Dict[str, Any]:
    """Use a cheap OpenAI model (e.g. gpt-3.5) to summarize, categorize, and score a project.

    Returns a dict with keys: summary, category, rough_score, automation_potential,
    manual_work_notes, reasons, risks.
    """

    client = _get_client()
    prompt_template = _load_analysis_prompt()
    project_json = json.dumps(project, ensure_ascii=False, indent=2)
    prompt = prompt_template.replace("{PROJECT_JSON}", project_json)

    model_name = model or os.getenv("OPENAI_CHEAP_MODEL", "gpt-3.5-turbo")

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "You are a careful assistant that follows the prompt instructions exactly.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.1,
    )

    content = response.choices[0].message.content or "{}"

    # Try to parse JSON response; if it fails, wrap the raw content.
    data = _extract_json_dict(content)
    if data is not None:
        return data

    return {
        "summary": content.strip(),
        "category": "other",
        "rough_score": 0,
        "automation_potential": 0,
        "manual_work_notes": "Model returned non-JSON content.",
        "reasons": "Model returned non-JSON content.",
        "risks": "Parsing error.",
    }


def generate_bid_for_project(
    project: Dict[str, Any],
    analysis: Dict[str, Any],
    profile: Dict[str, str],
    milestone_size: str,
    milestone_count: int,
    model: str | None = None,
) -> Dict[str, Any]:
    """Generate a proposal and milestone plan for a project using a more capable model.

    Returns a dict with keys: proposal_text, milestone_plan, free_demo_offered,
    free_demo_reason.
    """

    client = _get_client()
    prompt_template = _load_bid_prompt()

    title = project.get("title") or ""
    description = project.get("description") or project.get("preview_description") or ""
    seo_url = project.get("seo_url") or ""
    project_url = ""
    if isinstance(seo_url, str) and seo_url:
        project_url = f"https://www.freelancer.com/projects/{seo_url}"

    prompt = (
        prompt_template.replace("{PROJECT_TITLE}", str(title))
        .replace("{PROJECT_DESCRIPTION}", str(description))
        .replace("{PROJECT_URL}", project_url)
        .replace("{ANALYSIS_SUMMARY}", str(analysis.get("summary", "")))
        .replace("{ROUGH_SCORE}", str(analysis.get("rough_score", "")))
        .replace(
            "{AUTOMATION_POTENTIAL}", str(analysis.get("automation_potential", ""))
        )
        .replace(
            "{MANUAL_WORK_NOTES}", str(analysis.get("manual_work_notes", ""))
        )
        .replace("{PROFILE_LABEL}", profile.get("label", ""))
        .replace("{PROFILE_GENERAL}", profile.get("general", ""))
        .replace("{PROFILE_SECTION}", profile.get("section", ""))
        .replace("{PROFILE_LINK}", profile.get("link", ""))
        .replace("{MILESTONE_SIZE}", milestone_size)
        .replace("{MILESTONE_COUNT}", str(milestone_count))
    )

    model_name = model or os.getenv("OPENAI_EXPENSIVE_MODEL", "gpt-4.1-mini")

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "You are a careful assistant that follows the prompt instructions exactly.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.4,
    )

    content = response.choices[0].message.content or "{}"
    data = _extract_json_dict(content)
    if data is not None:
        return data

    return {
        "proposal_text": content.strip(),
        "milestone_plan": {
            "size": milestone_size,
            "count": milestone_count,
            "milestones": [],
        },
        "free_demo_offered": False,
        "free_demo_reason": "Model returned non-JSON content.",
    }
