import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from freelancer_client import FreelancerClient
from store import load_seen, save_seen


PRESETS_PATH = Path(__file__).resolve().parent / "config" / "search_presets.json"


def _parse_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_presets() -> Dict[str, Dict[str, Any]]:
    """Load search presets from config/search_presets.json if it exists."""
    if not PRESETS_PATH.exists():
        return {}
    try:
        with PRESETS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    presets = data.get("presets")
    if not isinstance(presets, dict):
        return {}
    return presets


def _format_age(time_submitted: Optional[int]) -> str:
    if not time_submitted:
        return "unknown"
    try:
        dt = datetime.fromtimestamp(int(time_submitted), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return "unknown"
    now = datetime.now(timezone.utc)
    delta = now - dt
    if delta < timedelta(minutes=1):
        return "just now"
    if delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() // 60)
        return f"{minutes} min ago"
    if delta < timedelta(days=1):
        hours = int(delta.total_seconds() // 3600)
        return f"{hours} h ago"
    days = delta.days
    return f"{days} d ago"


def _project_bid_count(project: Dict[str, Any]) -> Optional[int]:
    bid_stats = project.get("bid_stats")
    if isinstance(bid_stats, dict):
        bid_count = bid_stats.get("bid_count")
        if isinstance(bid_count, int):
            return bid_count
    return None


def _project_avg_budget(project: Dict[str, Any]) -> Optional[float]:
    budget = project.get("budget")
    if not isinstance(budget, dict):
        return None
    minimum = budget.get("minimum")
    maximum = budget.get("maximum")
    values: List[float] = []
    for v in (minimum, maximum):
        if isinstance(v, (int, float)):
            values.append(float(v))
    if not values:
        return None
    return sum(values) / len(values)


def _project_country(project: Dict[str, Any]) -> Optional[str]:
    location = project.get("location")
    if not isinstance(location, dict):
        return None
    country = location.get("country")
    if not isinstance(country, dict):
        return None
    code = country.get("code")
    name = country.get("name")
    if isinstance(code, str) and code:
        return code
    if isinstance(name, str) and name:
        return name
    return None


def _filter_projects(
    projects: Iterable[Dict[str, Any]],
    allowed_countries: Optional[List[str]],
    min_budget: Optional[float],
    max_budget: Optional[float],
    posted_within_hours: Optional[int],
    min_bids: Optional[int],
    max_bids: Optional[int],
    required_skills: Optional[List[str]],
) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    cutoff: Optional[datetime] = None
    if posted_within_hours is not None and posted_within_hours > 0:
        cutoff = now - timedelta(hours=posted_within_hours)

    normalized_skills: List[str] = []
    if required_skills:
        normalized_skills = [s.lower() for s in required_skills]

    filtered: List[Dict[str, Any]] = []

    # Normalize allowed country codes to upper-case for comparison.
    allowed_codes = None
    if allowed_countries:
        allowed_codes = {c.upper() for c in allowed_countries if isinstance(c, str)}

    for project in projects:
        avg_budget = _project_avg_budget(project)
        if min_budget is not None and avg_budget is not None and avg_budget < min_budget:
            continue
        if max_budget is not None and avg_budget is not None and avg_budget > max_budget:
            continue

        bid_count = _project_bid_count(project)
        if min_bids is not None and bid_count is not None and bid_count < min_bids:
            continue
        if max_bids is not None and bid_count is not None and bid_count > max_bids:
            continue

        if cutoff is not None:
            ts = project.get("time_submitted") or project.get("submitdate")
            if ts is not None:
                try:
                    dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
                except (TypeError, ValueError, OSError):
                    dt = None
                if dt is not None and dt < cutoff:
                    continue

        # Exclude projects that are marked as Preferred Freelancer only,
        # based on common upgrade flags in the response.
        upgrades = project.get("upgrades")
        if isinstance(upgrades, dict):
            pf_only = upgrades.get("pf_only") or upgrades.get("preferred_freelancer_only")
            if pf_only:
                continue

        # Enforce allowed employer countries client-side, if any are provided.
        if allowed_codes is not None:
            location = project.get("location")
            if isinstance(location, dict):
                country_info = location.get("country")
                if isinstance(country_info, dict):
                    code = country_info.get("code")
                    if isinstance(code, str) and code:
                        if code.upper() not in allowed_codes:
                            continue

        if normalized_skills:
            jobs = project.get("jobs") or []
            if not isinstance(jobs, list):
                jobs = []
            job_names: List[str] = []
            for job in jobs:
                if not isinstance(job, dict):
                    continue
                name = job.get("name") or job.get("seo_url")
                if isinstance(name, str):
                    job_names.append(name.lower())
            if job_names:
                if not any(
                    any(skill in job_name for job_name in job_names)
                    for skill in normalized_skills
                ):
                    continue

        filtered.append(project)

    return filtered


def _project_timestamp(project: Dict[str, Any]) -> Optional[datetime]:
    ts = project.get("time_submitted") or project.get("submitdate")
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _print_projects(projects: Iterable[Dict[str, Any]]) -> None:
    projects_list = list(projects)
    projects_list.sort(
        key=lambda p: _project_timestamp(p) or datetime.fromtimestamp(0, tz=timezone.utc),
        reverse=True,
    )

    now = datetime.now(timezone.utc)

    for project in projects_list:
        project_id = project.get("id")
        title = project.get("title") or ""
        currency = ""
        budget = project.get("budget")
        budget_str = ""
        if isinstance(budget, dict):
            currency_dict = budget.get("currency")
            if isinstance(currency_dict, dict):
                code = currency_dict.get("code")
                if isinstance(code, str):
                    currency = code
            minimum = budget.get("minimum")
            maximum = budget.get("maximum")
            if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)):
                budget_str = f"{minimum:.0f}-{maximum:.0f}"
            elif isinstance(minimum, (int, float)):
                budget_str = f"from {minimum:.0f}"
            elif isinstance(maximum, (int, float)):
                budget_str = f"up to {maximum:.0f}"

        ts = _project_timestamp(project)
        is_new = False
        if ts is not None:
            is_new = (now - ts) <= timedelta(minutes=15)

        bid_count = _project_bid_count(project)
        age = _format_age(project.get("time_submitted") or project.get("submitdate"))

        # Determine country and whether it's in the DACH region.
        country = ""
        location = project.get("location")
        if isinstance(location, dict):
            country_info = location.get("country")
            if isinstance(country_info, dict):
                country_code = country_info.get("code")
                country_name = country_info.get("name")
                if isinstance(country_code, str) and country_code:
                    country = country_code
                elif isinstance(country_name, str) and country_name:
                    country = country_name
                is_dach = False
                if isinstance(country_code, str) and country_code in {"DE", "AT", "CH"}:
                    is_dach = True
                elif isinstance(country_name, str) and country_name.lower() in {
                    "germany",
                    "austria",
                    "switzerland",
                }:
                    is_dach = True
            else:
                is_dach = False
        else:
            is_dach = False

        header_parts: List[str] = []
        if is_new:
            header_parts.append("NEW")
        if is_dach:
            header_parts.append("DACH")
        if currency and budget_str:
            header_parts.append(f"{currency} {budget_str}")
        if bid_count is not None:
            header_parts.append(f"{bid_count} bids")
        if age != "unknown":
            header_parts.append(age)
        if country:
            header_parts.append(country)

        header = " | ".join(header_parts)
        print(f"[{project_id}] {title}")
        if header:
            print(f"    {header}")
        url = project.get("seo_url")
        if isinstance(url, str) and url:
            print(f"    https://www.freelancer.com/projects/{url}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search Freelancer projects with filters.",
    )
    parser.add_argument(
        "--preset",
        help=(
            "Name of search preset defined in config/search_presets.json. "
            "Command-line options override preset values."
        ),
    )
    parser.add_argument(
        "--query",
        "-q",
        help="Search query (keywords).",
    )
    parser.add_argument(
        "--countries",
        help="Comma-separated list of ISO 2 country codes, e.g. US,CA.",
    )
    parser.add_argument(
        "--languages",
        help="Comma-separated list of language codes, e.g. en,de.",
    )
    parser.add_argument(
        "--skills",
        help="Comma-separated list of skill names to match against project jobs.",
    )
    parser.add_argument(
        "--min-budget",
        type=float,
        help="Minimum average budget.",
    )
    parser.add_argument(
        "--max-budget",
        type=float,
        help="Maximum average budget.",
    )
    parser.add_argument(
        "--posted-within-hours",
        type=int,
        help="Only include projects posted within this many hours.",
    )
    parser.add_argument(
        "--min-bids",
        type=int,
        help="Minimum current bid count.",
    )
    parser.add_argument(
        "--max-bids",
        type=int,
        help="Maximum current bid count.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Number of projects per API page (default: 50).",
    )
    parser.add_argument(
        "--pages",
        type=int,
        help="Number of pages to fetch (default: 1).",
    )
    parser.add_argument(
        "--output-json",
        help="Write shortlisted (new) projects to the given JSON file.",
    )

    # First parse to see if a preset was requested.
    initial_args, _ = parser.parse_known_args()
    if initial_args.preset:
        presets = _load_presets()
        preset = presets.get(initial_args.preset)
        if preset is None:
            parser.error(
                f"Preset '{initial_args.preset}' not found in config/search_presets.json"
            )

        preset_defaults: Dict[str, Any] = {}
        if "query" in preset:
            preset_defaults["query"] = preset["query"]
        if "countries" in preset and isinstance(preset["countries"], list):
            preset_defaults["countries"] = ",".join(preset["countries"])
        if "languages" in preset and isinstance(preset["languages"], list):
            preset_defaults["languages"] = ",".join(preset["languages"])
        if "skills" in preset and isinstance(preset["skills"], list):
            preset_defaults["skills"] = ",".join(preset["skills"])
        for key in (
            "min_budget",
            "max_budget",
            "posted_within_hours",
            "min_bids",
            "max_bids",
            "limit",
            "pages",
        ):
            if key in preset:
                preset_defaults[key.replace("_", "-") if "_" in key else key] = preset[key]

        # Map JSON keys to argparse dest names.
        if "min_budget" in preset:
            preset_defaults["min_budget"] = preset["min_budget"]
        if "max_budget" in preset:
            preset_defaults["max_budget"] = preset["max_budget"]
        if "posted_within_hours" in preset:
            preset_defaults["posted_within_hours"] = preset["posted_within_hours"]
        if "min_bids" in preset:
            preset_defaults["min_bids"] = preset["min_bids"]
        if "max_bids" in preset:
            preset_defaults["max_bids"] = preset["max_bids"]
        if "limit" in preset:
            preset_defaults["limit"] = preset["limit"]
        if "pages" in preset:
            preset_defaults["pages"] = preset["pages"]

        parser.set_defaults(**preset_defaults)

    args = parser.parse_args()

    countries = _parse_csv(args.countries)
    languages = _parse_csv(args.languages)
    skills = _parse_csv(args.skills)

    seen = load_seen()

    client = FreelancerClient()

    per_page = args.limit if args.limit is not None else 50
    pages = args.pages if args.pages is not None else 1

    all_projects: List[Dict[str, Any]] = []
    offset = 0
    for _ in range(max(pages, 1)):
        projects = client.search_projects(
            query=args.query,
            languages=languages or None,
            countries=countries or None,
            jobs=None,
            limit=per_page,
            offset=offset,
        )
        if not projects:
            break
        all_projects.extend(projects)
        offset += per_page

    filtered = _filter_projects(
        all_projects,
        countries or None,
        min_budget=args.min_budget,
        max_budget=args.max_budget,
        posted_within_hours=args.posted_within_hours,
        min_bids=args.min_bids,
        max_bids=args.max_bids,
        required_skills=skills or None,
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    new_projects: List[Dict[str, Any]] = []
    for project in filtered:
        project_id = project.get("id")
        if not isinstance(project_id, int):
            continue
        key = str(project_id)
        if key in seen:
            continue
        new_projects.append(project)
        if key not in seen:
            seen[key] = {"status": "seen_only", "last_updated": now_iso}

    output_path = args.output_json
    if output_path and new_projects:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": now_iso,
            "preset": args.preset,
            "query": args.query,
            "count": len(new_projects),
            "projects": new_projects,
        }
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    save_seen(seen)

    _print_projects(new_projects)


if __name__ == "__main__":
    main()
