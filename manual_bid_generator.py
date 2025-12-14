"""
Manual Bid Generator - Interactive bid generation with learning.

Features:
- Generate bids from project URL or pasted text
- Choose prompt version, language, tone
- Compare multiple versions
- Track outcomes for learning
- Learn from winning bids
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from bid_history import (
    save_bid,
    get_bid,
    get_recent_bids,
    get_winning_bids,
    get_successful_bids,
    search_bids_by_type,
    update_bid_outcome,
    save_final_bid,
    get_learning_stats,
    get_high_rated_bids,
    get_high_rated_by_type,
    get_uploaded_bids,
)
from prompt_manager import (
    get_prompt_versions,
    load_prompt,
    load_active_prompt,
    get_active_prompt_version,
)
from profiles import get_profile, select_profile_key

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

EXTENDED_PROFILE_PATH = BASE_DIR / "config" / "extended_profile.json"

# Project type categories
PROJECT_TYPES = [
    "web_app",
    "mobile_app",
    "api_backend",
    "ecommerce",
    "wordpress",
    "shopify",
    "odoo_erp",
    "scraping",
    "automation",
    "data_analysis",
    "ai_ml",
    "consulting",
    "bug_fix",
    "other",
]

# Supported languages
LANGUAGES = ["auto", "en", "de", "es"]

# Tone options
TONES = ["auto", "formal", "friendly", "neutral"]


def _get_client() -> OpenAI:
    """Get OpenAI client."""
    return OpenAI()


def _load_extended_profile() -> Dict[str, Any]:
    """Load the extended profile from me.hiplus.de."""
    if not EXTENDED_PROFILE_PATH.exists():
        return {}
    
    try:
        with EXTENDED_PROFILE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _format_extended_profile(profile: Dict[str, Any]) -> str:
    """Format extended profile for prompt injection."""
    if not profile:
        return "No extended profile available."
    
    parts = []
    
    if profile.get("name"):
        parts.append(f"Name: {profile['name']}")
    
    if profile.get("tagline"):
        parts.append(f"Tagline: {profile['tagline']}")
    
    summary = profile.get("summary", {})
    if summary:
        parts.append("\nBackground:")
        for key, val in summary.items():
            parts.append(f"- {val}")
    
    expertise = profile.get("core_expertise", {})
    if expertise:
        parts.append("\nCore Expertise:")
        for key, val in expertise.items():
            parts.append(f"- {key.replace('_', ' ').title()}: {val}")
    
    usps = profile.get("usps", [])
    if usps:
        parts.append("\nUnique Selling Points:")
        for usp in usps[:3]:  # Limit to top 3
            parts.append(f"- {usp}")
    
    testimonials = profile.get("testimonials", [])
    if testimonials:
        parts.append("\nClient Testimonial:")
        parts.append(f'"{testimonials[0]["text"][:200]}..."')
    
    return "\n".join(parts)


def _extract_json_dict(content: str) -> Dict[str, Any] | None:
    """Try to extract a JSON object from the model output."""
    text = content.strip()
    
    # First try direct JSON parsing
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    
    # Strip Markdown fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    
    # Try parsing again
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    
    # Extract first {...} block
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


def _determine_milestone_context(budget_min: Optional[float], budget_max: Optional[float]) -> Tuple[str, int]:
    """Determine milestone size and count based on budget."""
    avg = None
    if budget_min is not None and budget_max is not None:
        avg = (budget_min + budget_max) / 2
    elif budget_min is not None:
        avg = budget_min
    elif budget_max is not None:
        avg = budget_max
    
    if avg is None:
        return "unknown", 3
    elif avg < 200:
        return "small", 2
    elif avg < 1000:
        return "medium", 3
    else:
        return "large", 4


def generate_bid(
    project_title: str,
    project_description: str,
    project_type: str = "other",
    language: str = "auto",
    tone: str = "auto",
    prompt_version: Optional[str] = None,
    model: Optional[str] = None,
    project_url: Optional[str] = None,
    project_id: Optional[int] = None,
    budget_min: Optional[float] = None,
    budget_max: Optional[float] = None,
    include_similar_bids: bool = True,
    additional_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a bid for a project.
    
    Args:
        project_title: Title of the project
        project_description: Full project description
        project_type: Category of project (from PROJECT_TYPES)
        language: Language to write in (auto, en, de, es)
        tone: Tone to use (auto, formal, friendly, neutral)
        prompt_version: Specific prompt version to use (or None for active)
        model: OpenAI model to use (default from env)
        project_url: URL of the project (optional)
        project_id: Freelancer.com project ID (optional)
        budget_min: Minimum budget (optional)
        budget_max: Maximum budget (optional)
        include_similar_bids: Whether to include similar past bids for context
        additional_context: Personal details or special context (optional)
    
    Returns:
        Dict with bid_text, milestone_plan, metadata, and bid_id
    """
    
    client = _get_client()
    
    # Load prompt
    if prompt_version:
        prompt_content = load_prompt(prompt_version)
        if not prompt_content:
            prompt_version, prompt_content = load_active_prompt()
    else:
        prompt_version, prompt_content = load_active_prompt()
    
    # Get profile based on project type
    profile_key = _map_project_type_to_profile(project_type)
    profile = get_profile(profile_key)
    
    # Get extended profile
    extended_profile = _load_extended_profile()
    extended_profile_text = _format_extended_profile(extended_profile)
    
    # Get portfolio link
    portfolio_links = extended_profile.get("portfolio_links", {})
    profile_link = portfolio_links.get(profile_key) or portfolio_links.get("main") or profile.get("link", "")
    
    # Milestone context
    milestone_size, milestone_count = _determine_milestone_context(budget_min, budget_max)
    
    # Language/tone overrides
    language_override = "" if language == "auto" else f"Write this proposal in {_language_name(language)}."
    tone_override = "" if tone == "auto" else f"Use a {tone} tone throughout."
    
    # Additional context from user
    additional_context_text = ""
    if additional_context and additional_context.strip():
        additional_context_text = f"\n\n## Additional Personal Context\n{additional_context.strip()}\n"
    
    # Build the prompt
    prompt = (
        prompt_content
        .replace("{PROJECT_TITLE}", project_title)
        .replace("{PROJECT_DESCRIPTION}", project_description)
        .replace("{PROJECT_URL}", project_url or "")
        .replace("{ANALYSIS_SUMMARY}", "")
        .replace("{ROUGH_SCORE}", "")
        .replace("{AUTOMATION_POTENTIAL}", "")
        .replace("{MANUAL_WORK_NOTES}", "")
        .replace("{PROFILE_LABEL}", profile.get("label", ""))
        .replace("{PROFILE_GENERAL}", profile.get("general", ""))
        .replace("{PROFILE_SECTION}", profile.get("section", ""))
        .replace("{PROFILE_LINK}", profile_link)
        .replace("{EXTENDED_PROFILE}", extended_profile_text)
        .replace("{MILESTONE_SIZE}", milestone_size)
        .replace("{MILESTONE_COUNT}", str(milestone_count))
        .replace("{LANGUAGE_OVERRIDE}", language_override)
        .replace("{TONE_OVERRIDE}", tone_override)
    )
    
    # Add additional context if provided
    if additional_context_text:
        prompt += additional_context_text
    
    # Add similar successful bids for context
    if include_similar_bids:
        similar_context = _get_similar_bids_context(project_type)
        if similar_context:
            prompt += f"\n\n## Reference: Successful past bids for similar projects\n{similar_context}"
    
    # Select model
    model_name = model or os.getenv("OPENAI_CHEAP_MODEL", "gpt-4o-mini")
    
    # Generate
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "You are an expert freelance bid writer. Follow the prompt instructions exactly and output valid JSON.",
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
    
    if data is None:
        data = {
            "proposal_text": content.strip(),
            "milestone_plan": {
                "size": milestone_size,
                "count": milestone_count,
                "milestones": [],
            },
            "free_demo_offered": False,
            "free_demo_reason": "Model returned non-JSON content.",
        }
    
    # Save to history
    bid_id = save_bid(
        project_title=project_title,
        bid_text=data.get("proposal_text", ""),
        prompt_version=prompt_version,
        project_id=project_id,
        project_url=project_url,
        project_description=project_description,
        project_type=project_type,
        project_language=data.get("detected_language", language),
        project_budget_min=budget_min,
        project_budget_max=budget_max,
        milestone_plan=data.get("milestone_plan"),
        model_used=model_name,
        tone=data.get("detected_tone", tone),
    )
    
    return {
        "bid_id": bid_id,
        "bid_text": data.get("proposal_text", ""),
        "milestone_plan": data.get("milestone_plan", {}),
        "free_demo_offered": data.get("free_demo_offered", False),
        "free_demo_reason": data.get("free_demo_reason", ""),
        "detected_tone": data.get("detected_tone", tone),
        "detected_language": data.get("detected_language", language),
        "prompt_version": prompt_version,
        "model_used": model_name,
        "identified_pain_point": data.get("identified_pain_point", ""),
    }


