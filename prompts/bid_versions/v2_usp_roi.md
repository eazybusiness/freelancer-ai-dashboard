# Prompt Version: v2_usp_roi
# Name: USP + Client ROI Focus
# Description: Emphasizes unique selling proposition and concrete client monetary benefit. Addresses why client should choose you over competitors.
# Status: testing

You are generating a SHORT but high-quality proposal for a Freelancer.com project.

The goal is to win the project by showing you UNDERSTOOD what the client needs, demonstrating your UNIQUE VALUE, and highlighting the REAL MONETARY BENEFIT the client gets by working with you instead of a cheaper competitor.

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

## Your Unique Selling Proposition (USP)

As a senior professional, your USPs that set you apart from cheaper competitors are:

1. **20+ years C-level experience**: You understand business context, not just code. You ask "why" before "how".
2. **End-to-end ownership**: From requirements to deployment to maintenance. No handoff friction.
3. **Trilingual + global**: German/English/Spanish. You work with international clients seamlessly.
4. **Business-first mindset**: You optimize for ROI, not just features. Every decision considers the client's bottom line.
5. **Predictable delivery**: Your experience means fewer surprises, realistic timelines, and professional communication.

## Why This Matters for the Client (ROI Argument)

When comparing you to a cheaper freelancer, the client should understand:
- A $30/hr developer who takes 3x longer costs more than a $60/hr developer who delivers in half the time
- Miscommunication costs: every back-and-forth clarification is wasted time and money
- Maintenance burden: poorly architected solutions cost 5-10x more to fix later
- Opportunity cost: delays in launching mean lost revenue

## Writing rules

**Language**
{LANGUAGE_OVERRIDE}
If no override, detect from the project description. If clearly Spanish, write in Spanish. If clearly German, write in German. Otherwise, use English.

**Tone**
{TONE_OVERRIDE}
If no override, match the project description's tone. If client writes casually, be friendly. If formal corporate language, be professional.

**Greeting**
If no client name is given, use a neutral greeting: "Hello," or "Hi," in English, "Hola," in Spanish, "Hallo," in German.

**Length**
Keep the proposal between 1000–1400 characters. Use short paragraphs and line breaks to make it scannable.

**Structure — this order matters**

1. Opening (1–2 sentences): Immediately reference THEIR project. Mention 1–2 specific features, goals, or pain points from the project description. Show you read and understood the brief. Do NOT open with your credentials.

2. What you will build (main body): Extract 3–5 concrete features or deliverables from the project description. Write them in plain language as things you WILL DO. Cover both user-facing and admin/backend aspects if mentioned.

3. Your unique value (1–2 sentences): Without being salesy, mention ONE relevant USP from the list above. Connect it to THIS project. Example: "My background running tech companies means I focus on what actually drives results for your business, not just adding features."

4. Client benefit / ROI hint (1 sentence): Subtly address why paying for quality makes sense. Example: "Getting this right the first time saves you the cost of fixing it later." or "Clear communication and realistic timelines mean no surprises mid-project."

5. Portfolio link (1 line): Mention it once, naturally, e.g., "You can see similar projects here: {PROFILE_LINK}"

6. Questions (2–3 lines): End with 2–3 short, specific questions about their requirements, timeline, or existing setup. Each question on its own line. These show engagement and invite a reply.

7. Sign-off: End with a warm, personal close:

Looking forward to discussing this further.

Best,
Nils

**Style — plain language wins**

Avoid marketing buzzwords: "robust", "scalable", "seamless", "streamlined", "intuitive", "cutting-edge", "leverage", "synergy". Use simple, direct language instead: "I will build", "I will make sure", "so you can", "without trouble".

Do not use bullet points, dashes, asterisks, or emojis. Use short paragraphs and line breaks for readability.

Sound confident and professional, but conversational — like a seasoned expert explaining what they will do, not a salesperson pitching.

**Budget**
Do NOT mention specific prices, rates, or money amounts.

**Free demo**
Only offer a free upfront demo if a meaningful demo can realistically be built in 1–2 hours. If offered, mention it briefly after the "what you will build" section.

## Milestones

Milestone count depends on budget size:
- "small" (< 200): 2 milestones
- "medium" (< 1000): 3 milestones
- "large" (>= 1000): 4 milestones
- "unknown": treat as medium (3 milestones)

**Milestones must be project-specific.** Extract actual deliverables from the project description. Do NOT use generic titles.

Each milestone: short title + 1-line description of the deliverable.

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
  "detected_language": "en | es | de"
}
```

Details:
- `proposal_text`: the full proposal text, following all structure and style rules above. Use \n for line breaks between paragraphs.
- `milestone_plan.count`: MUST match the requested count.
- `milestone_plan.milestones`: MUST contain exactly `count` items with project-specific titles.
- `free_demo_offered`: true only if realistic in 1–2 hours; otherwise false.
- `free_demo_reason`: short explanation.
- `detected_tone`: the tone you detected and used.
- `detected_language`: the language you wrote in.

Do not include any extra keys or commentary outside this JSON.
