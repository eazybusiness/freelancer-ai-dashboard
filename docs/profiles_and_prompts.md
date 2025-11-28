# Profiles, Categories & AI Prompts

This document defines how we describe your profiles, categories/tags, and AI prompts in a way that is:

- Easy for you to edit in Vim.
- Simple for Python to load.
- Flexible enough for multiple roles (web design, Python, database, etc.).

It directly supports the strategic goals:

1. **Save time** – by letting the tool understand your strengths and auto-filter/score jobs.
2. **Never miss good jobs** – by mapping categories to good tags and filters.
3. **Bid quicker & better** – by feeding rich profile info + custom prompts into OpenAI.

---

## 1. Profiles: how you describe yourself

We will keep **machine-readable profile data** in a JSON config file later (e.g. `config/profiles.json`).

For now, you can think of each profile like this template:

```text
Profile ID: python
Label: Python / Automation / Data
One-liner: Short sentence about you in this role.
Summary: 2–4 sentences describing your experience and strengths.
Skills: list of main skills.
Experience highlights: 3–6 bullet points of concrete work you've done.
Portfolio links: list of URLs (GitHub, portfolio site, live apps).
Preferred project types: short phrases like "web scraping", "ETL", "APIs".
Avoid project types: phrases like "homework", "school assignment".
Languages: languages you can work in (e.g. EN, ES).
Rate/budget hints: min budget, ideal budget range, or hourly.
Time zone / availability: when you're usually available.
```

We’ll support **multiple profiles**, e.g.:

- `python` – Python / automation / data.
- `webdesign` – UI/UX, HTML/CSS/JS, landing pages, etc.
- `database` – SQL, data modeling, optimization, migrations.

### 1.1 Planned JSON structure (for later code)

Later we’ll put this into `config/profiles.json` in a shape like:

```json
{
  "profiles": {
    "python": {
      "label": "Python / Automation / Data",
      "one_liner": "Python developer focused on automation, scraping and data analysis.",
      "summary": "2–3 sentences about you in this role.",
      "skills": ["Python", "web scraping", "pandas", "selenium"],
      "experience_highlights": [
        "Built automated scraping pipelines for e‑commerce and job sites.",
        "Developed data processing tools with pandas and SQL.",
        "Created REST APIs with FastAPI/Flask for internal tools."
      ],
      "portfolio_links": [
        "https://your-site.example/python",
        "https://github.com/youruser"
      ],
      "languages": ["en"],
      "rate_info": {
        "min_project_budget": 100,
        "preferred_budget_range": [300, 1500]
      }
    },
    "webdesign": {
      "label": "Web Design / Frontend",
      "one_liner": "Designer-developer for clean, responsive websites.",
      "summary": "...",
      "skills": ["Figma", "HTML", "CSS", "Tailwind", "basic JS"],
      "portfolio_links": ["https://your-site.example/web"],
      "languages": ["en"],
      "rate_info": {"min_project_budget": 150}
    }
  }
}
```

You won't have to remember this structure by heart: we’ll provide an initial `profiles.json` with comments/examples and you’ll just fill in your data.

---

## 2. Categories & Tags (what kind of jobs we look for)

Each **profile** will have associated **categories/tags** that influence:

- How we **search/filter** projects.
- Which jobs we consider "good" vs "bad" for that profile.

Conceptually, for each profile we want something like:

```text
Profile ID: python
Positive tags / keywords: ["python", "automation", "web scraping", "pandas", "ETL"]
Negative tags / keywords: ["wordpress", "on-site", "homework", "assignment"]
Preferred job titles: ["Python developer", "Data engineer", "Automation specialist"]
```

### 2.1 Planned JSON structure (for tags)

We can keep this together with profiles or in a separate file like `config/tags.json`. For now, target shape:

```json
{
  "categories": {
    "python": {
      "positive_keywords": ["python", "automation", "web scraping", "pandas"],
      "negative_keywords": ["wordpress", "on-site", "homework", "assignment"],
      "default_search_query": "python",
      "default_skills": ["python"],
      "default_min_budget": 100,
      "default_max_bids": 30
    },
    "webdesign": {
      "positive_keywords": ["landing page", "UI", "Figma", "responsive"],
      "negative_keywords": ["on-site", "Wordpress theme edit only"],
      "default_search_query": "web design",
      "default_min_budget": 150
    }
  }
}
```