def generate_multiple_versions(
    project_title: str,
    project_description: str,
    prompt_versions: List[str],
    **kwargs,
) -> List[Dict[str, Any]]:
    """Generate bids using multiple prompt versions for comparison."""
    results = []
    
    for version in prompt_versions:
        try:
            result = generate_bid(
                project_title=project_title,
                project_description=project_description,
                prompt_version=version,
                **kwargs,
            )
            results.append(result)
        except Exception as e:
            results.append({
                "prompt_version": version,
                "error": str(e),
            })
    
    return results


def _map_project_type_to_profile(project_type: str) -> str:
    """Map project type to profile key."""
    mapping = {
        "web_app": "web",
        "mobile_app": "mobile",
        "api_backend": "web",
        "ecommerce": "web",
        "wordpress": "web",
        "shopify": "web",
        "odoo_erp": "coding",
        "scraping": "coding",
        "automation": "coding",
        "data_analysis": "coding",
        "ai_ml": "coding",
        "consulting": "hybrid",
        "bug_fix": "web",
        "other": "coding",
    }
    return mapping.get(project_type, "coding")


def _language_name(code: str) -> str:
    """Get full language name from code."""
    names = {
        "en": "English",
        "de": "German",
        "es": "Spanish",
    }
    return names.get(code, "English")


