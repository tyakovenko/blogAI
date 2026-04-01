"""
BlogAI — Gradio web interface.
Entry point for HuggingFace Spaces and local development.
"""

import gradio as gr
from app.pipeline import generate_post


def run_pipeline(url: str, notes: str, tone: str) -> tuple[str, str]:
    """Gradio handler. Returns (post_draft, status_line)."""
    if not url.strip():
        return "", "Please enter an article URL."
    if not notes.strip():
        return "", "Please add at least a few notes or reflections."

    try:
        result = generate_post(url.strip(), notes.strip(), tone)
        status = f"Generated with **{result['model_used']}** in {result['latency']}s"
        return result["post"], status
    except ValueError as e:
        return "", f"Error: {e}"
    except Exception as e:
        return "", f"Unexpected error: {e}"


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
                choices=["blog_social", "professional", "academic"],
                value="blog_social",
                label="Tone",
            )
            generate_btn = gr.Button("Generate draft", variant="primary")

        with gr.Column(scale=1):
            post_output = gr.Textbox(
                label="Blog post draft",
                lines=20,
            )
            status_output = gr.Markdown("")

    generate_btn.click(
        fn=run_pipeline,
        inputs=[url_input, notes_input, tone_selector],
        outputs=[post_output, status_output],
    )

    gr.Markdown(
        "---\n"
        "**Future:** Telegram note capture · One-click publish to Medium / Dev.to"
    )


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