How this helps your goals:

- **Save time:** automatic rejection of jobs that look like "wordpress" or "on-site".
- **Never miss good jobs:** each profile has a tuned search query & positive keywords.
- **Bid quicker:** less manual scanning before you even call the AI.

---

## 3. AI Prompts: analyzers & bid generators

We want prompts to be **plain text/Markdown files** you can edit, not hardcoded strings.

### 3.1 Files

Planned structure:

- `prompts/analysis_prompt.md` – used to analyze a project and score suitability.
- `prompts/bid_prompt.md` – used to draft a proposal/bid.

You will be able to open these in Vim, edit the wording, and re-run the tool.

### 3.2 Placeholders

Prompts will contain placeholders that the code fills in before sending to OpenAI.

Example for **analysis_prompt.md**:

```markdown
You are an assistant helping a freelancer decide whether to bid on a project.

## Freelancer profile

Name / label: {{PROFILE_LABEL}}
One-liner: {{PROFILE_ONE_LINER}}
Summary: {{PROFILE_SUMMARY}}
Key skills: {{PROFILE_SKILLS}}
Experience highlights:
{{PROFILE_EXPERIENCE_BULLETS}}

## Project

Title: {{PROJECT_TITLE}}
Description:
{{PROJECT_DESCRIPTION}}

Budget info: {{PROJECT_BUDGET_INFO}}
Bids so far: {{PROJECT_BIDS}}
Age: {{PROJECT_AGE}}

## Task

1. Give a suitability score from 0 to 100 for this freelancer.
2. Briefly explain why it fits or not.
3. List main risks / unknowns.
4. Propose a high-level working strategy in a few bullet points.

Answer in JSON with fields: score, summary, reasons, risks, strategy.
```

Example for **bid_prompt.md**:

```markdown
You are writing a freelance proposal for the following project.

## Freelancer profile
{{PROFILE_SUMMARY_FULL}}

## Project
Title: {{PROJECT_TITLE}}
Description:
{{PROJECT_DESCRIPTION}}

## Strategy (from your previous analysis)
{{STRATEGY_BULLETS}}

## Instructions

Write a proposal that:
- Uses a professional but friendly tone.
- Starts with 1–2 sentences showing understanding of the problem.
- Explains the proposed solution and steps.
- Mentions relevant past experience and portfolio links: {{PROFILE_PORTFOLIO_LINKS}}.
- Gives an estimated timeline.
- Ends with 2–3 specific questions to clarify requirements.

Return only the proposal text, no extra commentary.
```

We can adjust placeholder names as needed, but the idea is:

- You can **freely edit the natural language**.
- Just keep the `{{PLACEHOLDER}}` tokens intact so code can fill them.

### 3.3 Where your profile info fits

When we call OpenAI, the code will:

1. Load your **active profile** (e.g. `python`, `webdesign`).
2. Load the right **prompt template**.
3. Replace placeholders like:
   - `{{PROFILE_LABEL}}`, `{{PROFILE_SUMMARY}}`, `{{PROFILE_SKILLS}}`, etc.
   - `{{PROJECT_TITLE}}`, `{{PROJECT_DESCRIPTION}}`, etc.
4. Send the final prompt + project info to the OpenAI API.

This way the same code can:

- Switch profiles based on project type.
- Use different prompts for analysis vs bid drafting.
- Let you refine wording over time without touching Python.

---

## 4. What I need from you next

To move forward and keep things structured, you can prepare your profile info in this doc (or a separate `.md`) using the template from section 1.

For each role you care about now (e.g. `python`, `webdesign`, `database`), write:

1. **Profile ID**.
2. **Label**.
3. **One-liner**.
4. **Summary**.
5. **Skills list**.
6. **Experience highlights** (bullets).
7. **Portfolio links** for that profile.
8. Any **avoid** types (e.g. wordpress, on-site, homework).

Once you have those written down, I’ll:

- Turn them into an initial `config/profiles.json`.
- Propose a first `config/tags.json` reflecting your positive/negative keywords.
- Create `prompts/analysis_prompt.md` and `prompts/bid_prompt.md` using placeholders, so you can start tweaking the wording.

This will give us a clean foundation for the AI part while staying aligned with your three strategic goals.
