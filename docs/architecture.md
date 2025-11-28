# Freelancer Job Assistant – Architecture & Workflow

## 1. Strategic Goals

1. **Save time**  
   Let filters + AI scan new offers so you don’t have to manually read every listing.

2. **Never miss good jobs**  
   Systematically search recent projects with sensible filters, avoid duplicates, and highlight strong matches.

3. **Bid faster (and better)**  
   Pre-generate analysis, strategy, and draft bids so you can quickly review, tweak, and submit high-quality proposals.

---

## 2. High-Level Overview

The tool is a local Python application that:

- Searches Freelancer projects using your **personal access token**.
- Applies filters (country, language, budget, skills, time online, bids) to find promising projects.
- Avoids:
  - Projects you have already processed (ID tracking).
  - Projects matching unwanted keywords (blacklist, e.g. "wordpress", "on-site").
- Optionally fetches **full project details** and sends them to **OpenAI** to:
  - Score suitability for you.
  - Summarize requirements and risks.
  - Suggest a working strategy.
  - Draft a proposal/bid that you can edit and paste into Freelancer.

All data and configuration stay on your machine.

---

## 3. Current Implementation (Baseline)

Already implemented components:

- **`freelancer_client.py`**
  - Handles authentication using your personal access token (`freelancer-oauth-v1`).
  - Uses `https://www.freelancer.com/api/projects/0.1/projects/active/`.
  - Supports server-side filters: `query`, `languages[]`, `countries[]`, `jobs[]`, `limit`, `offset`.

- **`search_jobs.py`**
  - CLI tool that:
    - Queries active projects.
    - Applies client-side filters:
      - **Budget**: `--min-budget`, `--max-budget`.
      - **Time online**: `--posted-within-hours`.
      - **Current bids**: `--min-bids`, `--max-bids`.
      - **Required skills**: `--skills` (matches against project job names / SEO names).
    - Prints:
      - Project ID, title.
      - Budget range + currency (if available).
      - Number of bids.
      - Age (how long ago posted).
      - Country (if available).
      - Project URL.

This baseline already supports Goal **#1** partially (time-saving via filters).

---

## 4. New Functional Requirements

### R1 – No Duplicate Processing

- Maintain a persistent record of project IDs you have already **seen or processed**.
- When fetching new projects:
  - Skip any project whose ID is already in this record (unless explicitly overridden).
- Status values per project (planned):
  - `seen_only` – shown in search results.
  - `analyzed` – AI analysis done.
  - `bid_drafted` – AI-generated bid created.
  - `bid_sent` – you manually mark this once you actually bid.

This supports Goals **#1** and **#2** (systematic coverage, no rework).

### R2 – Blacklist of Unwanted Projects

- Maintain a configurable list of **blacklist keywords**, e.g.:
  - `"wordpress"`, `"on-site"`, `"shopify"`, `"homework"`, etc.
- For each project, check (lowercased):
  - Title.
  - Description (if available).
  - Job/skill names.
- If any keyword is a substring → **exclude** the project before AI analysis.

This supports Goal **#1** by cutting out work you never want to do.

### R3 – Fetch Full Project Details

- Add a method to `freelancer_client.py`:
  - `get_project_details(project_id: int) -> dict`
- Should return:
  - Full description.
  - Jobs / skills.
  - Budget & currency.
  - (Later) employer rating, past jobs, etc.

This enables better AI analysis for Goals **#2** and **#3**.

### R4 – OpenAI-Based Analysis

- Use an `OPENAI_API_KEY` from `.env` to call the OpenAI API.
- For each selected project, send:
  - Project details.
  - Your skills and profile.
  - Your preferences and constraints (budget range, preferred tech, languages, time zone, etc.).
- Receive from AI:
  - **Suitability score** (e.g. 0–100).
  - Short **summary** of the job.
  - Reasons to accept or reject.
  - Risks and unknowns.
  - Suggested **working strategy** (high-level steps).

