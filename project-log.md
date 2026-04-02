# BlogAI — Session Log
*Hot Memory for active session. Synced continuously. Never leave this stale.*

---

## State
**Current task:** Phase 1 — core pipeline (pipeline.py)
**Branch:** main (personal repo — single dev)
**Last action:** Project initialized, plan approved

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

---

## Decisions

| Decision | Rationale | Rejected | Date |
|---|---|---|---|
| Gradio over Streamlit | Native HF Spaces deploy, cleaner for demos | Streamlit — slightly more setup for HF | 2026-04-01 |
| Mistral 7B via HF Inference API as primary | Free, open-source, satisfies assignment requirement | Mixtral 8x22B — impossible locally, expensive on cloud | 2026-04-01 |
| Claude Sonnet as fallback | Better creative output, already have API access | GPT-4 — no existing access | 2026-04-01 |
| trafilatura for article scraping | Clean extraction, handles paywalls gracefully | BeautifulSoup — more boilerplate | 2026-04-01 |
| Telegram deferred to Future Work | Adds infra complexity, zero grade value | Full dual-arch as in original README | 2026-04-01 |

---

## Failed Approaches
*None yet.*

---

## Broken Skills
*None.*

---

## Blockers
- [ ] **Claude API** — key has no credits. Claude.ai subscription does not cover API access. To add: console.anthropic.com → Billing. Once credits are added, uncomment `anthropic` in requirements.txt and restore fallback logic in `app/pipeline.py`.

---

## Done

- 2026-04-01 — Project scoped, README reviewed, plan approved. Stack: Gradio + Mistral 7B (HF API) + Claude fallback + HF Spaces deploy.