def _get_similar_bids_context(project_type: str, limit: int = 2) -> str:
    """
    Get context from similar high-rated past bids for learning.
    
    Priority order:
    1. Uploaded bids (my wins, other freelancer wins, liked bids)
    2. High-rated bids from same project type
    3. General high-rated bids
    4. Any successful bids
    
    The system learns from ratings:
    - good (+5): Bid was well-written, client responded positively
    - winning (+10 bonus): Client accepted the bid
    - bad (-5): Bid didn't work, avoid this approach
    - uploaded: +15 (my win) or +20 (other freelancer) for learning priority
    """
    # First priority: Uploaded bids of same type
    bids = get_uploaded_bids(limit=limit)
    bids = [b for b in bids if b.get("project_type") == project_type]
    
    # If no uploaded of this type, get any uploaded bids
    if not bids:
        bids = get_uploaded_bids(limit=limit)
    
    # Second priority: High-rated bids for this project type
    if not bids:
        bids = get_high_rated_by_type(project_type, min_rating=5, limit=limit)
    
    # Third priority: General high-rated bids
    if not bids:
        bids = get_high_rated_bids(min_rating=5, limit=limit)
    
    # Fourth priority: Any successful bids
    if not bids:
        all_bids = search_bids_by_type(project_type, limit=limit * 2)
        bids = [b for b in all_bids if b.get("was_engaged") or b.get("was_won")]
    
    if not bids:
        return ""
    
    parts = ["--- HIGH-RATED BIDS FOR REFERENCE ---"]
    for bid in bids[:2]:
        rating = bid.get("rating", 0)
        status = f"Rating: {rating:+d}"
        
        # Add special indicators for uploaded bids
        if bid.get("is_uploaded"):
            source = bid.get("upload_source", "unknown")
            if source == "my_win":
                status += " | MY WIN"
            elif source == "other_freelancer":
                status += " | COMPETITOR WIN"
            else:
                status += " | LIKED"
        elif bid.get("was_won"):
            status += " | WON"
        elif bid.get("was_engaged"):
            status += " | ENGAGED"
        
        final_text = bid.get("final_bid_text") or bid.get("bid_text", "")
        if final_text:
            parts.append(f"\n[{status}] {bid.get('project_title', 'Unknown')}:")
            parts.append(final_text[:300] + "..." if len(final_text) > 300 else final_text)
    
    parts.append("\n--- END REFERENCE ---")
    return "\n".join(parts)


# ----- Outcome tracking API -----

def mark_bid_outcome(
    bid_id: int,
    outcome: str,
    was_viewed: bool = False,
    was_engaged: bool = False,
    was_won: bool = False,
    was_high_rank: bool = False,
    notes: Optional[str] = None,
) -> bool:
    """Mark the outcome of a bid for learning."""
    return update_bid_outcome(
        bid_id=bid_id,
        outcome=outcome,
        was_viewed=was_viewed,
        was_engaged=was_engaged,
        was_won=was_won,
        was_high_rank=was_high_rank,
        notes=notes,
    )


def save_edited_bid(bid_id: int, final_text: str, feedback: Optional[str] = None) -> bool:
    """Save the final edited version of a bid."""
    return save_final_bid(bid_id, final_text, feedback)


def get_stats() -> Dict[str, Any]:
    """Get learning statistics."""
    return get_learning_stats()


# ----- CLI for testing -----

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manual Bid Generator CLI")
    parser.add_argument("--title", required=True, help="Project title")
    parser.add_argument("--description", required=True, help="Project description")
    parser.add_argument("--type", default="other", choices=PROJECT_TYPES, help="Project type")
    parser.add_argument("--language", default="auto", choices=LANGUAGES, help="Language")
    parser.add_argument("--tone", default="auto", choices=TONES, help="Tone")
    parser.add_argument("--prompt", help="Prompt version to use")
    parser.add_argument("--model", help="OpenAI model to use")
    parser.add_argument("--url", help="Project URL")
    
    args = parser.parse_args()
    
    result = generate_bid(
        project_title=args.title,
        project_description=args.description,
        project_type=args.type,
        language=args.language,
        tone=args.tone,
        prompt_version=args.prompt,
        model=args.model,
        project_url=args.url,
    )
    
    print("\n" + "=" * 60)
    print(f"BID ID: {result['bid_id']}")
    print(f"Prompt: {result['prompt_version']}")
    print(f"Model: {result['model_used']}")
    print(f"Detected Language: {result['detected_language']}")
    print(f"Detected Tone: {result['detected_tone']}")
    print("=" * 60)
    print("\nPROPOSAL TEXT:\n")
    print(result['bid_text'])
    print("\n" + "=" * 60)
    print("\nMILESTONES:")
    for ms in result.get('milestone_plan', {}).get('milestones', []):
        print(f"  - {ms.get('title')}: {ms.get('description')}")
    print("=" * 60)
