# BlogAI — Session Log
*Hot Memory for active session. Synced continuously. Never leave this stale.*

---

## State
**Current task:** Gap fixes — Claude fallback + LinkedIn length bleed
**Branch:** main (personal repo — single dev)
**Last action:** Bot deployed to HF Space, secrets set, Notion connection unresolved

---

## Report Notes
- **Haiku correction scope — current session only:** Haiku corrections only apply to the active in-memory draft. If the bot restarts (e.g. HF Space wakes from sleep), conversation state is cleared and previous drafts cannot be edited via Telegram — they must be edited directly in Notion.
- **Single-mode correction:** A correction instruction applies to one draft at a time (Blog Post in `/blog` or `/all` mode, LinkedIn in `/linkedin` mode). There is no way to apply the same edit to both formats simultaneously — each must be corrected in a separate session.
- **HF Space free tier sleep limitation:** The Telegram bot runs as a background thread inside the HF Space. When the space goes idle (no Gradio UI traffic), HF puts it to sleep and the thread dies. Incoming Telegram messages are silently dropped until someone wakes the space by visiting the UI. This is an architectural constraint of hosting a persistent service on a free-tier platform — acceptable for personal/demo use, but not suitable for production reliability. Mitigation options: upgrade to paid HF tier, use a keep-alive ping service, or migrate the bot to a dedicated always-on host (e.g. a small VPS or Docker container).

---

## Constraints

| Constraint | Source | Failure Artifact |
|---|---|---|
| Text-based only — no image generation | Assignment requirement | — |
| Web framework must be Streamlit, Gradio, Voila, Shiny, or Panel | Assignment requirement | — |
| No local LLM — hardware is Intel UHD only, 16GB RAM | Discovered via hardware check | — |
| No Vercel/Next.js — not on approved framework list | Assignment requirement | — |
| Never hardcode model names, tone lists, or UI labels — all config lives in `app/config.py` | User feedback | — |
| Telegram bot: always register `add_error_handler` — never rely on per-handler try/except alone. Unhandled exceptions are swallowed silently by python-telegram-bot without it. | Recurring silent failure bug | — |
| Telegram bot: never use `parse_mode="Markdown"` unless input is sanitized. Telegram silently drops the entire message if the text contains unescaped `*` or `_`. | Silent message drop bug | — |
| Bot draft access: always use `drafts.get("Blog Post", "")` and `drafts.get("LinkedIn", "")` — never hardcode dict keys. In single-mode sessions only one key exists. | Recurring KeyError in save + correction handlers | — |
| Never hardcode calculated values (percentages, counts, scores) in reports or UI — always derive from data | User feedback | — |
| All Notion settings live at notion.so — never give confident UI navigation steps without flagging uncertainty | User feedback | — |

---

## Decisions

| Decision | Rationale | Rejected | Date |
|---|---|---|---|
| Gradio over Streamlit | Native HF Spaces deploy, cleaner for demos | Streamlit — slightly more setup for HF | 2026-04-01 |
| Mistral 7B via HF Inference API as primary | Free, open-source, satisfies assignment requirement | Mixtral 8x22B — impossible locally, expensive on cloud | 2026-04-01 |
| Claude Sonnet as fallback | Better creative output, already have API access | GPT-4 — no existing access | 2026-04-01 |
| trafilatura for article scraping | Clean extraction, handles paywalls gracefully | BeautifulSoup — more boilerplate | 2026-04-01 |
| Telegram bot runs inside HF Space as background thread | Zero extra infrastructure, already free and deployed | Railway — 30-day trial, env vars not propagating, overkill | 2026-04-02 |
| Multi-format output (Blog Post + LinkedIn) per generate call | One click, two usable drafts; formats defined in config | Single combined prompt — Qwen 7B can't follow multi-format in one pass | 2026-04-02 |
| Blog draft saved as Notion page body, LinkedIn as property | Rich text property has 2000 char limit; blog posts exceed it | Both as properties — would truncate | 2026-04-02 |

---

## Failed Approaches

| Tried | Error | Why wrong | Fix |
|---|---|---|---|
| Smoke test with anthropic.com URL | trafilatura fetch fails — JS-rendered SPA | trafilatura can't scrape JS-heavy pages without a headless browser | Add playwright/selenium fallback |
| Smoke test with NYT URL | trafilatura fetch fails — paywalled content | trafilatura cannot bypass subscription walls | Surface clearer error in UI; document paywall limitation |
| Railway worker for Telegram bot | TELEGRAM_BOT_TOKEN not set despite env vars configured | Railway doesn't propagate env vars to restarted deployments; new deploy also failed | Abandoned Railway, moved bot to HF Space background thread |
| Connecting telegramBot Notion integration via Connections menu | Integration doesn't appear in search | Notion Connections menu only shows external OAuth integrations (Google Drive, Figma, etc.), not internal integrations | Unknown — tried Share button too, not found. Needs investigation next session. |

---

