import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from openai_client import generate_bid_for_project
from store import load_seen, save_seen
from generate_bids import (
    _select_profile_key,
    _build_profile,
    _determine_milestone_size_and_count,
)
from profiles import load_profiles, save_profiles

# Manual bid generator with learning
from manual_bid_generator import (
    generate_bid as manual_generate_bid,
    generate_multiple_versions,
    mark_bid_outcome,
    save_edited_bid,
    get_stats as get_learning_stats,
    PROJECT_TYPES,
    LANGUAGES,
    TONES,
)
from prompt_manager import (
    get_prompt_versions,
    set_active_prompt_version,
    approve_prompt_version,
)
from bid_history import (
    get_recent_bids,
    get_bid,
    get_winning_bids,
    get_successful_bids,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Dashboard behaviour constants
MAX_PROJECT_AGE_HOURS = 48  # hide projects older than this
MAX_VISIBLE_CARDS = 50      # maximum number of cards on the board
REFRESH_MAX_PROJECTS = 20   # max projects to analyze per refresh call

app = FastAPI(title="Freelance AI Dashboard")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_refresh_in_progress = False


def _project_timestamp(project: Dict[str, Any]) -> Optional[int]:
    ts = project.get("time_submitted") or project.get("submitdate")
    if isinstance(ts, int):
        return ts
    try:
        return int(ts) if ts is not None else None
    except (TypeError, ValueError):
        return None


def _load_config_presets() -> List[str]:
    """Return preset names from config/search_presets.json if available."""

    config_path = BASE_DIR / "config" / "search_presets.json"
    if not config_path.exists():
        return []
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    presets_obj = data.get("presets")
    if not isinstance(presets_obj, dict):
        return []

    names = [str(name) for name in presets_obj.keys()]
    return sorted(names)


def _load_shortlist_projects(shortlist_path: Path) -> Dict[int, Dict[str, Any]]:
    projects_by_id: Dict[int, Dict[str, Any]] = {}
    if not shortlist_path.exists():
        return projects_by_id
    try:
        with shortlist_path.open("r", encoding="utf-8") as sf:
            payload = json.load(sf)
    except Exception:
        return projects_by_id
    projects = payload.get("projects") or []
    if not isinstance(projects, list):
        return projects_by_id
    for p in projects:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        if isinstance(pid, int):
            projects_by_id[pid] = p
    return projects_by_id


def _collect_dashboard_items() -> List[Dict[str, Any]]:
    """Collect projects + analysis data from all analysis_*.json files.

    Each item contains:
    - id, title, seo_url, preset
    - project (raw API fields)
    - analysis (AI summary etc.)
    - status and has_bid from seen_projects.json
    - project_url, avg_budget, bid_count, timestamp
    """

    seen_store = load_seen()

    items_by_id: Dict[int, Dict[str, Any]] = {}

    if not DATA_DIR.exists():
        return []

    for analysis_path in DATA_DIR.glob("analysis_*.json"):
        try:
            with analysis_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            continue

        shortlist_input = payload.get("input")
        shortlist_projects: Dict[int, Dict[str, Any]] = {}
        preset = None
        if isinstance(shortlist_input, str) and shortlist_input:
            sp = (BASE_DIR / shortlist_input).resolve()
            shortlist_projects = _load_shortlist_projects(sp)
            # Derive preset name from filename like python_daily_shortlist.json
            stem = sp.stem
            if stem.endswith("_shortlist"):
                preset = stem[: -len("_shortlist")]
            else:
                preset = stem

        results = payload.get("results") or []
        if not isinstance(results, list):
            continue

        for item in results:
            if not isinstance(item, dict):
                continue
            pid = item.get("id")
            if not isinstance(pid, int):
                continue

            analysis = item.get("analysis") or {}

            # Prefer the richer project data from the original shortlist, but
            # merge in any fields that may have been stored alongside the
            # analysis (e.g. updated status fields). This ensures that fields
            # like `description` are always available for the dashboard modal.
            project_from_shortlist = shortlist_projects.get(pid) or {}
            if not isinstance(project_from_shortlist, dict):
                project_from_shortlist = {}

            project_from_analysis = item.get("project") or {}
            if not isinstance(project_from_analysis, dict):
                project_from_analysis = {}

            project: Dict[str, Any] = {
                **project_from_shortlist,
                **project_from_analysis,
            }

            title = item.get("title") or project.get("title") or "(no title)"
            seo_url = item.get("seo_url") or project.get("seo_url") or ""
            project_url = (
                f"https://www.freelancer.com/projects/{seo_url}"
                if isinstance(seo_url, str) and seo_url
                else ""
            )

            # Basic stats
            budget = project.get("budget") or {}
            avg_budget = None
            if isinstance(budget, dict):
                values = []
                for v in (budget.get("minimum"), budget.get("maximum")):
                    if isinstance(v, (int, float)):
                        values.append(float(v))
                if values:
                    avg_budget = sum(values) / len(values)

            bid_stats = project.get("bid_stats") or {}
            bid_count = None
            if isinstance(bid_stats, dict):
                bc = bid_stats.get("bid_count")
                if isinstance(bc, int):
                    bid_count = bc

            # Country / DACH region detection
            country_code = None
            country_name = None
            is_dach = False
            location = project.get("location") or {}
            if isinstance(location, dict):
                country = location.get("country") or {}
                if isinstance(country, dict):
                    cc = country.get("code")
                    cn = country.get("name")
                    if isinstance(cc, str) and cc:
                        country_code = cc
                    if isinstance(cn, str) and cn:
                        country_name = cn
                    code_upper = (cc or "").upper() if isinstance(cc, str) else ""
                    name_lower = (cn or "").lower() if isinstance(cn, str) else ""
                    if code_upper in {"DE", "AT", "CH"} or name_lower in {
                        "germany",
                        "austria",
                        "switzerland",
                    }:
                        is_dach = True

            status_info = seen_store.get(str(pid)) or {}
            status = status_info.get("status", "unknown")
            has_bid = bool(status_info.get("bid"))

            ts = _project_timestamp(project) or 0

            entry = {
                "id": pid,
                "title": title,
                "seo_url": seo_url,
                "project_url": project_url,
                "project": project,
                "analysis": analysis,
                "preset": preset or payload.get("preset"),
                "status": status,
                "has_bid": has_bid,
                "avg_budget": avg_budget,
                "bid_count": bid_count,
                "country_code": country_code,
                "country_name": country_name,
                "is_dach": is_dach,
                "timestamp": ts,
            }

            # If we already have this id from another file, keep the newer one.
            existing = items_by_id.get(pid)
            if existing is None or entry["timestamp"] >= existing.get("timestamp", 0):
                items_by_id[pid] = entry

    items = list(items_by_id.values())
    items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return items


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    preset: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    min_budget: Optional[float] = Query(None, ge=0),
    max_bids: Optional[int] = Query(None, ge=0),
):
    items = _collect_dashboard_items()

    # Filter by status, age, and user-specified filters.
    now_ts = int(datetime.now(timezone.utc).timestamp())
    max_age_seconds = MAX_PROJECT_AGE_HOURS * 3600 if MAX_PROJECT_AGE_HOURS else None

    filtered_all: List[Dict[str, Any]] = []
    for item in items:
        analysis = item.get("analysis") or {}
        score = analysis.get("rough_score")
        avg_budget = item.get("avg_budget")
        bid_count = item.get("bid_count")
        status = item.get("status")
        ts = item.get("timestamp") or 0

        # Hide projects that were explicitly archived.
        if status in {"bid_posted", "rejected"}:
            continue

        # Hide projects older than the max age.
        if max_age_seconds is not None and isinstance(ts, int) and ts > 0:
            if now_ts - ts > max_age_seconds:
                continue

        if preset and item.get("preset") != preset:
            continue
        if isinstance(min_score, int) and isinstance(score, int) and score < min_score:
            continue
        if (
            isinstance(min_budget, (int, float))
            and isinstance(avg_budget, (int, float))
            and avg_budget < min_budget
        ):
            continue
        if isinstance(max_bids, int) and isinstance(bid_count, int) and bid_count > max_bids:
            continue

        filtered_all.append(item)

    # Enforce card limit after all filters.
    limited_items = filtered_all[:MAX_VISIBLE_CARDS]

    # Presets to offer in the dropdown: prefer config-defined presets,
    # but fall back to those discovered in analysis items.
    config_presets = _load_config_presets()
    if config_presets:
        presets = config_presets
    else:
        presets = sorted({i.get("preset") for i in items if i.get("preset")})

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "items": limited_items,
            "all_presets": presets,
            "active_preset": preset,
            "min_score": min_score,
            "min_budget": min_budget,
            "max_bids": max_bids,
            "active_page": "projects",
            "total_items": len(filtered_all),
            "visible_items": len(limited_items),
            "max_visible": MAX_VISIBLE_CARDS,
        },
    )


