import threading
import traceback

from tools.i18n.i18n import I18nAuto

from . import settings
from .audio import prepare_reference_audio
from .languages import TARGET_LANG_CHOICES, normalize_language


settings.apply_environment()

from GPT_SoVITS.inference_webui import change_gpt_weights, change_sovits_weights, get_tts_wav


_i18n = I18nAuto(language=settings.LANGUAGE)
_lock = threading.Lock()
_models_loaded = True


def _load_models_if_needed():
    global _models_loaded
    if _models_loaded:
        return

    generator = change_sovits_weights(
        sovits_path=settings.SOVITS_PATH,
        prompt_language=_i18n("中文"),
        text_language=_i18n("中文"),
    )
    for _ in generator:
        pass
    change_gpt_weights(gpt_path=settings.GPT_PATH)
    _models_loaded = True


def synthesize(reference_audio, target_text, target_language, top_k, top_p, temperature, speed):
    try:
        if reference_audio is None:
            return None, "请先录制参考音频"

        target_text = (target_text or "").strip()
        if not target_text:
            return None, "请输入要合成的文字"

        with _lock:
            _load_models_if_needed()
            reference_path, duration = prepare_reference_audio(reference_audio)
            result = list(
                get_tts_wav(
                    ref_wav_path=reference_path,
                    prompt_text="",
                    prompt_language=_i18n("中文"),
                    text=target_text,
                    text_language=_i18n(normalize_language(target_language, TARGET_LANG_CHOICES)),
                    top_k=int(top_k),
                    top_p=float(top_p),
                    temperature=float(temperature),
                    speed=float(speed),
                )
            )

        if not result:
            return None, "合成失败"

        sample_rate, audio = result[-1]
        return (sample_rate, audio), f"合成完成，参考音频 {duration:.2f} 秒"
    except Exception as exc:
        return None, f"错误: {exc}\n{traceback.format_exc()}"

