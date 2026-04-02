"""
Single source of truth for all configurable values.
UI and pipeline both import from here — never duplicate these elsewhere.
"""

# Active model — change here, propagates everywhere
ACTIVE_MODEL = "Qwen/Qwen2.5-7B-Instruct"

# Display name derived from model ID — never hardcode separately
ACTIVE_MODEL_DISPLAY = ACTIVE_MODEL.split("/")[-1]

# Tone options: key → label shown in UI
# To add a tone: add an entry here + its instruction in TONE_INSTRUCTIONS below
TONES: dict[str, str] = {
    "blog_social": "Blog / Social",
    "professional": "Professional",
    "academic": "Academic",
}

DEFAULT_TONE = "blog_social"

# Tone instructions passed to the LLM
TONE_INSTRUCTIONS: dict[str, str] = {
    "blog_social": (
        "Write in a casual, conversational blog voice. "
        "Lead with a hot take or relatable observation — not a thesis. "
        "Use contractions. Keep paragraphs short (2–3 sentences). "
        "Reference real platforms, apps, or cultural moments by name where relevant. "
        "Use 'honestly,' 'lowkey,' 'to be fair' as natural beats. "
        "State opinions bluntly first, unpack after. "
        "Take something that seems surface-level and add a layer that makes it more interesting. "
        "End with an open question or thought, not a formal conclusion. "
        "No em-dashes. No bullet points in the body."
    ),
    "professional": (
        "Write in a clear, professional tone. Build context before the thesis. "
        "Use concrete named examples. Every paragraph needs a claim, evidence, and implication. "
        "End by returning to the opening frame."
    ),
    "academic": (
        "Write in a structured, analytical tone. Cite reasoning explicitly. "
        "Acknowledge counterarguments and redirect. Formal transitions only."
    ),
}
