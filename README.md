# Freelance Job Search & Bid Assistant

This project automates searching for projects on Freelancer.com, analyzing them with OpenAI, and drafting proposal texts and milestone plans. You can run each stage manually or via cron.

## Prerequisites

- Python 3.10+ installed.
- `.env` file in the project root with at least:

  ```bash
  FREELANCER_OAUTH_TOKEN=...
  OPENAI_API_KEY=...
  # optional for email notifications
  SMTP_SERVER=...
  SMTP_PORT=587
  SMTP_USERNAME=...
  SMTP_PASSWORD=...
  NOTIFICATION_EMAIL=...
  ```

- Install Python dependencies:

  ```bash
  cd /home/nop/CascadeProjects/freelance_api
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
*/30 6-17 * * 1-5 /home/nop/CascadeProjects/freelance_api/run_pipeline_once.sh >> /home/nop/CascadeProjects/freelance_api/logs/pipeline.log 2>&1

# Saturday at 06:00
0 6 * * 6 /home/nop/CascadeProjects/freelance_api/run_pipeline_once.sh >> /home/nop/CascadeProjects/freelance_api/logs/pipeline.log 2>&1
```

## 6. Seen project tracking

The file `data/seen_projects.json` tracks project IDs and their status to avoid re-processing the same projects and wasting API/AI calls.

Statuses include, for example:

- `seen_only`
- `analyzed`
- `bid_drafted`

## 7. Development notes

- All prompts are in `prompts/` and can be edited to tweak AI behavior.
- Search presets live in `config/search_presets.json`.
- The Freelancer API client is in `freelancer_client.py`.
- The OpenAI client and prompt loading logic are in `openai_client.py`.
