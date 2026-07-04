import sys
import soundfile as sf
from tools.i18n.i18n import I18nAuto
from GPT_SoVITS.inference_webui import change_gpt_weights, change_sovits_weights, get_tts_wav

i18n = I18nAuto()

GPT_PATH = "GPT_SoVITS/pretrained_models/s1v3.ckpt"
SOVITS_PATH = "GPT_SoVITS/pretrained_models/s2Gv3.pth"


def tts(ref_audio, ref_text, ref_lang, target_text, target_lang, output="output.wav"):
    print(f"Loading GPT model: {GPT_PATH}")
    change_gpt_weights(gpt_path=GPT_PATH)
    print(f"Loading SoVITS model: {SOVITS_PATH}")
    change_sovits_weights(sovits_path=SOVITS_PATH)

    print(f"Reference: {ref_audio}")
    print(f"Synthesizing: {target_text}")
    result = list(get_tts_wav(
        ref_wav_path=ref_audio,
        prompt_text=ref_text,
        prompt_language=i18n(ref_lang),
        text=target_text,
        text_language=i18n(target_lang),
        top_p=1,
        temperature=1,
    ))

    if result:
        sr, audio = result[-1]
        sf.write(output, audio, sr)
        print(f"Saved to {output}")
    else:
        print("Synthesis failed!")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python quick_tts.py <ref_audio.wav> <ref_text> <target_text> [ref_lang] [target_lang] [output]")
        print("Example: python quick_tts.py my_voice.wav '大家好我是小明' '今天天气真不错' 中文 中文 output.wav")
        sys.exit(1)

    ref_audio = sys.argv[1]
    ref_text = sys.argv[2]
    target_text = sys.argv[3]
    ref_lang = sys.argv[4] if len(sys.argv) > 4 else "中文"
    target_lang = sys.argv[5] if len(sys.argv) > 5 else "中文"
    output = sys.argv[6] if len(sys.argv) > 6 else "output.wav"

    tts(ref_audio, ref_text, ref_lang, target_text, target_lang, output)
