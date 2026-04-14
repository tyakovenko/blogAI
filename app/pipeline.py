"""
Core pipeline: article URL + notes → blog post draft.

Primary LLM: selected per-request, defaults to DEFAULT_MODEL_KEY in config.
Fallback: Claude Haiku if an HF model fails and ANTHROPIC_API_KEY is set.
"""

import logging
import os
import re
import time
import urllib.parse

logger = logging.getLogger(__name__)

import trafilatura
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

try:
    import anthropic as _anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

try:
    from .config import (
        AVAILABLE_MODELS, DEFAULT_MODEL_KEY, CLAUDE_FALLBACK_MODEL,
        DEFAULT_TONE, TONE_INSTRUCTIONS, FORMAT_CONFIGS, OUTPUT_FORMATS,
    )
except ImportError:
    from config import (
        AVAILABLE_MODELS, DEFAULT_MODEL_KEY, CLAUDE_FALLBACK_MODEL,
        DEFAULT_TONE, TONE_INSTRUCTIONS, FORMAT_CONFIGS, OUTPUT_FORMATS,
    )

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def fetch_article(url: str) -> str:
    """Fetch and extract clean text from a URL."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Could not fetch URL: {url}")
    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    if not text:
        raise ValueError("Could not extract article text from the page.")
    return text


def build_prompt(article_text: str, notes: str, tone: str = DEFAULT_TONE, fmt: str = "Blog Post") -> str:
    """Build the user-facing prompt for a given format.

    LinkedIn gets a stripped-down prompt — no 'write a blog post' framing, no example.
    The LinkedIn system prompt in FORMAT_CONFIGS handles all style constraints.
    Mixing blog framing with the LinkedIn system caused blog-length bleed.
    """
    if fmt == "LinkedIn":
        return f"""Write a LinkedIn post using the source article as backdrop and the author's notes as the core perspective.

Source article:
{article_text[:4000]}

Author's notes:
{notes}

