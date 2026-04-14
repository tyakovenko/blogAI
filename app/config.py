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

# Fallback model used when HF Inference is unavailable.
# Haiku is the same model used for corrections in the bot — consistent and cheap.
CLAUDE_FALLBACK_MODEL = "claude-haiku-4-5-20251001"

# Output formats — one LLM call + Notion column per entry.
# To add a format: add an entry here + its prompt in FORMAT_PROMPTS below.
# Then run: python scripts/sync_notion_schema.py
OUTPUT_FORMATS: list[str] = ["Blog Post", "LinkedIn"]

# Tone instructions passed to the LLM
# Per-format system prompts and user prompt suffixes.
# "system" → replaces the default SYSTEM_PROMPT for this format
# "suffix" → appended to the shared user prompt
FORMAT_CONFIGS: dict[str, dict] = {
    "Blog Post": {
        "system": None,  # uses default SYSTEM_PROMPT in pipeline.py
        "suffix": "Length: 300–500 words. Include a title. No headers. No bullet points. Plain paragraphs only.",
        "max_tokens": 900,
    },
    "LinkedIn": {
        "system": (
            "You are writing a LinkedIn post for a young professional.\n"
            "FORMAT — hard rules:\n"
            "- 150–250 words\n"
            "- Short paragraphs, 2–3 sentences each\n"
            "- Open with a hook: a direct reaction or opinion, not a summary\n"
            "- End with exactly one question\n"
            "- No hashtags. No bullet points. No headers. No em-dashes."
        ),
        "suffix": "Write the LinkedIn post now:",
        "max_tokens": 400,
    },
}

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
