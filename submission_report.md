# BlogAI: Voice-Preserving Content Amplification via a Two-Stage LLM Pipeline

**DS552 — Generative AI | Assignment 7**

---
## 0. Quick notes

Generative AI Use Disclaimer: The project is done in collaboration with Anthropic's Claude CLI (Sonnet + Haiku + Opus). The models are responsible for the  code and initial report writing. All of the research, system planning, and report edits was done with AI aid.

- Application is built primarily for personal use so my own Telegram, Notion, HF, and Anthropic keys are used
- This document provides a comprehensive overview of the whole project - details live in two separate repos: [application](https://github.com/tyakovenko/blogAI) and [evals](https://github.com/tyakovenko/blogAI_evals).
- Full evaluation methodology, results tables, calibration data, and statistical tests: [Evaluation Report](https://github.com/tyakovenko/blogAI_evals/blob/main/results/report.md)
- Application usage, known limitations, and local setup: [README](https://github.com/tyakovenko/blogAI/blob/main/README.md)
- [Live](https://huggingface.co/spaces/tyakovenko/blogAI) application. 
- [Sample](https://github.com/tyakovenko/blogAI/blob/main/sample_output.md)

## 1. Introduction and Objective

Writing about what you read is one of the highest-leverage habits for building a public presence in a technical field — but the gap between "I have thoughts about this article" and "I have a publishable draft" is wide. I have the same trouble so BlogAI is meant to close the gap.

The application takes two inputs: an article URL and the user's raw notes on that article. It produces two outputs: a blog post draft (300–500 words) and a LinkedIn post draft (150–250 words), both calibrated to the user's voice. The notes are the primary input — the article is context, not source material. The goal is thought amplification, not summarization. The application is build primarily for personal use but can be extended to support multiple users (would require minimal architectural changes and migration away from free application tiers).


---

## 2. Generative AI Model Selection

### Primary generation: Qwen 2.5 7B Instruct (HuggingFace free-tier serverless)

The original plan called for Mistral 7B Instruct v0.3. During development, HuggingFace's free inference tier (Novita provider) dropped support for both `mistralai/Mistral-7B-Instruct-v0.3` (rejected: *"not supported for task text-generation, provider novita"*) and `mistralai/Mistral-7B-Instruct-v0.2` (rejected: *"not a chat model"*). Another model to try was Gemma which failed silently on the same endpoint, reverting to the fallback model - Claude Haiku -  without any visible error. Qwen 2.5 7B Instruct was the first model tested that responded successfully on the free-tier serverless API and has remained the production model since.

Qwen 2.5 7B was selected over larger alternatives because free-tier serverless inference does not support hosted deployments — the model must be available as a shared endpoint. Within that constraint, Qwen 2.5 7B is a strong instruction-following model that handles the substance generation task well, even if its stylistic instruction-following has a measurable ceiling (discussed in §8).

**Relevance:** open-source, instruction-tuned, no API cost, accessible to any user without credentials.
**Applicability:** text generation from structured prompts — the core task.
**Feasibility:** confirmed working on HF free-tier serverless; resumable generation scripts for 162-output eval runs.

### Edit pass and fallback: Claude Haiku 4.5 (Anthropic API)

Claude Haiku 4.5 serves two roles. In the production pipeline, it receives Qwen's draft and applies a voice-correction edit pass — specifically targeting the stylistic patterns Qwen cannot reliably produce under prompt constraint. As a fallback, Haiku generates the full post directly if the HF Inference API is unavailable.

Haiku was chosen over Sonnet and Opus for cost. At approximately $0.001 per sample on a short edit-pass prompt, it is viable for a per-post production pipeline. Haiku's instruction-following on stylistic tasks is sufficient to operationalize a detailed voice specification. Sonnet and Opus would produce marginally better output at 5–10× the cost — not justified for an edit pass on short-form content. The API cost for the full 27-sample, two-mode evaluation study (54 Haiku calls for standalone generation + 54 edit-pass calls) was **$0.084 total**.

### Why not RAG

A retrieval-augmented architecture was considered and rejected. The user's notes are already the grounding source — there is no corpus to retrieve from, and the article text is fetched directly rather than indexed. RAG adds infrastructure (vector store, retrieval step, chunking pipeline) without solving a problem that exists in this use case.

---

## 3. Project Definition and Use Case

BlogAI is an AI-powered writing assistant that transforms the combination of an article and a user's reaction to it into mode-appropriate draft content. It is not:

- A summarizer — it builds outputs around the user's notes, using the article as backdrop
- A general writing assistant — it requires an article URL and notes as minimum input
- A publisher — it generates drafts for manual editing and posting

**The core loop:**

1. User reads an article on their phone → sends the URL + rough reaction to a Telegram bot or types the information into the HuggingFace interface.
2. Later, user opens BlogAI → pastes the URL and notes → clicks Generate
3. Two drafts appear: blog post and LinkedIn post
4. User edits and posts manually

The Telegram bot (step 1) is the mobile capture layer — it saves notes to a Notion drafts queue so nothing is lost between "I have a thought" and "I'm at a computer." The bot also allows for edits using Haiku and model selection. This step is optional for the assignment demo; the core generation functionality is entirely in the Gradio web interface.

**Two output modes:**

| Mode | Length | Voice target |
|---|---|---|
| Blog Post | 300–500 words | Personal, conversational, em-dash heavy, no bullet points |
| LinkedIn | 150–250 words | Hook opening, short paragraphs, direct address, closing question |

**Tone options:** Blog/Social (default), Professional, Academic — each maps to a distinct system prompt.

The app also includes an experimental **LinkedIn-ify via Kagi** button — it sends the user's raw notes (not the full pipeline output) to Kagi Translate's style rewriter via URL parameter, opening the result in a new tab. It's a separate, lighter-weight function for quickly reformatting rough notes into LinkedIn style without an article URL.

---

## 4. Implementation Plan

### 4.1 Technology Stack

| Component | Technology |
|---|---|
| Web framework | Gradio 5.x |
| Primary generation model | Qwen 2.5 7B Instruct via HuggingFace Inference API |
| Edit pass / fallback model | Claude Haiku 4.5 via Anthropic API |
| Article fetching | trafilatura |
| Telegram bot | python-telegram-bot (background thread) |
| Note queue | Notion API |
| Evaluation — substance fidelity | sentence-transformers (`all-mpnet-base-v2`), cosine similarity |
| Evaluation — voice fidelity | spaCy (`en_core_web_sm`), regex |
| Evaluation — factual consistency | rank-bm25, DeBERTa-v3-large-mnli (NLI) |
| Statistical analysis | scipy (Wilcoxon signed-rank), numpy, pandas |

### 4.2 Architecture

```
User input (Gradio)
  │
  ├── Article URL ──► trafilatura ──► article_text
  └── Notes

article_text + notes + tone
  │
  ▼
[Qwen 2.5 7B — HF Inference API]
  │  substance-focused prompt
  │  no style spec (Qwen's style ceiling)
  ▼
qwen_draft
  │
  ▼
[Claude Haiku 4.5 — Anthropic API]
  │  voice-correction edit prompt
  │  does NOT receive original notes
  ▼
final_draft (blog + LinkedIn)
```

The edit pass receives only Qwen's draft and a short voice-correction prompt. It does not receive the original notes. This is the key architectural constraint: substance already lost in Qwen's generation cannot be recovered by the edit pass. This constraint motivated the two-metric evaluation design and is discussed in §8.

If the HF Inference API is unavailable, the pipeline falls back to Haiku generating the full post directly from notes + article text (bypassing Qwen entirely). 

### 4.3 API Architecture Note

HuggingFace's Inference API migrated from `text_generation` to `chat_completion` as the standard task interface during development. Code written against the older API breaks silently in some cases. The application uses `chat_completion` with explicit system/user message structure throughout.

### 4.4 Development and Testing

**Local development:**

```bash
git clone https://github.com/tyakovenko/blogAI.git
cd blogAI
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add HF_TOKEN and ANTHROPIC_API_KEY
python app.py          # opens at http://localhost:7860
```

**Evaluation pipeline (separate repo — `blogAI_evals`):**

The evaluation runs were executed locally, not on HF Spaces. 

```bash
cd blogAI_evals
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add HF_TOKEN and ANTHROPIC_API_KEY
python scripts/generate.py        # runs all 3 conditions × 2 modes × 27 samples
python eval/run_all.py            # produces results/scores.csv
jupyter notebook notebooks/01_analysis.ipynb
```

The generation script is resumable — it checks `data/outputs/` before making API calls and skips already-generated samples. Three samples in the study required Qwen retries due to HF serverless downtime; all 27 samples were ultimately generated successfully.

**Smoke test (single sample, all conditions):**

```bash
python scripts/test_call.py
```

---

## 5. Model Evaluation and Performance Metrics

*Full methodology, results tables, calibration data, and statistical tests are in the [Evaluation Report](https://github.com/tyakovenko/blogAI_evals/blob/main/results/report.md). This section summarizes the approach and key findings.*

### 5.1 Why Standard Metrics Don't Fit

- **BLEU/ROUGE** measure n-gram overlap against a reference. This task has no fixed reference — the expected output is a paraphrase of the user's notes in a new mode. A correct output that rephrases a claim using different words would score near zero on BLEU despite being fully successful.
- **Perplexity** measures how well the model predicts its own output distribution. It is a proxy for fluency, not for whether the user's argument was preserved.

The evaluation instead uses two primary metrics calibrated specifically for this task, plus a factual floor check.

### 5.2 Substance Fidelity

**What it measures:** Whether the user's argument components from the notes appear in the output.

Each note sentence is typed by keyword pattern matching into four component types (logic, implication, evidence, claim), then embedded with `all-mpnet-base-v2` and matched against output sentences via cosine similarity. Per-type means and an aggregate score are reported.

**Why `all-mpnet-base-v2`:** Dense embedding cosine similarity allows models to rephrase freely while still scoring well if the underlying argument is preserved — which is the actual requirement. BERTScore (token-level) and ROUGE (n-gram overlap) would penalize legitimate reformulations.

**Flattening flag:** claim score ≥ 0.6 AND (logic + implication) / 2 < 0.4 — the model kept the topic but stripped the reasoning structure.

### 5.3 Voice Fidelity

**What it measures:** Whether the output matches the user's known linguistic fingerprint.

A custom two-tier rubric operationalizes the voice specification:
- **Tier 1 (surface markers):** em-dash usage, contractions, banned words, no bullet points, no markdown headers — detectable by regex
- **Tier 2 (structural patterns):** subordinate clause ratio, additive transition count, concession-redirect structure, paragraph-ending consequence markers — requires spaCy dependency parsing

The Tier 1 − Tier 2 delta is a diagnostic in itself: high Tier 1 with low Tier 2 indicates surface mimicry — the output looks right on the surface but lacks the structural patterns that define the voice at depth.

**Why a custom rubric:** No off-the-shelf metric operationalizes a specific author's linguistic patterns. The rubric was validated against human-edited gold outputs (Spearman ρ = 0.876, p ≈ 0) before the study ran — a required gate to trust the rankings.

### 5.4 Factual Consistency (Floor Check)

BM25 retrieval over article passages followed by DeBERTa-v3-large-mnli NLI flags outputs with > 20% sentence contradiction rate. This is a floor check, not a ranking signal — it catches egregious hallucination without requiring high precision at the boundary. Per-sentence grounding avoids false contradiction flags from comparing output sentences against unrelated article sections.

### 5.5 Latency and Cost

Latency was measured on every API call. Qwen 2.5 7B on HF free-tier serverless showed non-deterministic latency: 5–8 seconds per generation at ~1,200–1,300 prompt tokens, with variance attributable to shared infrastructure. A paid inference endpoint would reduce this to approximately 1–2 seconds for the same model. Haiku latency was logged per call by the cost tracker but not analyzed as a primary metric — median observed latency was approximately 3–4 seconds.

Cost tracking applies to Haiku calls only (Qwen is free tier):

| Condition | Mode | Mean cost per sample | Study total (27 samples) |
|---|---|---|---|
| Haiku standalone | Blog | $0.001034 | $0.027925 |
| Haiku standalone | LinkedIn | $0.000636 | $0.017179 |
| Qwen→Haiku (edit pass) | Blog | $0.001032 | $0.027860 |
| Qwen→Haiku (edit pass) | LinkedIn | $0.000396 | $0.010703 |

The pipeline's LinkedIn edit pass costs 38% less than standalone Haiku generation for the same mode. Total Haiku spend across the entire 27-sample, two-mode evaluation: **$0.084**.

### 5.6 Key Results

The study compared three conditions: Qwen standalone, Haiku standalone, and the Qwen→Haiku pipeline, across 27 samples and two output modes (blog and LinkedIn).

**Substance fidelity:** The pipeline was competitive with or better than Haiku standalone on both modes. On LinkedIn, Qwen→Haiku (mean 0.663) outperformed Haiku standalone (0.624) at p = 0.030. On blog, the difference (0.679 vs. 0.659) was non-significant at this sample size. Haiku's edit pass slightly degrades substance relative to Qwen's draft — it rewrites to fix voice, and substance takes a marginal hit. The pre-edit intermediate condition isolates this: substance drops from 0.690 (Qwen draft) to 0.679 (after Haiku edit) on blog, and from 0.679 to 0.663 on LinkedIn.

**Voice fidelity:** The pipeline was strongly superior to Haiku standalone on both modes, and substantially better than Qwen standalone. On blog, Qwen→Haiku Tier 2 (structural voice) scored 0.956 vs. Haiku's 0.800 and Qwen's 0.548. The Tier 1 − Tier 2 delta shows Qwen alone is mimicking surface form (delta +0.119) while the pipeline achieves genuine structural voice (delta −0.104).

**The tradeoff:** The Haiku edit pass trades a small amount of substance for significant voice improvement. Whether that tradeoff is acceptable depends on the use case — for a personal brand writing tool, voice is the primary constraint, making the pipeline the preferred configuration.

**Argument flattening:** All conditions flagged 7% of blog samples (2/27) and 4% of LinkedIn samples (1/27) for argument flattening. No condition was meaningfully worse than another on this metric.

---

## 6. Deployment Strategy

### Live application

**HuggingFace Spaces (primary deployment):**
`https://huggingface.co/spaces/tyakovenko/blogAI`


### How the deployment works

The application is deployed as a Gradio app on HuggingFace Spaces (free tier). HF Spaces builds the Docker image from the repository on push, installs `requirements.txt`, and runs `app.py`. The `HF_TOKEN` and `ANTHROPIC_API_KEY` are stored as Space secrets (not in the repository).

The Gradio interface runs on port 7860 inside the Space; HF Spaces exposes it at the public URL above. A `GRADIO_SHARE` tunnel is not used — the Space URL is permanent and stable.

### Telegram bot constraint

The Telegram capture bot (`bot/bot.py`) runs as a background polling thread inside the HF Space process, started at app launch. **If the HF Space goes idle (no web traffic for approximately 15 minutes on the free tier), the Space process is suspended and the bot thread dies with it.** Incoming Telegram messages during idle periods are silently dropped — no error, no retry, no notification.

To use the Telegram bot reliably: visit the Space URL before sending messages to wake the process. For persistent always-on capture, the bot would need to be migrated to a webhook-based deployment on an independent host (Render, Fly.io) separate from the Space.

This is a known free-tier architectural constraint. The Gradio web interface is unaffected — it wakes the Space on page load.

### Hosting comparison

| Option | Cost | Reliability | Suitable for |
|---|---|---|---|
| HuggingFace Spaces (free) | $0 | Idle timeout, shared infra | Demo, low-traffic personal use |
| HF Spaces (paid/persistent) | ~$23/mo | Always-on | Production |
| Render / Fly.io (Telegram bot only) | Free tier | Always-on | Bot-only migration |
| Local | $0 | Manual | Development, eval runs |

---

## 7. Expected Outcomes and Challenges

### What the evaluation confirmed

The Qwen→Haiku pipeline is the recommended production configuration. It outperforms Haiku standalone on substance fidelity (significantly on LinkedIn, directionally on blog) while achieving stronger voice fidelity than either standalone model. The LinkedIn edit pass costs 38% less than standalone Haiku generation. The pipeline's primary cost is a small degradation in substance relative to Qwen's raw draft — this is recoverable in principle by injecting the original notes into the edit prompt, which is the most direct next step (see §9).

### Challenges encountered and mitigations

**Model availability on free-tier inference (encountered, mitigated):**
Mistral 7B and Gemma both failed on the HF free-tier serverless endpoint during development — Mistral explicitly rejected, Gemma silently failing to the Anthropic fallback. The application now includes a visible status line showing which model was actually used (`Generated with Qwen/Qwen2.5-7B-Instruct in 6.1s`) so silent fallbacks surface to the user.

**Qwen's stylistic instruction ceiling (known limitation):**
Qwen 2.5 7B defaults strongly to structured listicle output (headers, bullet points) under standard instruction-following prompts. Four prompt iterations were tested — basic tone guidance, explicit rule lists, hard-rule framing, few-shot examples — with only partial improvement. This is not a prompt engineering failure; it is a 7B-class model capability boundary. The Haiku edit pass was introduced specifically to handle the stylistic gap. The evaluation confirms it works.

**Paywall and bot-detection failures (known limitation):**
trafilatura cannot fetch paywalled content (NYT, Bloomberg, most major newspapers) or JS-rendered SPAs without SSR. Three of 30 eval samples were dropped for this reason; five required manual copy-paste. The application returns an explicit error message for fetch failures. Open-access sources (dev blogs, newsletters, arXiv, company pages) work reliably.

**HF serverless downtime (encountered, mitigated):**
The HF Inference API experienced downtime during the evaluation generation run. The generation script is resumable — it checks existing outputs before making API calls. Three samples required retries and were ultimately generated successfully.

**LinkedIn rubric misalignment (known, deferred):**
Feature analysis on 51 real LinkedIn posts revealed that three of seven rubric checks rarely fire on actual LinkedIn content (hook detection operationalized as first-person reaction verb; specific conversational markers; explicit CTA ending). LinkedIn scores in the study are computed with the uncorrected rubric and underestimate platform fidelity for all conditions equally. Rubric correction is deferred to future work.

---

## 8. Resources Required

### APIs and services

| Resource | Cost | Purpose |
|---|---|---|
| HuggingFace Inference API | Free (serverless) | Qwen 2.5 7B generation |
| Anthropic API (Claude Haiku 4.5) | Pay-per-token (~$0.001/post) | Edit pass, fallback generation |
| HuggingFace Spaces | Free | Hosting |
| Notion API | Free | Telegram note queue (optional) |
| Telegram Bot API | Free | Mobile capture (optional) |

### Libraries

**Application:** Gradio, trafilatura, anthropic, python-telegram-bot, requests, notion-client

**Evaluation:** sentence-transformers, spaCy + `en_core_web_sm`, rank-bm25, transformers (DeBERTa-v3), scipy, numpy, pandas, matplotlib, seaborn, jupyter

### Hardware

No special hardware required. Both Qwen and Haiku inference run server-side (HF Inference API and Anthropic API respectively). The evaluation pipeline runs locally but requires no GPU — sentence-transformers and spaCy run on CPU; DeBERTa-v3 inference is slow on CPU but completes within acceptable time for 27 samples. A GPU would reduce eval runtime but is not required.

---

## 9. Conclusion and Future Work

BlogAI demonstrates that a two-stage LLM pipeline — a free-tier open-source model for substance generation followed by a low-cost proprietary model for voice correction — can produce content that outperforms either model alone on the metrics that matter for the use case. The evaluation shows that the Qwen→Haiku pipeline achieves stronger substance fidelity than Haiku standalone (significantly so on LinkedIn) while producing better voice fidelity than either standalone model. The pipeline's LinkedIn edit pass costs 38% less than standalone Haiku generation at better performance on both primary metrics.

The evaluation methodology is the substantive contribution of the study. Off-the-shelf metrics (BLEU, ROUGE, perplexity) do not fit this task — they penalize paraphrase, which is the correct behavior for a thought amplification tool. The custom two-metric design (argument-component cosine similarity for substance; calibrated two-tier linguistic rubric for voice) was validated against human-edited gold outputs before use, and the calibration gate is what makes the rankings trustworthy.

### Future work

**Inject notes into the edit prompt.** The highest-leverage improvement is adding the original notes to the Haiku edit prompt. Currently the edit pass cannot recover substance already dropped by Qwen. Adding notes as context would decouple substance preservation from Qwen's generation quality.

**Fix the LinkedIn rubric.** Three of seven LinkedIn rubric checks rarely fire on real LinkedIn content. The corrected rubric (based on the 51-post feature analysis) would produce more accurate voice scores for the LinkedIn mode.

**Extended model set.** The evaluation infrastructure supports additional conditions with minimal code changes. When Gemma and Mistral become available on a reliable inference endpoint, adding them requires only new prompt files and a model entry in `generate.py`.

**Production monitoring.** The eval pipeline can be adapted for lightweight production monitoring — sampling real BlogAI outputs periodically and flagging substance drop or argument flattening rates that exceed study thresholds. This would detect model drift or prompt regression without a full re-run.

**LoRA fine-tuning.** A LoRA fine-tune of Qwen 2.5 7B on a corpus of the author's writing would directly address the style ceiling. A T4 GPU on Google Colab (free tier) is sufficient for a low-rank fine-tune of a 7B model; the fine-tuned adapter would be hosted alongside the base model on HF Hub. This is the highest-leverage improvement to generation quality after the notes-in-edit-prompt change.

---