Write the LinkedIn post now:"""

    # Blog Post (and any other format) — full framing + tone instructions
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


def generate_for_format(
    prompt: str,
    format_name: str,
    model_key: str = DEFAULT_MODEL_KEY,
) -> tuple[str, float]:
    """Generate output for one format using the selected model.

    HF models: try HF Inference first, fall back to Claude Haiku if it fails.
    Anthropic models: call Claude directly, no fallback.
    Returns (text, latency_seconds).
    """
    fmt_config = FORMAT_CONFIGS[format_name]
    system = fmt_config["system"] or SYSTEM_PROMPT
    max_tokens = fmt_config["max_tokens"]

    model_config = AVAILABLE_MODELS[model_key]
    provider = model_config["provider"]
    model_id = model_config["id"]

    if provider == "anthropic":
        if not (_ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY):
            raise RuntimeError("Claude Haiku selected but ANTHROPIC_API_KEY is not set.")
        client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        start = time.time()
        response = client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text, time.time() - start

    # HF provider — try primary, fall back to Claude Haiku on failure
    try:
        client = InferenceClient(token=HF_TOKEN)
        start = time.time()
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            model=model_id,
            max_tokens=max_tokens,
            temperature=0.85,
        )
        return response.choices[0].message.content, time.time() - start
    except Exception as hf_err:
        logger.warning("HF Inference failed for %s (%s), falling back to Claude Haiku", model_key, hf_err)

    if not (_ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY):
        raise RuntimeError(
            f"HF Inference failed for {model_key} and ANTHROPIC_API_KEY is not set — cannot generate {format_name}."
        )

    client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    start = time.time()
    response = client.messages.create(
        model=CLAUDE_FALLBACK_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text, time.time() - start


def summarize_article(article_text: str, model_key: str = DEFAULT_MODEL_KEY) -> tuple[str, float]:
    """Generate a short summary of the article to use as notes when none are provided.

    Returns (summary_text, latency_seconds).
    Uses the same model routing as generate_for_format so behaviour is consistent.
    """
    model_config = AVAILABLE_MODELS[model_key]
    provider = model_config["provider"]
    model_id = model_config["id"]
    max_tokens = 300

    system = "You extract the key ideas from articles concisely."
    prompt = (
        f"Read this article and extract 3–5 bullet points capturing the most interesting "
        f"claims, arguments, or findings. Be specific — no generic summaries.\n\n"
        f"{article_text[:4000]}"
    )

    if provider == "anthropic":
        if not (_ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY):
            raise RuntimeError("Claude selected but ANTHROPIC_API_KEY is not set.")
        client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        start = time.time()
        response = client.messages.create(
            model=model_id, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip(), time.time() - start

    try:
        client = InferenceClient(token=HF_TOKEN)
        start = time.time()
        response = client.chat_completion(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            model=model_id, max_tokens=max_tokens, temperature=0.5,
        )
        return response.choices[0].message.content.strip(), time.time() - start
    except Exception as hf_err:
        logger.warning("HF summarization failed (%s), falling back to Claude Haiku", hf_err)

    if not (_ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY):
        raise RuntimeError("HF summarization failed and ANTHROPIC_API_KEY is not set.")

    client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    start = time.time()
    response = client.messages.create(
        model=CLAUDE_FALLBACK_MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip(), time.time() - start


def generate_post(
    url: str,
    notes: str,
    tone: str = DEFAULT_TONE,
    formats: list[str] | None = None,
    model_key: str = DEFAULT_MODEL_KEY,
) -> dict:
    """
    Full pipeline: fetch article → build prompt → generate all output formats.

    If notes is empty, generates an AI summary of the article and uses that instead.
    Returns dict with keys: drafts, model_used, latency, article_preview, error_log,
    and auto_notes (populated only when notes were auto-generated, else None).
    """
    article_text = fetch_article(url)

    auto_notes = None
    if not notes.strip():
        auto_notes, summary_latency = summarize_article(article_text, model_key=model_key)
        notes = auto_notes
        logger.info("No notes provided — used AI summary as notes")
    else:
        summary_latency = 0.0

    active_formats = formats if formats is not None else OUTPUT_FORMATS
    drafts = {}
    total_latency = summary_latency
    for fmt in active_formats:
        base_prompt = build_prompt(article_text, notes, tone, fmt=fmt)
        suffix = FORMAT_CONFIGS[fmt]["suffix"]
        prompt = f"{base_prompt}\n\n{suffix}" if suffix else base_prompt
        text, latency = generate_for_format(prompt, fmt, model_key=model_key)
        drafts[fmt] = text.strip()
        total_latency += latency

    return {
        "drafts": drafts,
        "model_used": model_key,
        "latency": round(total_latency, 2),
        "article_preview": article_text[:300] + "...",
        "auto_notes": auto_notes,
        "error_log": None,
    }


def build_linkedin_url(notes: str) -> str:
    """Build a Kagi Translate URL to LinkedIn-ify the user's raw notes."""
    seed = re.sub(r'[\s.!?,]+$', '', notes.strip())
    encoded = urllib.parse.quote(seed)
    return f"https://translate.kagi.com/?from=en&to=linkedin&text={encoded}"


if __name__ == "__main__":
    import sys

    test_url = sys.argv[1] if len(sys.argv) > 1 else None
    test_notes = sys.argv[2] if len(sys.argv) > 2 else "This was an interesting read."
    test_model = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_MODEL_KEY

    if not test_url:
        print("Usage: python pipeline.py <article_url> [notes] [model_key]")
        sys.exit(1)

    print(f"Fetching article from {test_url}...")
    result = generate_post(test_url, test_notes, model_key=test_model)
    print(f"\nModel: {result['model_used']} | Latency: {result['latency']}s")
    print(f"\nArticle preview:\n{result['article_preview']}")
    for fmt, draft in result["drafts"].items():
        print(f"\n--- {fmt} ---\n{draft}")