This helps you quickly decide where to focus (Goals **#1** & **#2**).

### R5 – Bid / Proposal Drafting

- For high-scoring projects, call OpenAI again with a **proposal prompt** including:
  - Project details.
  - Working strategy.
  - Your portfolio highlights and style (from config).
- Output:
  - A proposal/bid draft with:
    - Intro & credibility.
    - Restatement of requirements.
    - Proposed solution & phases.
    - Timeline and budget justification.
    - 2–3 clarifying questions.
- You **always review and edit** before pasting into Freelancer.

This directly supports Goal **#3** (faster, higher-quality bids).

### R6 – Status Tracking

- Store, per project ID:
  - Current status (`seen_only`, `analyzed`, `bid_drafted`, `bid_sent`).
  - Last updated timestamp.
- Use this to:
  - Skip projects already fully processed.
  - Allow future UX features (e.g. list all `bid_drafted` projects that still need manual submission).

---

## 5. Data & Storage Design

### 5.1 Sensitive Secrets – `.env`

- **Already used:**
  - `FREELANCER_OAUTH_TOKEN` or `AccessToken` – personal Freelancer access token.
- **To add:**
  - `OPENAI_API_KEY` – OpenAI key for analysis & drafting.

These are **never** committed or printed.

### 5.2 Configuration – `config.json`

Planned JSON file, example structure:

```json
{
  "blacklist_keywords": ["wordpress", "on-site"],
  "min_budget": 100,
  "max_budget": 2000,
  "preferred_languages": ["en"],
  "preferred_countries": ["US", "CA", "GB"],
  "ai_score_threshold": 70
}
```

Purpose:

- Central place for your preferences and rules.
- Easy to tweak without changing code.

### 5.3 Persistent State – `seen_projects.json`

Planned JSON file to track processed projects:

```json
{
  "40020233": {
    "status": "seen_only",
    "last_updated": "2025-11-28T14:00:00Z"
  },
  "40020104": {
    "status": "analyzed",
    "last_updated": "2025-11-28T14:10:00Z"
  }
}
```

Minimal version: could start as a simple list of IDs and evolve to this richer structure.

---

## 6. Modules & Responsibilities

### 6.1 Existing

- **`freelancer_client.py`**
  - Handles auth and raw HTTP requests to Freelancer API.
  - Current: `search_projects(...)`.
  - Planned: `get_project_details(project_id)`.

- **`search_jobs.py`**
  - CLI for querying and listing projects.
  - Will be extended to use config, blacklist, and seen-projects tracking.

### 6.2 Planned New Modules

- **`config.py`**
  - Load `config.json` with default values.
  - Provide helpers like `get_blacklist_keywords()`, `get_budget_range()`, etc.

- **`store.py`**
  - Load / save `seen_projects.json`.
  - Core functions:
    - `is_seen(project_id) -> bool`.
    - `get_status(project_id) -> Optional[str]`.
    - `mark_seen(project_id, status)`.

- **`openai_client.py`**
  - Load `.env` / OpenAI key.
  - Provide high-level functions:
    - `analyze_project(project, user_profile, preferences) -> {score, summary, strategy, notes}`.
    - `draft_bid(project, user_profile, strategy) -> str`.

- **`analyze_jobs.py`** (separate CLI, to keep things modular)
  - Orchestrates AI steps for selected project IDs.
  - Fetches details, calls OpenAI, prints results, and updates `seen_projects.json`.

---

## 7. User Workflows

### 7.1 Daily Search Workflow

1. **Run search** with sensible defaults:

   ```bash
   python search_jobs.py -q "python" --posted-within-hours 24 --max-bids 20
   ```

2. **Filtering pipeline**:
   - API-side filters: query, languages, countries, jobs, limit, offset.
   - Client-side filters:
     - Budget range.
     - Age (time online).
     - Bids.
     - Required skills.
   - New filters to add:
     - Remove projects with IDs in `seen_projects.json` (no duplicates).
     - Remove projects matching blacklist keywords.

3. **Output**: A curated list of promising projects.
4. **State**: Mark all printed project IDs as at least `seen_only`.

This directly supports Goals **#1** and **#2**.

### 7.2 Deeper AI Analysis Workflow

1. Choose project IDs from the printed list.
2. Run an analysis command (exact UX TBD, e.g. separate `analyze_jobs.py`):

   ```bash
   python analyze_jobs.py --project-ids 40020233,40020104
   ```

3. For each project ID:
   - Fetch full details via `freelancer_client.get_project_details(...)`.
   - Call `openai_client.analyze_project(...)`.
   - Print:
     - Suitability score.
     - Short summary.
     - Pros/cons, risks.
     - Suggested working strategy.
   - Update `seen_projects.json` with `status="analyzed"` (or `"shortlisted"` if score ≥ threshold).

This strongly supports Goals **#1** and **#2** (quickly focus on the best matches).

### 7.3 Bid Drafting Workflow

1. From analyzed/shortlisted projects, pick one to bid on.
2. Run:

   ```bash
   python analyze_jobs.py --project-ids 40020233 --draft-bid
   ```

3. For each selected project:
   - Use the existing analysis/strategy.
   - Call `openai_client.draft_bid(...)`.
   - Print the draft proposal text (or save to a `.md` file).
   - Update `seen_projects.json` with `status="bid_drafted"`.

4. You copy, refine, and submit the proposal on Freelancer, then (optionally) mark `status="bid_sent"` manually.

This directly supports Goal **#3**: bidding faster, but with better, more tailored content.

---

## 8. Implementation Roadmap (High-Level)

1. **Config & Storage**
   - Add `config.json` and `config.py`.
   - Add `seen_projects.json` and `store.py` with basic `is_seen/mark_seen` behavior.
   - Integrate blacklist + no-duplicate logic into `search_jobs.py`.

2. **Project Details Endpoint**
   - Implement `get_project_details(project_id)` in `freelancer_client.py`.

3. **OpenAI Integration**
   - Create `openai_client.py`.
   - Define first-version prompts for:
     - Project analysis.
     - Bid drafting.

4. **AI CLI (`analyze_jobs.py`)**
   - Implement commands to analyze projects by ID and optionally draft bids.

5. **Iteration & Refinement**
   - Tune blacklist, thresholds, and prompts based on real usage.
   - Potentially add more UX niceties (e.g. summary tables, export to CSV, etc.).

This document is intended as a **living spec**: we can update sections as the project evolves.
