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

You read something interesting. You have thoughts. BlogAI turns that combination into a draft blog post and LinkedIn post — in your voice, ready to edit and publish.

Built with Gradio + Qwen 2.5 7B via HuggingFace Inference API.

---

## What this is for

You already read articles and have opinions about them. BlogAI removes the gap between "I should write about this" and an actual draft. The use case is personal brand building — posting consistently without the blank page problem.

The core loop:
1. Read something on your phone → send the URL + your reaction to the Telegram bot
2. Later, open BlogAI → paste the URL and your notes → generate a blog post and LinkedIn draft
3. Edit, approve, post

---

## What this is NOT for

- **Writing from scratch** — BlogAI needs an article URL and your notes as input. It is not a general writing assistant.
- **Paywalled or JS-heavy articles** — NYT, Bloomberg, most major newspapers require subscriptions. The app will fail to fetch those. Use open-access sources (Wikipedia, dev blogs, newsletters, arXiv, company announcement pages).
- **Publishing directly** — BlogAI generates drafts. It does not post to Medium, LinkedIn, or anywhere else. Copy, edit, post manually.
- **Replacing your voice** — the draft is a starting point. The model (Qwen 7B) will follow your notes but may drift from your exact style. Always edit before posting.

---

## How to use

### Capture (mobile — recommended)

Send a single message to [@tayapb_bot](https://t.me/tayapb_bot) on Telegram:

```
https://example.com/article-you-read

Your raw reaction here. As rough as you want.
Can be multiple lines.
```

The bot extracts the first URL it finds and treats the rest as your notes. It saves both to your Notion drafts queue with status **Inbox**.

If you have no URL yet — notes only is fine too. The bot will save them without a link.

### Generate (web app)

1. Open the BlogAI Space
2. Paste the article URL and your notes
3. Pick a tone (Blog / Social is the default)
4. Click **Generate draft**

You get two outputs:
- **Blog Post** — 300–500 words, personal voice, plain paragraphs
- **LinkedIn** — 150–250 words, hook opening, single closing question

The LinkedIn-ify button (experimental) is a separate tool — it sends your raw notes to Kagi Translate for a different style rewrite. Not the same as the LinkedIn draft above.

### Tone options

| Tone | Best for |
|---|---|
| Blog / Social | Personal posts, casual takes, dev blog |
| Professional | Work-adjacent writing, industry commentary |
| Academic | Structured analysis, course work adjacent |

---

## Known limitations

- **Telegram requires the HF Space to be awake.** The bot runs as a background thread inside the HF Space process. If the Space goes idle (~15 min of no web traffic on free tier), the thread dies and incoming messages are silently dropped — no error, no notification, no retry. To wake it: visit the Space URL before sending messages. For reliable always-on capture: (a) pipe Telegram → Notion via Make.com or Zapier (free tier, no code); (b) migrate the bot to a webhook deploy on Render or Fly.io independent of the Space.
- Paywalled and JS-rendered pages will fail — the app returns an error. Open-access sources (dev blogs, newsletters, arXiv, company pages) work fine.
- Generation model quality varies — HF free tier models follow formatting rules imperfectly. Falls back to Claude Haiku automatically if HF Inference is unavailable (requires `ANTHROPIC_API_KEY` set in Space secrets).
- The app generates drafts only — it does not post to Medium, LinkedIn, or anywhere else.
