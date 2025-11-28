import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from openai_client import analyze_project_with_gpt35
from store import load_seen, save_seen


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze shortlisted Freelancer projects with a cheap OpenAI model "
            "(summary, category, rough score)."
        ),
    )
    parser.add_argument(
        "--input-json",
        required=True,
        help="Path to the shortlist JSON file produced by search_jobs.py.",
    )
    parser.add_argument(
        "--output-json",
        help="Path to write analysis results as JSON (default: data/analysis_<input>.json).",
    )
    parser.add_argument(
        "--max-projects",
        type=int,
        default=20,
        help="Maximum number of projects to analyze in this run (default: 20).",
    )
    parser.add_argument(
        "--model",
        help="Override cheap model name (default: OPENAI_CHEAP_MODEL or gpt-3.5-turbo).",
    )

    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.exists():
        raise SystemExit(f"Input JSON not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    projects: List[Dict[str, Any]] = payload.get("projects") or []
    if not isinstance(projects, list):
        raise SystemExit("Input JSON does not contain a 'projects' list.")

    seen = load_seen()
    now_iso = datetime.now(timezone.utc).isoformat()

    analyzed_results: List[Dict[str, Any]] = []

    count = 0
    for project in projects:
        project_id = project.get("id")
        if not isinstance(project_id, int):
            continue
        key = str(project_id)

        # Skip if beyond max limit.
        if count >= args.max_projects:
            break

        existing = seen.get(key) or {}
        status = existing.get("status")
        previous_analysis = existing.get("analysis") or {}
        previous_score = previous_analysis.get("rough_score")
        previous_reasons = previous_analysis.get("reasons") or ""

        # If we have a prior successful analysis, skip. If the previous
        # analysis was a parsing fallback (rough_score == 0 and reasons
        # mention non-JSON), allow re-analysis.
        if status in {"analyzed", "bid_drafted", "bid_sent"}:
            if not (
                isinstance(previous_score, int)
                and previous_score == 0
                and "non-JSON" in str(previous_reasons)
            ):
                continue

        ai_result = analyze_project_with_gpt35(project, model=args.model)
        analyzed_results.append(
            {
                "id": project_id,
                "title": project.get("title"),
                "seo_url": project.get("seo_url"),
                "project": project,
                "analysis": ai_result,
            }
        )

        seen[key] = {
            "status": "analyzed",
            "last_updated": now_iso,
            "analysis": ai_result,
        }
        count += 1

    save_seen(seen)

    if not analyzed_results:
        print("No projects analyzed (either none in input or all already analyzed / limit reached).")
        return

    # Determine default output path if not provided.
    if args.output_json:
        out_path = Path(args.output_json)
    else:
        out_dir = Path("data")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"analysis_{input_path.stem}.json"

    result_payload: Dict[str, Any] = {
        "generated_at": now_iso,
        "input": str(input_path),
        "count": len(analyzed_results),
        "results": analyzed_results,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result_payload, f, ensure_ascii=False, indent=2)

    print(f"Analyzed {len(analyzed_results)} projects. Results written to {out_path}.")


if __name__ == "__main__":
    main()