@app.post("/api/generate-bid/{project_id}")
async def generate_bid(project_id: int) -> Dict[str, Any]:
    items = _collect_dashboard_items()
    item = next((i for i in items if i.get("id") == project_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Project not found")

    analysis = item.get("analysis") or {}
    project = item.get("project") or {}
    if not isinstance(project, dict) or not isinstance(analysis, dict):
        raise HTTPException(status_code=400, detail="Missing project or analysis data")

    profile_key = _select_profile_key(str(analysis.get("category", "")), project)
    profile = _build_profile(profile_key)
    ms = _determine_milestone_size_and_count(project)

    bid = generate_bid_for_project(
        project=project,
        analysis=analysis,
        profile=profile,
        milestone_size=ms["size"],
        milestone_count=ms["count"],
    )

    seen_store = load_seen()
    key = str(project_id)
    existing = seen_store.get(key) or {}
    existing.update(
        {
            "status": "bid_drafted",
            "analysis": analysis,
            "bid": bid,
        }
    )
    seen_store[key] = existing
    save_seen(seen_store)

    return {
        "ok": True,
        "project_id": project_id,
        "title": item.get("title"),
        "seo_url": item.get("seo_url"),
        "bid": bid,
    }


@app.get("/api/bid/{project_id}")
async def get_bid(project_id: int) -> Dict[str, Any]:
    seen_store = load_seen()
    entry = seen_store.get(str(project_id)) or {}
    bid = entry.get("bid")
    if not bid:
        raise HTTPException(status_code=404, detail="No bid stored for this project")

    return {
        "ok": True,
        "project_id": project_id,
        "bid": bid,
    }


@app.post("/api/refresh")
async def refresh(preset: str = Query(...)) -> Dict[str, Any]:
    """Run search + analysis for a given preset to fetch new projects.

    Uses the existing CLI tools (search_jobs.py and analyze_jobs.py) but limits
    the number of analyzed projects per call.
    """

    global _refresh_in_progress
    if _refresh_in_progress:
        raise HTTPException(status_code=409, detail="Refresh already in progress")
    if not preset:
        raise HTTPException(status_code=400, detail="Query parameter 'preset' is required")

    _refresh_in_progress = True
    try:
        shortlist_path = BASE_DIR / "data" / f"{preset}_shortlist.json"

        # 1) Run search_jobs.py to update the shortlist for this preset.
        search_cmd = [
            sys.executable,
            str(BASE_DIR / "search_jobs.py"),
            "--preset",
            preset,
            "--output-json",
            str(shortlist_path),
        ]
        search_proc = subprocess.run(
            search_cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )
        if search_proc.returncode != 0:
            msg = search_proc.stderr.strip() or search_proc.stdout.strip() or "search_jobs failed"
            raise HTTPException(status_code=500, detail=msg)

        # 2) Run analyze_jobs.py to apply phase 1 AI on new projects.
        analyze_cmd = [
            sys.executable,
            str(BASE_DIR / "analyze_jobs.py"),
            "--input-json",
            str(shortlist_path),
            "--max-projects",
            str(REFRESH_MAX_PROJECTS),
        ]
        analyze_proc = subprocess.run(
            analyze_cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )
        if analyze_proc.returncode != 0:
            msg = analyze_proc.stderr.strip() or analyze_proc.stdout.strip() or "analyze_jobs failed"
            raise HTTPException(status_code=500, detail=msg)

        return {"ok": True}
    finally:
        _refresh_in_progress = False


@app.post("/api/project/{project_id}/status")
async def update_project_status(project_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    status = payload.get("status")
    reason = payload.get("reason")
    if not isinstance(status, str) or not status:
        raise HTTPException(status_code=400, detail="Field 'status' is required")

    seen_store = load_seen()
    key = str(project_id)
    entry = seen_store.get(key) or {}

    entry["status"] = status
    if reason:
        entry["rejection_reason"] = str(reason)

    seen_store[key] = entry
    save_seen(seen_store)

    return {"ok": True}


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    profiles = load_profiles()
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "profiles": profiles,
            "active_page": "settings",
        },
    )


@app.post("/api/profiles")
async def update_profiles(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, dict):
        raise HTTPException(status_code=400, detail="Field 'profiles' must be an object")

    cleaned: Dict[str, Dict[str, str]] = {}
    for key, value in raw_profiles.items():
        if not isinstance(value, dict):
            continue
        cleaned[key] = {
            "label": str(value.get("label", "")).strip(),
            "link": str(value.get("link", "")).strip(),
            "general": str(value.get("general", "")),
            "section": str(value.get("section", "")),
        }

    if not cleaned:
        raise HTTPException(status_code=400, detail="At least one profile must be provided")

    save_profiles(cleaned)
    return {"ok": True}


@app.get("/manual-bid", response_class=HTMLResponse)
async def manual_bid_page(request: Request):
    """Page for manually pasting a project description and generating a bid."""
    profiles = load_profiles()
    prompt_versions = get_prompt_versions()
    recent_bids = get_recent_bids(limit=10)
    stats = get_learning_stats()
    
    return templates.TemplateResponse(
        "manual_bid.html",
        {
            "request": request,
            "profiles": profiles,
            "prompt_versions": prompt_versions,
            "project_types": PROJECT_TYPES,
            "languages": LANGUAGES,
            "tones": TONES,
            "recent_bids": recent_bids,
            "stats": stats,
            "active_page": "manual_bid",
        },
    )


@app.post("/api/manual-bid")
async def manual_bid_generate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a bid from a manually pasted project description using the new learning system."""
    description = payload.get("description", "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="Field 'description' is required")

    title = payload.get("title", "").strip() or "Untitled Project"
    url = payload.get("url", "").strip() or None
    project_type = payload.get("project_type", "other").strip()
    language = payload.get("language", "auto").strip()
    tone = payload.get("tone", "auto").strip()
    prompt_version = payload.get("prompt_version", "").strip() or None
    model = payload.get("model", "").strip() or None
    budget_min = payload.get("budget_min")
    budget_max = payload.get("budget_max")
    
    # Convert budget values
    if budget_min is not None:
        try:
            budget_min = float(budget_min)
        except (ValueError, TypeError):
            budget_min = None
    if budget_max is not None:
        try:
            budget_max = float(budget_max)
        except (ValueError, TypeError):
            budget_max = None

    result = manual_generate_bid(
        project_title=title,
        project_description=description,
        project_type=project_type,
        language=language,
        tone=tone,
        prompt_version=prompt_version,
        model=model,
        project_url=url,
        budget_min=budget_min,
        budget_max=budget_max,
    )

    return {
        "ok": True,
        "bid_id": result.get("bid_id"),
        "title": title,
        "proposal_text": result.get("bid_text", ""),
        "milestone_plan": result.get("milestone_plan", {}),
        "free_demo_offered": result.get("free_demo_offered", False),
        "free_demo_reason": result.get("free_demo_reason", ""),
        "detected_tone": result.get("detected_tone", ""),
        "detected_language": result.get("detected_language", ""),
        "prompt_version": result.get("prompt_version", ""),
        "model_used": result.get("model_used", ""),
        "identified_pain_point": result.get("identified_pain_point", ""),
    }


@app.post("/api/manual-bid/compare")
async def manual_bid_compare(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate bids using multiple prompt versions for comparison."""
    description = payload.get("description", "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="Field 'description' is required")
    
    title = payload.get("title", "").strip() or "Untitled Project"
    prompt_versions = payload.get("prompt_versions", [])
    
    if not prompt_versions or not isinstance(prompt_versions, list):
        raise HTTPException(status_code=400, detail="Field 'prompt_versions' must be a non-empty list")
    
    results = generate_multiple_versions(
        project_title=title,
        project_description=description,
        prompt_versions=prompt_versions,
        project_type=payload.get("project_type", "other"),
        language=payload.get("language", "auto"),
        tone=payload.get("tone", "auto"),
        project_url=payload.get("url"),
        budget_min=payload.get("budget_min"),
        budget_max=payload.get("budget_max"),
    )
    
    return {"ok": True, "results": results}


# ----- Bid History & Learning API -----

@app.get("/api/bids")
async def api_get_bids(
    limit: int = Query(default=20, le=100),
    outcome: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Get recent bids, optionally filtered by outcome."""
    if outcome:
        from bid_history import get_bids_by_outcome
        bids = get_bids_by_outcome(outcome, limit=limit)
    else:
        bids = get_recent_bids(limit=limit)
    
    return {"ok": True, "bids": bids}


@app.get("/api/bids/{bid_id}")
async def api_get_bid(bid_id: int) -> Dict[str, Any]:
    """Get a single bid by ID."""
    bid = get_bid(bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    return {"ok": True, "bid": bid}


@app.post("/api/bids/{bid_id}/outcome")
async def api_update_bid_outcome(bid_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update the outcome of a bid for learning."""
    outcome = payload.get("outcome", "pending")
    was_viewed = payload.get("was_viewed", False)
    was_engaged = payload.get("was_engaged", False)
    was_won = payload.get("was_won", False)
    was_high_rank = payload.get("was_high_rank", False)
    notes = payload.get("notes")
    
    success = mark_bid_outcome(
        bid_id=bid_id,
        outcome=outcome,
        was_viewed=was_viewed,
        was_engaged=was_engaged,
        was_won=was_won,
        was_high_rank=was_high_rank,
        notes=notes,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    return {"ok": True}


@app.post("/api/bids/{bid_id}/final")
async def api_save_final_bid(bid_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save the final edited version of a bid."""
    final_text = payload.get("final_text", "").strip()
    if not final_text:
        raise HTTPException(status_code=400, detail="Field 'final_text' is required")
    
    feedback = payload.get("feedback")
    
    success = save_edited_bid(bid_id, final_text, feedback)
    if not success:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    return {"ok": True}


@app.get("/api/bids/winning")
async def api_get_winning_bids(limit: int = Query(default=20, le=50)) -> Dict[str, Any]:
    """Get winning bids for learning reference."""
    bids = get_winning_bids(limit=limit)
    return {"ok": True, "bids": bids}


@app.get("/api/learning-stats")
async def api_get_learning_stats() -> Dict[str, Any]:
    """Get learning statistics."""
    stats = get_learning_stats()
    return {"ok": True, "stats": stats}


# ----- Prompt Version Management API -----

@app.get("/api/prompt-versions")
async def api_get_prompt_versions() -> Dict[str, Any]:
    """Get all prompt versions with their stats."""
    versions = get_prompt_versions()
    return {"ok": True, "versions": versions}


@app.post("/api/prompt-versions/{version_key}/activate")
async def api_activate_prompt_version(version_key: str) -> Dict[str, Any]:
    """Set a prompt version as active."""
    success = set_active_prompt_version(version_key)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return {"ok": True}


@app.post("/api/prompt-versions/{version_key}/approve")
async def api_approve_prompt_version(version_key: str) -> Dict[str, Any]:
    """Mark a prompt version as approved."""
    success = approve_prompt_version(version_key)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return {"ok": True}


@app.get("/api/prompt-versions/{version_key}/content")
async def api_get_prompt_content(version_key: str) -> Dict[str, Any]:
    """Get the full content of a prompt version."""
    from prompt_manager import load_prompt
    content = load_prompt(version_key)
    if content is None:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return {"ok": True, "content": content}


@app.put("/api/prompt-versions/{version_key}")
async def api_update_prompt_version(version_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update a prompt version's content and metadata."""
    from prompt_manager import PROMPTS_DIR
    import re
    
    name = payload.get("name", "").strip()
    description = payload.get("description", "").strip()
    content = payload.get("content", "").strip()
    
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
    
    # Find the file
    safe_key = re.sub(r'[^a-zA-Z0-9_-]', '_', version_key)
    file_path = PROMPTS_DIR / f"{safe_key}.md"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Prompt version not found")
    
    # Update the header metadata in the content
    lines = content.split("\n")
    new_lines = []
    metadata_updated = {"version": False, "name": False, "description": False}
    
    for line in lines:
        if line.startswith("# Prompt Version:") and not metadata_updated["version"]:
            new_lines.append(f"# Prompt Version: {version_key}")
            metadata_updated["version"] = True
        elif line.startswith("# Name:") and not metadata_updated["name"]:
            new_lines.append(f"# Name: {name}")
            metadata_updated["name"] = True
        elif line.startswith("# Description:") and not metadata_updated["description"]:
            new_lines.append(f"# Description: {description}")
            metadata_updated["description"] = True
        else:
            new_lines.append(line)
    
    final_content = "\n".join(new_lines)
    
    # Write file
    file_path.write_text(final_content, encoding="utf-8")
    
    # Update database
    from bid_history import register_prompt_version
    register_prompt_version(
        version_key=version_key,
        name=name,
        description=description,
    )
    
    return {"ok": True}


@app.post("/api/prompt-versions")
async def api_create_prompt_version(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new prompt version."""
    from prompt_manager import create_prompt_version
    
    version_key = payload.get("version_key", "").strip()
    name = payload.get("name", "").strip()
    description = payload.get("description", "").strip()
    content = payload.get("content", "").strip()
    
    if not version_key or not name:
        raise HTTPException(status_code=400, detail="version_key and name are required")
    
    success = create_prompt_version(
        version_key=version_key,
        name=name,
        description=description,
        content=content,
        status="testing"
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create prompt version")
    
    return {"ok": True}


# ----- Prompt Editor Page -----

@app.get("/prompt-editor", response_class=HTMLResponse)
async def prompt_editor_page(request: Request):
    """Page for editing prompt versions."""
    prompt_versions = get_prompt_versions()
    
    return templates.TemplateResponse(
        "prompt_editor.html",
        {
            "request": request,
            "prompt_versions": prompt_versions,
            "active_page": "prompt_editor",
        },
    )


# ----- Bid History Page -----

@app.get("/bid-history", response_class=HTMLResponse)
async def bid_history_page(request: Request):
    """Page for viewing and managing bid history."""
    recent_bids = get_recent_bids(limit=50)
    winning_bids = get_winning_bids(limit=10)
    stats = get_learning_stats()
    prompt_versions = get_prompt_versions()
    
    return templates.TemplateResponse(
        "bid_history.html",
        {
            "request": request,
            "recent_bids": recent_bids,
            "winning_bids": winning_bids,
            "stats": stats,
            "prompt_versions": prompt_versions,
            "active_page": "bid_history",
        },
    )