## Broken Skills
*None.*

---

## Backlog

- [x] **Notion bot connection** — resolved. Created new `blogAI-bot` internal integration in Claude Brain workspace, connected via Blog Posts database `...` → Connections menu. Fixed property name `userDefined:URL` → `URL` in `bot/notion_queue.py`.
- [ ] **LinkedIn prompt tuning** — Qwen generates blog-length content for LinkedIn format. Root cause: `build_prompt` generates a "write a blog post" user message shared across all formats; LinkedIn system prompt overrides intent but doesn't fix the user-message framing. Fix: build a separate lean prompt for LinkedIn that doesn't carry blog-post framing.
- [ ] **Experimental LinkedIn speak** — investigate LinkedIn-native tone and register as a distinct output mode. Requires a summarization step before the generation call: article + notes → condensed summary → LinkedIn post. Current pipeline passes raw article text; LinkedIn format likely needs a pre-condensed input to prevent blog-length bleed. Explore as a separate `linkedin_experimental` condition in the Study 2 eval once baseline LinkedIn mode is stable.
- [ ] **Gemma as generation model** — add `google/gemma-2-9b-it` (or `gemma-2-2b-it`) as a selectable model via UI dropdown. Requires model selector in `app.py` + options list in `app/config.py`. Evaluate against Qwen baseline for style adherence before making it the default.
- [ ] **PDF file support** — accept PDF uploads as an alternative to article URL. Extract text via `pypdf` or `pdfplumber`, feed extracted text into `build_prompt` in place of `fetch_article()` output. Surface in Gradio UI as an optional file upload input.
- [ ] **Evals repo** — companion evaluation study lives at `~/Desktop/blogAI_evals` (separate git repo). Keep separate: evals run on Colab with heavy ML deps (BERTScore, sentence-transformers, NLI) incompatible with HF Spaces `requirements.txt`. Link in README. Evals call HF/Anthropic APIs directly — no code dependency on this repo.
- [ ] **Model selector** — add dropdown to UI for switching between available HF models (Qwen 7B, Gemma 9B). Options defined in `app/config.py`. Unblock once Gemma evaluation is done.
- [ ] **Post length control** — add short/medium/long option to UI. Map to word count ranges in `app/config.py`.
- [ ] **Paywalled/JS-rendered URLs** — add clearer user-facing error. Consider playwright fallback.
- [ ] **Save drafts back to Notion from web app** — add "Save to Notion" button in Gradio UI. Creates/updates Blog Posts entry with generated drafts, flips Status to Draft Generated.

---

## Notion Writes
- gradio-background-services — created — daemon thread pattern for background services in Gradio
- notion-integration-types — created — internal vs external integrations, 2000-char property limit
- hf-spaces-operations — created — secrets API, deployment triggers, free tier sleep behaviour
- telegram-bot-error-handling — created — global error handler, parse_mode silent drop bug
- telegram-bot-state-machine — created — per-chat state, mode flags, .get() draft access, run_in_executor

---

## Blockers
- [ ] **Claude API** — key has no credits. Add at console.anthropic.com → Billing. Then uncomment `anthropic` in requirements.txt and restore fallback logic in `app/pipeline.py`.
- [ ] **Telegram bot → Notion** — bot crashes with "Could not find database" because telegramBot integration isn't connected to Blog Posts DB. Bot is deployed and running on HF Space but saving to Notion is broken until this is resolved.

---

## Done

- 2026-04-01 — Project scoped, README reviewed, plan approved. Stack: Gradio + Mistral 7B (HF API) + Claude fallback + HF Spaces deploy.
- 2026-04-02 — Multi-format generation (Blog Post + LinkedIn). Formats driven by `OUTPUT_FORMATS` in config — adding a format requires one config line + running `scripts/sync_notion_schema.py`.
- 2026-04-02 — Telegram note capture bot built (`bot/`). Runs as background thread in HF Space. Parses URL + notes from single message, saves to Notion Blog Posts queue.
- 2026-04-02 — Notion Blog Posts database created in claudeBrain. Schema: Name, URL, Notes, LinkedIn, Status (Inbox/Draft Generated/Published), Created.
- 2026-04-02 — HF Space secrets set via API (TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_ID, NOTION_TOKEN, NOTION_DATABASE_ID).
- 2026-04-02 — README updated with full usage guide — use case, Telegram message format, what app is not for, known limitations.
- 2026-04-14 — Fixed LinkedIn length bleed: `build_prompt` now takes `fmt` param; LinkedIn gets a stripped prompt (no "write a blog post" framing, no example) — system prompt handles all constraints.
- 2026-04-14 — Wired Claude Haiku fallback in `pipeline.py`: HF call wrapped in try/except, falls back to `CLAUDE_FALLBACK_MODEL` from config if HF fails. `ANTHROPIC_API_KEY` read from env.
- 2026-04-14 — Backlog updated: Gemma model, PDF support, evals repo (keep separate), model selector prereqs.
