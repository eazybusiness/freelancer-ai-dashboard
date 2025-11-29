import json
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

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = FastAPI(title="Freelance AI Dashboard")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _project_timestamp(project: Dict[str, Any]) -> Optional[int]:
    ts = project.get("time_submitted") or project.get("submitdate")
    if isinstance(ts, int):
        return ts
    try:
        return int(ts) if ts is not None else None
    except (TypeError, ValueError):
        return None


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

    filtered: List[Dict[str, Any]] = []
    for item in items:
        analysis = item.get("analysis") or {}
        score = analysis.get("rough_score")
        avg_budget = item.get("avg_budget")
        bid_count = item.get("bid_count")

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

        filtered.append(item)

    presets = sorted(
        {i.get("preset") for i in items if i.get("preset")},
    )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "items": filtered,
            "all_presets": presets,
            "active_preset": preset,
            "min_score": min_score,
            "min_budget": min_budget,
            "max_bids": max_bids,
            "active_page": "projects",
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
