# BlogAI — Extended Evaluation Study

**Study question:** Does a Claude Haiku edit pass rescue Qwen 2.5 7B's style failures on constrained blog synthesis tasks, and on which dimensions?

This extends the findings in `findings.md` from anecdotal observation to systematic measurement. The style constraint failure documented there (Qwen ignores structural rules across 4 prompt iterations) is the hypothesis under test.

---

## Conditions

Three outputs generated per input sample, holding the prompt constant across conditions:

| Label | Description |
|---|---|
| `qwen_raw` | Qwen 2.5 7B, strict style prompt, no edit pass |
| `haiku_only` | Claude Haiku, same strict style prompt, standalone |
| `qwen_haiku` | Qwen raw output → Claude Haiku edit pass |

The edit pass prompt instructs Haiku to enforce style constraints only — not to alter content, add information, or change the argument structure.

---

## Inputs

**Target:** 30–50 samples. Each sample: `{article_url, article_text, notes, domain}`.

Collect by logging real BlogAI usage. Do not synthesize inputs — authenticity matters for the voice preservation dimension.

**Minimum distribution:**
- 3–4 topic domains (tech, opinion, research summary, news)
- Mix of note styles: bullet fragments, full sentences, mixed
- At least 10 samples per domain

**Schema — `data/inputs.jsonl`:**
```json
{
  "id": "sample_001",
  "article_url": "https://...",
  "article_text": "...",
  "notes": "...",
  "domain": "tech"
}
```

---

## Metrics

All automated. No human participants required unless automated scores are ambiguous.

### 1. Style Adherence Score
**What:** Does the output use headers, bullet points, or listicle structure when the prompt forbids them?
**How:** Regex-based rubric counting structural violations. Score = `1 - (violations / max_violations)`, clipped to [0, 1].
**Violations tracked:** markdown headers (`##`, `###`), bullet points (`-`, `*`, numbered lists `1.`), bold section labels.

### 2. Source Coverage
**What:** What fraction of the source article's key points appear in the output?
**How:** BERTScore (F1) computed between output and `article_text`. Uses `bert-score` library, `roberta-large` backbone.

### 3. Note Integration
**What:** Do the user's notes actually shape the output?
**How:** Cosine similarity between sentence embeddings of `notes` and `output`. Uses `sentence-transformers`, `all-MiniLM-L6-v2`.

### 4. Factual Consistency
**What:** Does the output contradict the source article?
**How:** Split output into sentences. For each sentence, run NLI against source using `roberta-large-mnli`. Score = ratio of `entailment` labels to total sentences.

### 5. Latency
**What:** Generation time per condition.
**How:** Logged during generation in `01_generate.ipynb`. Reported as mean ± std per condition.

---

## File Structure

```
blogAI/
└── evals/
    ├── data/
    │   ├── inputs.jsonl
    │   └── outputs/
    │       ├── qwen_raw.jsonl        # {id, output, latency_s}
    │       ├── haiku_only.jsonl
    │       └── qwen_haiku.jsonl
    ├── eval/
    │   ├── style_rubric.py
    │   ├── coverage.py
    │   ├── note_integration.py
    │   ├── factual_consistency.py
    │   └── run_all.py                # → results/scores.csv
    ├── notebooks/
    │   ├── 01_generate.ipynb         # Colab — runs all 3 conditions
    │   ├── 02_evaluate.ipynb         # runs eval pipeline
    │   └── 03_analysis.ipynb         # plots, statistical tests, findings
    └── results/
        └── scores.csv                # condition × metric × sample_id
```

---

## Execution Sequence

1. **Collect inputs** — log 30–50 real BlogAI runs into `data/inputs.jsonl`
2. **Run `01_generate.ipynb`** on Colab — calls HF API (Qwen), Claude API (Haiku standalone), BlogAI pipeline (Qwen+Haiku). Saves to `data/outputs/`
3. **Run `02_evaluate.ipynb`** — runs all metrics, writes `results/scores.csv`
4. **Run `03_analysis.ipynb`** — per-metric deltas, Wilcoxon signed-rank tests (qwen_raw vs qwen_haiku, haiku_only vs qwen_haiku)
5. **Decision gate** — if style adherence delta is ambiguous (< 0.1 between conditions), recruit 10 people for preference ranking on a 10-sample subset

---

## Expected Findings

One of three outcomes, all defensible:

| Outcome | Implication |
|---|---|
| Haiku edit fixes style, hurts nothing | Pipeline justified — edit pass is worth the extra API call |
| Haiku edit fixes style, hurts factual consistency | Edit pass introduces drift — tradeoff documented |
| Haiku standalone outperforms pipeline | Skip Qwen — cost analysis follows |

The finding in `findings.md` (style failure is robust across 4 prompt iterations) predicts the first or second outcome. The third would require Qwen to be providing signal the Haiku-only condition can't replicate — possible if note integration scores diverge.

---

## Statistical Tests

Per metric, per comparison pair:
- **Wilcoxon signed-rank test** (non-parametric, paired) — appropriate for 30–50 samples, no normality assumption
- Report effect size (rank-biserial correlation) alongside p-values
- α = 0.05, no correction needed (3 pre-specified comparisons, not exploratory)
