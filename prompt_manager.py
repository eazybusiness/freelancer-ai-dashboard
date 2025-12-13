"""
Prompt Version Manager - Load, list, and manage bid prompt versions.

Handles:
- Loading prompts from prompts/bid_versions/
- Parsing metadata from prompt headers
- Registering versions in the database
- Selecting prompts for generation
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from bid_history import (
    register_prompt_version,
    get_prompt_versions as db_get_prompt_versions,
    get_active_prompt_version,
    set_active_prompt_version as db_set_active,
    approve_prompt_version as db_approve,
)

BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts" / "bid_versions"
LEGACY_PROMPT_PATH = BASE_DIR / "prompts" / "bid_prompt.md"


def _parse_prompt_metadata(content: str) -> Dict[str, str]:
    """Extract metadata from prompt file header comments."""
    metadata = {
        "version_key": "",
        "name": "",
        "description": "",
        "status": "testing",
    }
    
    lines = content.split("\n")
    for line in lines[:20]:  # Only check first 20 lines
        line = line.strip()
        if not line.startswith("#"):
            continue
        
        line = line.lstrip("#").strip()
        
        if line.startswith("Prompt Version:"):
            metadata["version_key"] = line.replace("Prompt Version:", "").strip()
        elif line.startswith("Name:"):
            metadata["name"] = line.replace("Name:", "").strip()
        elif line.startswith("Description:"):
            metadata["description"] = line.replace("Description:", "").strip()
        elif line.startswith("Status:"):
            metadata["status"] = line.replace("Status:", "").strip()
    
    return metadata


def discover_prompt_versions() -> List[Dict[str, Any]]:
    """Discover all prompt versions from the prompts/bid_versions/ directory."""
    versions = []
    
    if not PROMPTS_DIR.exists():
        PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        return versions
    
    for file_path in sorted(PROMPTS_DIR.glob("*.md")):
        try:
            content = file_path.read_text(encoding="utf-8")
            metadata = _parse_prompt_metadata(content)
            
            if not metadata["version_key"]:
                # Use filename as fallback
                metadata["version_key"] = file_path.stem
            
            if not metadata["name"]:
                metadata["name"] = file_path.stem.replace("_", " ").title()
            
            versions.append({
                "version_key": metadata["version_key"],
                "name": metadata["name"],
                "description": metadata["description"],
                "status": metadata["status"],
                "file_path": str(file_path),
                "is_approved": metadata["status"] == "approved",
            })
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
    
    return versions


def sync_prompt_versions_to_db() -> int:
    """Sync discovered prompt versions to the database. Returns count of synced versions."""
    versions = discover_prompt_versions()
    
    for v in versions:
        register_prompt_version(
            version_key=v["version_key"],
            name=v["name"],
            description=v["description"],
            is_active=False,
            is_approved=v["is_approved"],
        )
    
    # If no active version, set the first approved one as active
    active = get_active_prompt_version()
    if not active and versions:
        approved = [v for v in versions if v["is_approved"]]
        if approved:
            db_set_active(approved[0]["version_key"])
        else:
            db_set_active(versions[0]["version_key"])
    
    return len(versions)


def get_prompt_versions() -> List[Dict[str, Any]]:
    """Get all prompt versions with their stats from DB, enriched with file info."""
    # First sync files to DB
    sync_prompt_versions_to_db()
    
    # Get from DB (includes stats)
    db_versions = db_get_prompt_versions()
    
    # Enrich with file paths
    file_versions = {v["version_key"]: v for v in discover_prompt_versions()}
    
    for v in db_versions:
        if v["version_key"] in file_versions:
            v["file_path"] = file_versions[v["version_key"]]["file_path"]
        else:
            v["file_path"] = None
    
    return db_versions


def load_prompt(version_key: str) -> Optional[str]:
    """Load a prompt by version key."""
    versions = discover_prompt_versions()
    
    for v in versions:
        if v["version_key"] == version_key:
            file_path = Path(v["file_path"])
            if file_path.exists():
                return file_path.read_text(encoding="utf-8")
    
    return None


def load_active_prompt() -> tuple[str, str]:
    """Load the currently active prompt. Returns (version_key, content)."""
    sync_prompt_versions_to_db()
    
    active_key = get_active_prompt_version()
    
    if active_key:
        content = load_prompt(active_key)
        if content:
            return active_key, content
    
    # Fallback to legacy prompt
    if LEGACY_PROMPT_PATH.exists():
        return "legacy", LEGACY_PROMPT_PATH.read_text(encoding="utf-8")
    
    # Final fallback
    return "fallback", _get_fallback_prompt()


def set_active_prompt_version(version_key: str) -> bool:
    """Set a prompt version as active."""
    versions = discover_prompt_versions()
    valid_keys = [v["version_key"] for v in versions]
    
    if version_key not in valid_keys:
        return False
    
    return db_set_active(version_key)


def approve_prompt_version(version_key: str) -> bool:
    """Mark a prompt version as approved."""
    return db_approve(version_key)


def create_prompt_version(
    version_key: str,
    name: str,
    description: str,
    content: str,
    status: str = "testing",
) -> bool:
    """Create a new prompt version file."""
    # Ensure directory exists
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sanitize version key for filename
    safe_key = re.sub(r'[^a-zA-Z0-9_-]', '_', version_key)
    file_path = PROMPTS_DIR / f"{safe_key}.md"
    
    # Add metadata header
    header = f"""# Prompt Version: {version_key}
# Name: {name}
# Description: {description}
# Status: {status}

"""
    
    full_content = header + content
    file_path.write_text(full_content, encoding="utf-8")
    
    # Register in DB
    register_prompt_version(
        version_key=version_key,
        name=name,
        description=description,
        is_active=False,
        is_approved=status == "approved",
    )
    
    return True


def _get_fallback_prompt() -> str:
    """Minimal fallback prompt if nothing else is available."""
    return """You are generating a JSON object with a freelance project proposal.

Project: {PROJECT_TITLE}
Description: {PROJECT_DESCRIPTION}

Write a professional proposal (900-1200 characters) that shows you understood the project.

Output JSON:
{
  "proposal_text": "...",
  "milestone_plan": {"size": "{MILESTONE_SIZE}", "count": {MILESTONE_COUNT}, "milestones": []},
  "free_demo_offered": false,
  "free_demo_reason": ""
}
"""
