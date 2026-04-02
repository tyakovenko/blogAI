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

- Paywalled and JS-rendered pages will fail silently — the app returns an error
- Qwen 7B (free tier) follows formatting rules imperfectly — expect headers and bullet points occasionally despite instructions. A Claude API backend (coming once credits are added) will fix this.
- The Telegram bot runs inside the HF Space — if the Space is sleeping, messages will not be received until the Space wakes up
