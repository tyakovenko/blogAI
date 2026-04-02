# BlogAI — Session Log
*Hot Memory for active session. Synced continuously. Never leave this stale.*

---

## State
**Current task:** Notion integration for Telegram bot — BLOCKED
**Branch:** main (personal repo — single dev)
**Last action:** Bot deployed to HF Space, secrets set, Notion connection unresolved

---

## Constraints

| Constraint | Source | Failure Artifact |
|---|---|---|
| Text-based only — no image generation | Assignment requirement | — |
| Web framework must be Streamlit, Gradio, Voila, Shiny, or Panel | Assignment requirement | — |
| No local LLM — hardware is Intel UHD only, 16GB RAM | Discovered via hardware check | — |
| No Vercel/Next.js — not on approved framework list | Assignment requirement | — |
| Never hardcode model names, tone lists, or UI labels — all config lives in `app/config.py` | User feedback | — |
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

- [ ] **Notion bot connection** — telegramBot internal integration can't be connected to Blog Posts database via UI. Connections menu only shows external integrations. Share menu also doesn't surface it. Investigate Notion internal integration connection flow at notion.so/my-integrations.
- [ ] **Model selector** — add dropdown to UI for switching between available HF models. Options defined in `app/config.py`.
- [ ] **Post length control** — add short/medium/long option to UI. Map to word count ranges in `app/config.py`.
- [ ] **Paywalled/JS-rendered URLs** — add clearer user-facing error. Consider playwright fallback.
- [ ] **Save drafts back to Notion from web app** — add "Save to Notion" button in Gradio UI. Creates/updates Blog Posts entry with generated drafts, flips Status to Draft Generated.

---

## Notion Writes
- gradio-background-services — created — daemon thread pattern for background services in Gradio
- notion-integration-types — created — internal vs external integrations, 2000-char property limit
- hf-spaces-operations — created — secrets API, deployment triggers, free tier sleep behaviour

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
