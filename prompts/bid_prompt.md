You are generating a SHORT but high-quality proposal for a Freelancer.com project.

The freelancer wants to:
- Save time.
- Stand out from generic, boring bids.
- Focus on outcomes, not specific tools.

Use the information below.

## Project

Title: {PROJECT_TITLE}
URL: {PROJECT_URL}

Description:
{PROJECT_DESCRIPTION}

## Previous analysis

Summary: {ANALYSIS_SUMMARY}
Rough suitability score: {ROUGH_SCORE}
Automation potential (0-100): {AUTOMATION_POTENTIAL}
Manual / non-automatable work notes: {MANUAL_WORK_NOTES}

## Freelancer profile

Label: {PROFILE_LABEL}
General:
{PROFILE_GENERAL}

Specific focus:
{PROFILE_SECTION}

Portfolio link: {PROFILE_LINK}

## Milestones context

Budget size (approx): {MILESTONE_SIZE}
Required milestone count: {MILESTONE_COUNT}

## Writing rules

- **Language**: Detect from the project description. If clearly Spanish, write in Spanish. If clearly German, write in German. Otherwise, use English.
- **Greeting**: If no client name is given, use a neutral greeting in that language, e.g.:
  - English: "Hi there,"
  - Spanish: "Hola,"
  - German: "Hallo,"
- **Length**: Keep the proposal under roughly 900–1100 characters. Prioritize clarity and impact.
- **Personal positioning**:
  - In the first or second sentence, briefly describe who you are as a freelancer (role, strengths, focus) using the PROFILE_GENERAL text. Do not invent or assume a specific personal name.
  - Blend the freelancer profile information (PROFILE_GENERAL and PROFILE_SECTION) into 1–2 natural sentences. Do not dump it as a list; integrate it into the flow.
  - Mention the portfolio link once, for example: "You can see more of my work here: {PROFILE_LINK}".
- **Style**:
  - Start with something concrete about their project or a specific outcome you will achieve.
  - Focus on business results (reliability, time saved, revenue/profit impact), not on tools.
  - Sound confident, original, and professional; avoid generic phrases like "I am very eager and enthusiastic".
- **Questions**:
  - End the proposal with 2–4 short, concrete questions about technical details and success criteria (e.g. current stack, existing setup, constraints, timeline, KPIs).
  - Write each question as a separate plain-text sentence on its own line (no bullet characters).
- **Formatting**:
  - Plain text only. No markdown (no bullets like -, *, **, etc.).
  - You may only use the "✅" emoji, at the start of a line, to highlight 1–3 key advantages or outcomes.
- **Budget**:
  - Do NOT mention specific prices, rates, or money amounts.
  - You may mention that you optimize for value, reliability, and long-term maintainability rather than the lowest upfront price.
- **Free demo**:
  - Only offer a free upfront demo if you judge that a meaningful demo can be built within about 1–2 hours.
  - Use automation potential and project complexity to decide.

## Milestones

Decide milestone content based on budget size and milestone count:
- "small" (< 200): usually 2 milestones.
- "medium" (< 1000): usually 3 milestones.
- "large" (>= 1000): usually 4 milestones.
- "unknown": treat like medium (3 milestones).

In the JSON output:
- `milestone_plan.size` MUST equal the given {MILESTONE_SIZE}.
- `milestone_plan.count` MUST equal the given {MILESTONE_COUNT}.

Each milestone should have a short title and 1-line description, focusing on deliverables, not price.

## Output

Respond with **valid JSON only**, with this exact structure:

```json
{
  "proposal_text": "...",
  "milestone_plan": {
    "size": "small | medium | large | unknown",
    "count": 0,
    "milestones": [
      {"title": "...", "description": "..."}
    ]
  },
  "free_demo_offered": true,
  "free_demo_reason": "..."
}
```

Details:
- `proposal_text`: the full text of the proposal, following all rules above.
- `milestone_plan.count`: MUST match the requested milestone count.
- `milestone_plan.milestones`: MUST contain exactly `count` items.
- `free_demo_offered`: true only if a small but meaningful demo is realistic in 1–2 hours; otherwise false.
- `free_demo_reason`: short explanation of why a free demo is or is not realistic.

Do not include any extra keys or commentary outside this JSON.
