# BlogAI — Report Findings

Raw notes from the build session. Use these to populate the report sections.

---

## Model Selection

**Planned model:** Mistral 7B Instruct v0.3
**Actual model:** Qwen/Qwen2.5-7B-Instruct

Mistral 7B was the original choice, but HuggingFace's free inference tier (novita provider) dropped support for it mid-project. Two variants were tested and both failed:
- `mistralai/Mistral-7B-Instruct-v0.3` — rejected with: *"not supported for task text-generation, provider novita"*
- `mistralai/Mistral-7B-Instruct-v0.2` — rejected with: *"not a chat model"*

Qwen 2.5 7B was selected after testing four models against the free tier. It was the first to respond successfully. This is worth noting in the report as a real deployment constraint — model availability on free inference infrastructure is not guaranteed and requires fallback planning.

---

## API Architecture Finding

The HuggingFace Inference API shifted from `text_generation` to `chat_completion` as the standard task interface. Code written against the older API breaks silently in some cases. For production use, `chat_completion` with an explicit system/user message structure is the safer default.

---

## Model Performance — Instruction Following

**Finding:** Qwen 2.5 7B has a measurable ceiling on stylistic instruction-following.

The model was given progressively stricter formatting instructions across four prompt iterations:
1. Basic tone guidance — model ignored it, produced structured listicle
2. Explicit rules list — model still used headers and bullet points
3. Hard rules + "never break these" framing — still produced headers
4. Few-shot example showing target format — partial improvement, but sentence structure reverted to default

**Conclusion:** Small open-source models (7B class) default strongly to their instruction-tuning format. They handle factual and summarization tasks well but struggle to maintain a specific voice or structural style under constraint. This is not a prompt engineering failure — it's a model capability boundary.

**Implication for the report:** Use this as evidence for why model selection matters beyond benchmark scores. A model that scores well on MMLU may still fail at style-constrained generation tasks.

---

## Latency Benchmarks (HF Free Tier)

Measured on Qwen 2.5 7B via HuggingFace Serverless Inference:

| Run | Prompt tokens (approx) | Latency |
|---|---|---|
| 1 | ~1,200 | 7.9s |
| 2 | ~1,300 | 5.3s |

Variance is expected on shared free-tier infrastructure. For the report, note that free-tier latency is non-deterministic — a paid inference endpoint would reduce this to ~1–2s for the same model.

---

## Claude API Finding

Claude API (claude-sonnet-4-6) was integrated as a fallback but could not be tested — the API key had no credits. Claude.ai subscription does **not** include API access; they are billed separately. This is a common point of confusion worth noting in the report as a deployment gotcha.

**Hypothesis (untested):** Claude Sonnet would produce significantly better voice adherence than Qwen 7B on the same prompt. This can be validated once API credits are added and would make a strong model comparison section.

---

## Article Ingestion

**Library:** `trafilatura`
**Finding:** Worked on the first test URL with no configuration. Extracted clean article text, stripped navigation and ads. For the report, note it handles most modern web formats but may fail on paywalled content or JS-rendered pages (e.g. SPAs without SSR).

---

## Deployment Note

HuggingFace Spaces with Gradio provides a public URL at no cost. The app is mobile-accessible via browser — no separate mobile client needed for the assignment deliverable. This directly addresses the use case of capturing notes on the go without adding infrastructure complexity.

---

## Ideas That Were Cut (useful for Future Work section)

| Idea | Why cut | Worth revisiting? |
|---|---|---|
| Telegram note capture bot | Adds infra complexity, zero grade value | Yes — ~50 lines, Fly.io free tier |
| Local Mixtral 8x22B hosting | Hardware impossible (Intel UHD, 16GB RAM, no GPU) | Only if hardware upgrades |
| Dynamic model routing | Premature for v1 | Yes, once Claude fallback is active |
| One-click publish to Medium/Dev.to | Out of scope for assignment | Yes, strong v2 feature |
| LoRA fine-tune on Mistral 7B | Optional — adds report depth | Yes, Google Colab T4 free |
| Engagement analytics | Premature — need posting habit first | Yes, v3: track views/likes per post via platform APIs (Medium Stats API, LinkedIn Analytics API, Dev.to built-in), surface in a simple dashboard to close the feedback loop between "what I wrote" and "what resonated" |

---

## Kagi Translate — Zero-Auth LinkedIn Integration

**Finding:** Kagi Translate (`translate.kagi.com`) exposes a URL-parameter interface that pre-populates the translation form without requiring authentication. The `from` and `to` parameters accept non-standard language codes including `linkedin`, enabling style rewriting rather than language translation.

**Endpoint discovered:** `POST https://translate.kagi.com/api/translate` — returns `{"error":"Not authenticated"}` without a session. Kagi's public API key covers search only, not translate.

**Workaround:** Construct a URL with `?from=en&to=linkedin&text=<encoded>` and open it in a new tab. The page loads with the text pre-filled and runs the translation client-side. No API key, no scraping, no auth required.

**Implementation detail:** The input is the user's raw notes (not the full generated post). Notes are already short and capture the core idea — no additional summarization step needed. Trailing punctuation is stripped before encoding to prevent browser URL-parsing artifacts.

**Tested output** (input: *"Anthropic released a terminal pet feature on April Fools day. I hope I can add customization and it doesn't go away"*):
> 🚀 Anthropic just dropped a terminal pet feature for April Fools! 🐾 It's these kinds of innovative, out-of-the-box features that keep the tech community buzzing. 💡 I'm already thinking about the possibilities — I'd love to see some deep customization options added to the mix! 🛠️ #TechInnovation #ProductLaunch #DeveloperExperience

**Report angle:** Frame this as a creative integration pattern — using a web tool's URL interface as a lightweight API substitute when no official API exists. Relevant to the "Implementation Plan" and "Expected Outcomes" sections.
