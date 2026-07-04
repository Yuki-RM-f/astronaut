import gradio as gr

from . import settings
from .languages import TARGET_LANG_CHOICES
from .service import synthesize


def build_demo():
    with gr.Blocks(title=settings.APP_TITLE) as demo:
        gr.Markdown(f"# {settings.APP_TITLE}")

        with gr.Row():
            with gr.Column(scale=1):
                reference_audio = gr.Audio(
                    source="microphone",
                    type="numpy",
                    label="参考录音（3-10秒）",
                )

            with gr.Column(scale=1):
                target_text = gr.Textbox(
                    label="合成文本",
                    value=settings.DEFAULT_TARGET_TEXT,
                    lines=4,
                )
                target_language = gr.Dropdown(
                    choices=TARGET_LANG_CHOICES,
                    value="中文",
                    type="index",
                    label="目标语言",
                )

                with gr.Accordion("参数", open=False):
                    top_k = gr.Slider(1, 30, value=settings.DEFAULT_TOP_K, step=1, label="Top-K")
                    top_p = gr.Slider(0.1, 1.0, value=settings.DEFAULT_TOP_P, step=0.05, label="Top-P")
                    temperature = gr.Slider(
                        0.1,
                        1.0,
                        value=settings.DEFAULT_TEMPERATURE,
                        step=0.05,
                        label="温度",
                    )
                    speed = gr.Slider(0.6, 1.65, value=settings.DEFAULT_SPEED, step=0.05, label="语速")

                synthesize_button = gr.Button("开始合成", variant="primary", size="lg")

        output_audio = gr.Audio(label="合成结果", type="numpy")
        status = gr.Textbox(label="状态", interactive=False)

        synthesize_button.click(
            synthesize,
            [reference_audio, target_text, target_language, top_k, top_p, temperature, speed],
            [output_audio, status],
        )

    return demo

