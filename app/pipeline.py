"""
Core pipeline: article URL + notes → blog post draft.

Primary LLM: configured in app/config.py
Fallback LLM: Claude Sonnet (TODO: wire up once API credits are added)
"""

import os
import re
import time
import urllib.parse
from typing import Optional

import trafilatura
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

try:
    from .config import ACTIVE_MODEL, ACTIVE_MODEL_DISPLAY, DEFAULT_TONE, TONE_INSTRUCTIONS, FORMAT_CONFIGS, OUTPUT_FORMATS
except ImportError:
    from config import ACTIVE_MODEL, ACTIVE_MODEL_DISPLAY, DEFAULT_TONE, TONE_INSTRUCTIONS, FORMAT_CONFIGS, OUTPUT_FORMATS

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")


def fetch_article(url: str) -> str:
    """Fetch and extract clean text from a URL."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Could not fetch URL: {url}")
    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    if not text:
        raise ValueError("Could not extract article text from the page.")
    return text


def build_prompt(article_text: str, notes: str, tone: str = DEFAULT_TONE) -> str:
    tone_instruction = TONE_INSTRUCTIONS.get(tone, "")

    blog_social_example = """
Example of the correct format and voice (blog_social):

Title: Anthropic gave me a terminal pet and I have opinions

Honestly, I did not expect to care about this. A little ASCII duck showed up next to my cursor and I've been thinking about it for two days.

The feature is called Claude Code Buddy. You type /buddy and it hatches. Mine is a duck. I wanted something cooler — a dragon, a cat, anything. Turns out your pet is locked to your account ID forever. No trading. No rerolling. Just you and your duck.

The rarity system is real though. There's a 1% chance yours is shiny. It's basically the Pokémon card opening experience but for developers who should be working.

What I actually want is progression. Like, finish a debugging session, earn a token, unlock a new species. It'd be the developer version of Duolingo streaks. Right now it just sits there looking cute, which is fine, but it could be so much more.

I hope this isn't just an April Fools thing.
""" if tone == "blog_social" else ""

    return f"""Write a blog post in the author's personal voice using the source article as backdrop and the author's notes as the core perspective.

{blog_social_example}
Now write a new post in that exact format and voice for the following:

Source article:
{article_text[:4000]}

Author's notes:
{notes}

{tone_instruction}

Length: 300–500 words. Include a title. No headers. No bullet points. Plain paragraphs only.

Blog post:"""


SYSTEM_PROMPT = """You are ghostwriting a casual personal blog post for a young professional.

FORMAT — these are hard rules, never break them:
- Plain prose only. Zero headers. Zero subheadings. Zero bullet points. Zero numbered lists.
- Short paragraphs: 2 to 3 sentences each.
- Short sentences. One idea per sentence. If a sentence needs more than one comma, split it into two sentences.
- The post ends with exactly one sentence — either a statement or a single question. Never end with two questions.
- No em-dashes anywhere.

VOICE:
- Lead with a reaction or opinion, not background context.
- The author's personal notes are the whole point. Build around them.
- Mention real platforms, apps, or cultural moments by name when they fit.
- Do not summarize the article. Use it as backdrop only."""


def generate_for_format(prompt: str, format_name: str) -> tuple[str, float]:
    """Call Qwen via HF Inference API for a specific output format. Returns (text, latency_seconds)."""
    fmt_config = FORMAT_CONFIGS[format_name]
    system = fmt_config["system"] or SYSTEM_PROMPT
    max_tokens = fmt_config["max_tokens"]

    client = InferenceClient(token=HF_TOKEN)
    start = time.time()
    response = client.chat_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        model=ACTIVE_MODEL,
        max_tokens=max_tokens,
        temperature=0.85,
    )
    latency = time.time() - start
    return response.choices[0].message.content, latency


def generate_post(
    url: str,
    notes: str,
    tone: str = "professional",
) -> dict:
    """
    Full pipeline: fetch article → build prompt → generate all output formats.

    Returns dict with keys: drafts, model_used, latency, article_preview, error_log
    drafts is a dict keyed by format name (matches OUTPUT_FORMATS).
    """
    article_text = fetch_article(url)
    base_prompt = build_prompt(article_text, notes, tone)

    drafts = {}
    total_latency = 0.0
    for fmt in OUTPUT_FORMATS:
        suffix = FORMAT_CONFIGS[fmt]["suffix"]
        prompt = f"{base_prompt}\n\n{suffix}" if suffix else base_prompt
        text, latency = generate_for_format(prompt, fmt)
        drafts[fmt] = text.strip()
        total_latency += latency

    return {
        "drafts": drafts,
        "model_used": ACTIVE_MODEL_DISPLAY,
        "latency": round(total_latency, 2),
        "article_preview": article_text[:300] + "...",
        "error_log": None,
    }


def build_linkedin_url(notes: str) -> str:
    """
    Build a Kagi Translate URL to LinkedIn-ify the user's raw notes.
    Uses notes directly as the seed — they're already brief and capture the core idea.
    """
    # Strip trailing punctuation/whitespace that causes browser URL parsing issues
    seed = re.sub(r'[\s.!?,]+$', '', notes.strip())
    encoded = urllib.parse.quote(seed)
    return f"https://translate.kagi.com/?from=en&to=linkedin&text={encoded}"


if __name__ == "__main__":
    # Quick smoke test — replace with a real URL and notes to validate
    import sys

    test_url = sys.argv[1] if len(sys.argv) > 1 else None
    test_notes = sys.argv[2] if len(sys.argv) > 2 else "This was an interesting read."

    if not test_url:
        print("Usage: python pipeline.py <article_url> [notes]")
        sys.exit(1)

    print(f"Fetching article from {test_url}...")
    result = generate_post(test_url, test_notes)
    print(f"\nModel: {result['model_used']} | Latency: {result['latency']}s")
    print(f"\nArticle preview:\n{result['article_preview']}")
    for fmt, draft in result["drafts"].items():
        print(f"\n--- {fmt} ---\n{draft}")
