# Freelancer AI Dashboard

The must-have tool for busy freelancers. It pulls the latest job offers from Freelancer.com, rates and summarizes them, highlights risks and opportunities, and, when you decide to bid, drafts a tailored proposal based on your saved profiles and portfolio links. You can maintain multiple profiles for different skills and roles.

## What this project showcases

- **API integration & automation**: end-to-end pipeline that talks to the Freelancer.com API, filters and scores projects, and calls OpenAI for analysis and bid generation.
- **AI prompt engineering**: separate, editable prompts for analysis and bid drafting, with structured JSON outputs and robust parsing.
- **Config-driven design**: search presets and freelancer profiles are stored in JSON and editable from the browser-based settings UI.
- **Web dashboard**: FastAPI + Jinja2 dashboard to review analyzed projects, highlight top opportunities, and trigger bid generation on demand.
- **Production readiness (single-user)**: `.env`-based configuration, virtualenv support, cron-friendly scripts, and a systemd service option for the dashboard.

## Prerequisites

- Python 3.10+ installed.
- A virtual environment is recommended:

  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

- Copy the example environment file and fill in your own keys:

  ```bash
  cp .env.example .env
  # then edit .env with your Freelancer, OpenAI and SMTP credentials
  ```

- Install Python dependencies:

  ```bash
  cd freelance_api  # or the directory where you cloned this repo
  pip install -r requirements.txt
  ```

## 1. Search for projects

Use `search_jobs.py` with a preset (recommended):

```bash
python3 search_jobs.py \
  --preset python_daily \
  --output-json data/python_daily_shortlist.json
```

Other presets (from `config/search_presets.json`):

- `fullstack_daily`
- `python_daily`
- `mobile_daily`

This writes a shortlist JSON with new (not yet seen) projects.

## 2. Analyze shortlisted projects with OpenAI

```bash
python3 analyze_jobs.py \
  --input-json data/python_daily_shortlist.json \
  --output-json data/analysis_python_daily_shortlist.json \
  --max-projects 20
```

This calls a cheap OpenAI model (e.g. gpt-3.5) to produce:

- Summary
- Category
- Rough suitability score (0–100)
- Automation potential (0–100)
- Manual work notes, reasons, risks

Results are saved into the `results` list inside the analysis JSON.

## 3. Generate bid drafts and milestone plans

```bash
python3 generate_bids.py \
  --input-json data/analysis_python_daily_shortlist.json \
  --max-projects 3 \
  --min-score 60 \
  --notify-email
```

Options:

- `--max-projects`: limit how many top projects to create bids for.
- `--min-score`: only consider projects with `rough_score >= min-score`.
- `--model`: override the expensive model (default `gpt-4.1-mini` or env).
- `--notify-email`: send an email summary (requires SMTP/NOTIFICATION env vars).

Output JSON (e.g. `data/bids_analysis_python_daily_shortlist.json`) contains:

- Original project and analysis data
- `bid.proposal_text`: ready-to-paste proposal
- `bid.milestone_plan`: size, count, and milestone titles/descriptions
- `bid.free_demo_offered` and `bid.free_demo_reason`

## 4. Email notifications

`generate_bids.py` uses `email_notifier.py` when `--notify-email` is passed.

- Sender account is taken from `SMTP_*` variables in `.env`.
- Recipient is `NOTIFICATION_EMAIL`.
- The bids JSON file is attached to the email.

## 5. Cron-based automation

There is a helper script to run the full pipeline for all three presets:

```bash
./run_pipeline_once.sh
```

This script does, for each of `python_daily`, `fullstack_daily`, `mobile_daily`:

1. `search_jobs.py --preset ... --output-json data/..._shortlist.json`
2. `analyze_jobs.py --input-json ... --output-json data/analysis_..._shortlist.json`
3. `generate_bids.py --input-json ... --max-projects 3 --min-score 60 --notify-email`

You can schedule it in your user crontab, for example:

```cron
# Mon–Fri, every 30 minutes from 06:00 to 17:30
*/30 6-17 * * 1-5 /path/to/freelance_api/run_pipeline_once.sh >> /path/to/freelance_api/logs/pipeline.log 2>&1

# Saturday at 06:00
0 6 * * 6 /path/to/freelance_api/run_pipeline_once.sh >> /path/to/freelance_api/logs/pipeline.log 2>&1
```

## 6. Seen project tracking

The file `data/seen_projects.json` tracks project IDs and their status to avoid re-processing the same projects and wasting API/AI calls.

Statuses include, for example:

- `seen_only`
- `analyzed`
- `bid_drafted`

## 7. Web dashboard

In addition to the CLI pipeline, the project includes a FastAPI web dashboard to review and act on analyzed projects:

- Filter by preset, score and budget.
- Highlight DACH / high-scoring projects.
- Quickly mark projects as posted / rejected with reasons.
- Open a modal to see full AI analysis, manual work notes and risks.
- Trigger Phase 2 bid generation from the browser and view/update stored bids.

Run the dashboard locally with Uvicorn:

```bash
uvicorn dashboard:app --reload
```

Or, for a long-running local service, configure a small `systemd` unit pointing at your virtualenv’s `python3` and `uvicorn dashboard:app`.

## 8. Development notes

- All prompts are in `prompts/` and can be edited to tweak AI behavior.
- Search presets live in `config/search_presets.json`.
- Profile definitions live in `config/profiles.json` and are also editable via the `/settings` page in the dashboard.
- The Freelancer API client is in `freelancer_client.py`.
- The OpenAI client and prompt loading logic are in `openai_client.py`.
