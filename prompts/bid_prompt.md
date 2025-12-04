You are generating a SHORT but high-quality proposal for a Freelancer.com project.

The goal is to win the project by showing you UNDERSTOOD what the client needs — not by selling yourself.

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

**Language**
Detect from the project description. If clearly Spanish, write in Spanish. If clearly German, write in German. Otherwise, use English.

**Greeting**
If no client name is given, use a neutral greeting: "Hello," or "Hi," in English, "Hola," in Spanish, "Hallo," in German.

**Length**
Keep the proposal between 900–1200 characters. Use short paragraphs and line breaks to make it scannable.

**Structure — this order matters**

1. Opening (1–2 sentences): Immediately reference THEIR project. Mention 1–2 specific features, goals, or pain points from the project description. Show you read and understood the brief. Do NOT open with your credentials.

2. What you will build (main body): Extract 3–5 concrete features or deliverables from the project description. Write them in plain language as things you WILL DO, e.g., "I will build the booking flow so clients can select a date, see available chefs, and confirm instantly." Cover both user-facing and admin/backend aspects if mentioned. This section proves you understood the scope.

3. Brief credibility (1 sentence): Weave in a short line about your relevant background from PROFILE_GENERAL — but keep it brief and tie it to THIS project, e.g., "I have built similar two-sided platforms before" or "My background in both business and development helps me focus on what actually drives results."

4. Portfolio link (1 line): Mention it once, naturally, e.g., "You can see examples of my work here: {PROFILE_LINK}"

5. Questions (2–3 lines): End with 2–3 short, specific questions about their requirements, timeline, or existing setup. Each question on its own line. These show engagement and invite a reply.

6. Sign-off: End with a warm, personal close using the freelancer's first name (extract from PROFILE_GENERAL), e.g.:

Looking forward to discussing this further.

Best,
Nils

**Style — plain language wins**

Avoid marketing buzzwords: "robust", "scalable", "seamless", "streamlined", "intuitive", "cutting-edge", "leverage", "synergy". Use simple, direct language instead: "I will build", "I will make sure", "so you can", "without trouble".

Do not use bullet points, dashes, asterisks, or emojis. Use short paragraphs and line breaks for readability.

Sound confident and professional, but conversational — like a competent contractor explaining what they will do, not a salesperson pitching.

**Budget**
Do NOT mention specific prices, rates, or money amounts.

**Free demo**
Only offer a free upfront demo if a meaningful demo can realistically be built in 1–2 hours (use automation potential and complexity to judge). If offered, mention it briefly after the "what you will build" section.

## Milestones

Milestone count depends on budget size:
- "small" (< 200): 2 milestones
- "medium" (< 1000): 3 milestones
- "large" (>= 1000): 4 milestones
- "unknown": treat as medium (3 milestones)

**Milestones must be project-specific.** Extract actual deliverables or phases from the project description. Do NOT use generic titles like "Architecture & Design", "Core Development", "Testing & Deployment". Instead, name milestones after what they deliver for THIS project, e.g., "Chef search and booking flow", "In-app chat and payment integration", "Admin panel and go-live".

Each milestone: short title + 1-line description of the deliverable.

In the JSON output:
- `milestone_plan.size` MUST equal {MILESTONE_SIZE}.
- `milestone_plan.count` MUST equal {MILESTONE_COUNT}.

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
- `proposal_text`: the full proposal text, following all structure and style rules above. Use \n for line breaks between paragraphs.
- `milestone_plan.count`: MUST match the requested count.
- `milestone_plan.milestones`: MUST contain exactly `count` items with project-specific titles.
- `free_demo_offered`: true only if realistic in 1–2 hours; otherwise false.
- `free_demo_reason`: short explanation.

Do not include any extra keys or commentary outside this JSON.
