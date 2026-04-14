"""
BlogAI — Gradio web interface.
Entry point for HuggingFace Spaces and local development.
"""

import gradio as gr
from app.pipeline import generate_post, build_linkedin_url
from app.config import TONES, DEFAULT_TONE, OUTPUT_FORMATS, AVAILABLE_MODELS, DEFAULT_MODEL_KEY
from bot.bot import start_polling_in_background


def run_pipeline(url: str, notes: str, tone: str, model_key: str) -> tuple:
    """Gradio handler. Returns (*drafts_in_format_order, status_line)."""
    empty = ("",) * len(OUTPUT_FORMATS)

    if not url.strip():
        return empty + ("Please enter an article URL.",)

    try:
        result = generate_post(url.strip(), notes.strip(), tone, model_key=model_key)
        status = f"Generated with **{result['model_used']}** in {result['latency']}s"
        if result.get("auto_notes"):
            status += f"\n\n*No notes provided — used AI summary:*\n{result['auto_notes']}"
        drafts = tuple(result["drafts"].get(fmt, "") for fmt in OUTPUT_FORMATS)
        return drafts + (status,)
    except ValueError as e:
        return empty + (f"Error: {e}",)
    except Exception as e:
        return empty + (f"Unexpected error: {e}",)


with gr.Blocks(title="BlogAI") as demo:
    gr.Markdown("# BlogAI\nTurn an article + your notes into a polished blog post draft.")

    with gr.Row():
        with gr.Column(scale=1):
            url_input = gr.Textbox(
                label="Article URL",
                placeholder="https://example.com/article",
            )
            notes_input = gr.Textbox(
                label="Your notes & reflections",
                placeholder="Paste your rough notes, highlights, or thoughts here...",
                lines=8,
            )
            tone_selector = gr.Radio(
                choices=list(TONES.keys()),
                value=DEFAULT_TONE,
                label="Tone",
            )
            model_selector = gr.Dropdown(
                choices=list(AVAILABLE_MODELS.keys()),
                value=DEFAULT_MODEL_KEY,
                label="Model",
            )
            generate_btn = gr.Button("Generate draft", variant="primary")

        with gr.Column(scale=1):
            output_boxes = [
                gr.Textbox(
                    label=fmt,
                    lines=15 if i == 0 else 8,
                )
                for i, fmt in enumerate(OUTPUT_FORMATS)
            ]
            status_output = gr.Markdown("")
            linkedin_link = gr.HTML("")
            with gr.Row():
                linkedin_btn = gr.Button("LinkedIn-ify via Kagi ↗", variant="secondary")
            gr.Markdown("<div style='text-align:center'>✨ experimental ✨</div>")

    def make_linkedin_link(notes: str) -> str:
        if not notes.strip():
            return ""
        url = build_linkedin_url(notes)
        return f'<a href="{url}" target="_blank" style="font-size:14px">Open in Kagi Translate ↗</a>'

    generate_btn.click(
        fn=run_pipeline,
        inputs=[url_input, notes_input, tone_selector, model_selector],
        outputs=output_boxes + [status_output],
    )

    linkedin_btn.click(
        fn=make_linkedin_link,
        inputs=[notes_input],
        outputs=[linkedin_link],
    )

    gr.Markdown(
        "---\n"
        "**Future:** Telegram note capture · One-click publish to Medium / Dev.to · Engagement analytics"
    )


start_polling_in_background()

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
