---
title: BlogAI
emoji: ✍️
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.10.0
app_file: app.py
pinned: false
short_description: Turn an article + your notes into a blog post draft
---

# BlogAI

You read something interesting. You have thoughts. BlogAI turns that combination into a draft blog post and LinkedIn post, in your voice, ready to edit and publish.

Built with Gradio + Qwen 2.5 7B via HuggingFace Inference API.

**[Live on HuggingFace Spaces](https://huggingface.co/spaces/tyakovenko/blogAI)**

---

## What it's for

You already read articles and have opinions about them. BlogAI closes the gap between "I should write about this" and an actual draft, so you can post consistently without the blank-page problem.

The loop:
1. Read something on your phone, send the URL plus your reaction to the Telegram bot.
2. Later, open BlogAI, paste the URL and your notes, generate a blog post and a LinkedIn draft.
3. Edit, approve, post.

It takes an article and your notes as input, so it isn't a from-scratch writing assistant, and it drafts rather than publishes. Limits worth knowing up front are at the bottom.

---

## How to use

### Capture (mobile, recommended)

Send a single message to [@tayapb_bot](https://t.me/tayapb_bot) on Telegram:

```
https://example.com/article-you-read

Your raw reaction here. As rough as you want.
Can be multiple lines.
```

The bot extracts the first URL it finds and treats the rest as your notes. It saves both to your Notion drafts queue with status **Inbox**.

No URL yet? Notes only is fine; the bot saves them without a link.

### Generate (web app, HuggingFace)

1. Open the BlogAI Space
2. Paste the article URL and your notes
3. Pick a tone (Blog / Social is the default)
4. Click **Generate draft**

### Run locally

```bash
git clone https://github.com/tyakovenko/blogAI.git
cd blogAI
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export HF_TOKEN=your_hf_token
export ANTHROPIC_API_KEY=your_anthropic_key  # optional fallback
python app.py
```

Opens at `http://localhost:7860`. No `GRADIO_SHARE` needed; the tunnel is only enabled on HF Spaces.

You get two outputs:
- **Blog Post**: 300–500 words, personal voice, plain paragraphs
- **LinkedIn**: 150–250 words, hook opening, single closing question

The LinkedIn-ify button (experimental) is a separate tool: it sends your raw notes to Kagi Translate for a different style rewrite, not the same as the LinkedIn draft above.

### Tone options

| Tone | Best for |
|---|---|
| Blog / Social | Personal posts, casual takes, dev blog |
| Professional | Work-adjacent writing, industry commentary |
| Academic | Structured analysis, course work adjacent |

---

## Known limitations

- **Telegram requires the HF Space to be awake.** The bot runs as a background thread inside the HF Space process. If the Space goes idle (~15 min of no web traffic on free tier), the thread dies and incoming messages are silently dropped, with no error, notification, or retry. To wake it, visit the Space URL before sending messages. For reliable always-on capture: (a) pipe Telegram → Notion via Make.com or Zapier (free tier, no code); (b) migrate the bot to a webhook deploy on Render or Fly.io independent of the Space.
- Paywalled and JS-rendered pages fail; the app returns an error. Open-access sources (dev blogs, newsletters, arXiv, company pages) work fine.
- Generation quality varies; HF free-tier models follow formatting rules imperfectly. Falls back to Claude Haiku automatically if HF Inference is unavailable (requires `ANTHROPIC_API_KEY` set in Space secrets).

---

## Evaluation

The Qwen→Haiku pipeline was evaluated on 27 samples across two output modes (blog, LinkedIn) against Haiku standalone and Qwen standalone baselines. The pipeline outperforms Haiku standalone on substance fidelity (significantly on LinkedIn: 0.663 vs. 0.624, p=0.030) and substantially on voice fidelity (Tier 2 structural score: 0.956 vs. 0.800). The LinkedIn edit pass costs 38% less than standalone Haiku generation.

Full methodology, results, and data: [blogAI_evals](https://github.com/tyakovenko/blogAI_evals)
