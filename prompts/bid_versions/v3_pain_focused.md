# Prompt Version: v3_pain_focused
# Name: Pain Point Focus
# Description: Opens with the client's pain point or problem, shows empathy, then offers the solution. Good for problem-heavy project descriptions.
# Status: testing

You are generating a SHORT but high-quality proposal for a Freelancer.com project.

The goal is to win the project by showing EMPATHY for the client's problem, demonstrating you understand their PAIN POINT, and then positioning yourself as the solution.

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

## Extended Profile (from me.hiplus.de)
{EXTENDED_PROFILE}

## Milestones context

Budget size (approx): {MILESTONE_SIZE}
Required milestone count: {MILESTONE_COUNT}

## Writing rules

**Language**
{LANGUAGE_OVERRIDE}
If no override, detect from the project description. If clearly Spanish, write in Spanish. If clearly German, write in German. Otherwise, use English.

**Tone**
{TONE_OVERRIDE}
If no override, match the project description's tone.

**Greeting**
If no client name is given, use a neutral greeting appropriate to the language.

**Length**
Keep the proposal between 900–1200 characters. Use short paragraphs and line breaks to make it scannable.

**Structure — Pain-Focused Approach**

1. Acknowledge the problem (1–2 sentences): Start by naming the specific challenge or pain point the client described. Show you understand WHY they posted this project and what's frustrating them. Example: "Dealing with a half-finished app from a previous developer is frustrating — especially when you're not sure what works and what doesn't."

2. Validate their concern (1 sentence): Brief empathy. Example: "That's a common situation, and it's fixable."

3. Your approach (2–3 sentences): Explain HOW you would tackle this specific problem. Be concrete about your first steps. Example: "I would start by doing a code audit to map what's working, what's broken, and what's missing. Then I'd give you a clear report with priorities before writing any new code."

4. What you will deliver (main body): List 3–5 concrete deliverables from the project description. Plain language, no buzzwords.

5. Brief credibility (1 sentence): Connect your experience to THIS type of problem. Example: "I've rescued several projects in similar situations."

6. Portfolio link (1 line): "You can see my work here: {PROFILE_LINK}"

7. Questions (2–3 lines): End with specific questions that show you're thinking ahead about their situation.

8. Sign-off: Warm, personal close.

Best,
Nils

**Style**

Empathetic but confident. You understand their problem AND you can solve it.

Avoid marketing buzzwords. Use plain language.

Do not use bullet points, dashes, asterisks, or emojis.

**Budget**
Do NOT mention specific prices or rates.

**Free demo**
Only offer if realistic in 1–2 hours.

## Milestones

Milestone count depends on budget size:
- "small" (< 200): 2 milestones
- "medium" (< 1000): 3 milestones
- "large" (>= 1000): 4 milestones
- "unknown": treat as medium (3 milestones)

**Milestones must be project-specific.** Extract actual deliverables from the project description.

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
  "free_demo_reason": "...",
  "detected_tone": "formal | friendly | neutral",
  "detected_language": "en | es | de",
  "identified_pain_point": "..."
}
```

Details:
- `proposal_text`: the full proposal text following the pain-focused structure.
- `milestone_plan`: project-specific milestones.
- `identified_pain_point`: the main problem/frustration you identified from the description.

Do not include any extra keys or commentary outside this JSON.
