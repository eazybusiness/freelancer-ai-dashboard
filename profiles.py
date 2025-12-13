import json
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent
PROFILES_PATH = BASE_DIR / "config" / "profiles.json"
PRIVATE_PROFILES_PATH = BASE_DIR / "config" / "profiles.private.json"


DEFAULT_PROFILES: Dict[str, Dict[str, str]] = {
    "web": {
        "label": "Full-Stack Web & Product Engineering",
        "link": "https://your-portfolio.example/web",
        "general": (
            "Hi, I'm a senior full-stack engineer and product-minded architect.\n\n"
            "I design and build web applications end-to-end: from requirements and UX "
            "to backend architecture, DevOps, and production monitoring. I enjoy turning "
            "ambiguous business ideas into stable, maintainable software products."
        ),
        "section": (
            "Full-Stack Excellence: Building robust web applications from concept to deployment.\n"
            "Technical Stack: Python (FastAPI/Flask), Node.js, React, Next.js, TypeScript.\n"
            "Database Expertise: PostgreSQL, MongoDB, MySQL with optimized query design.\n"
            "API Development: RESTful APIs, background workers, integrations with third-party APIs.\n"
            "Cloud & DevOps: Docker, CI/CD pipelines, basic monitoring and logging."
        ),
    },
    "mobile": {
        "label": "Mobile Apps & Cross-Platform",
        "link": "https://your-portfolio.example/mobile",
        "general": (
            "Hi, I'm a full-stack and mobile engineer focused on shipping reliable apps.\n\n"
            "I build cross-platform and native mobile applications, connect them to secure "
            "backends, and care about performance, UX, and maintainability."
        ),
        "section": (
            "Mobile Development: Native iOS/Android and cross-platform apps with Flutter/React Native.\n"
            "Mobile-First Design: Responsive, intuitive UI/UX following platform guidelines.\n"
            "App Store: Deployment support and basic ASO strategy.\n"
            "Offline & Sync: Robust offline functionality with seamless data sync."
        ),
    },
    "coding": {
        "label": "Innovation, Automation & Prototyping",
        "link": "https://your-portfolio.example/labs",
        "general": (
            "Hi, I'm an engineer who enjoys exploring new ideas, automating workflows, "
            "and building proof-of-concept products.\n\n"
            "I work across the stack, from backend services and data pipelines to quick "
            "interfaces that help validate concepts with real users."
        ),
        "section": (
            "Innovation Prototyping: Rapid MVPs and proof-of-concept projects.\n"
            "Emerging Tech: AI/ML integration, automation, experimental features.\n"
            "Performance: Load testing, security reviews, and optimization.\n"
            "R&D: Exploring new frameworks, APIs, and architectural patterns."
        ),
    },
}


def _merge_with_defaults(stored: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    merged: Dict[str, Dict[str, str]] = {k: dict(v) for k, v in DEFAULT_PROFILES.items()}
    for key, value in stored.items():
        if not isinstance(value, dict):
            continue
        base = merged.get(key, {}).copy()
        for field in ("label", "link", "general", "section"):
            if field in value and isinstance(value[field], str):
                base[field] = value[field]
        merged[key] = base
    return merged


def load_profiles() -> Dict[str, Dict[str, str]]:
    # Start from public profiles (or defaults if file is missing/broken).
    if PROFILES_PATH.exists():
        try:
            with PROFILES_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    else:
        data = {}

    raw_profiles = data.get("profiles") if isinstance(data, dict) else None
    if isinstance(raw_profiles, dict):
        profiles = _merge_with_defaults(raw_profiles)
    else:
        profiles = {k: dict(v) for k, v in DEFAULT_PROFILES.items()}

    # Optional: local override file with personalized profiles.
    if PRIVATE_PROFILES_PATH.exists():
        try:
            with PRIVATE_PROFILES_PATH.open("r", encoding="utf-8") as f:
                private_data = json.load(f)
        except Exception:
            private_data = {}

        private_raw = private_data.get("profiles") if isinstance(private_data, dict) else None
        if isinstance(private_raw, dict):
            for key, value in private_raw.items():
                if not isinstance(value, dict):
                    continue
                base = profiles.get(key, {}).copy()
                for field in ("label", "link", "general", "section"):
                    if field in value and isinstance(value[field], str):
                        base[field] = value[field]
                profiles[key] = base

    return profiles


def save_profiles(profiles: Dict[str, Dict[str, str]]) -> None:
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"profiles": profiles}
    with PROFILES_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def get_profile(profile_key: str) -> Dict[str, str]:
    profiles = load_profiles()
    profile = profiles.get(profile_key) or {}

    # Fallbacks if fields are missing
    fallback = DEFAULT_PROFILES.get("web", {})
    label = profile.get("label") or fallback.get("label") or "Full Stack Developer"
    link = profile.get("link") or fallback.get("link") or ""
    general = profile.get("general") or fallback.get("general") or ""
    section = profile.get("section") or ""

    return {
        "label": str(label),
        "link": str(link),
        "general": str(general),
        "section": str(section),
    }


def select_profile_key(category: str, project: Dict[str, Any]) -> str:
    """Pick a profile key (web, mobile, coding) based on analysis category and text."""

    category = (category or "").lower()
    text = (project.get("description") or project.get("preview_description") or "")
    text_lower = text.lower()

    # Hybrid IT/business consulting, project management, and strategy roles.
    if category in {"consulting", "strategy", "projectmanagement", "productmanagement"} or any(
        kw in text_lower
        for kw in (
            "technology consultant",
            "technical project manager",
            "it project manager",
            "it strategy",
            "digital transformation",
            "business strategy",
            "stakeholder",
            "c-level",
            "executive",
            "global team",
            "bilingual",
            "multilingual",
        )
    ):
        return "hybrid"

    if category == "mobile" or any(
        kw in text_lower for kw in ("flutter", "android", "ios", "react native")
    ):
        return "mobile"

    if any(kw in text_lower for kw in ("odoo", "erp")):
        return "coding"

    if category in {"fullstack", "webdesign", "data", "devops"}:
        return "web"

    return "coding"
