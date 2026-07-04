import os
from pathlib import Path


APP_TITLE = "GPT-SoVITS 实时录音克隆"
HOST = os.getenv("VOICE_CLONE_HOST", "127.0.0.1")
PORT = int(os.getenv("VOICE_CLONE_PORT", "7860"))

LANGUAGE = "zh_CN"
MODEL_VERSION = "v2ProPlus"
GPT_PATH = os.getenv("VOICE_CLONE_GPT_PATH", "GPT_SoVITS/pretrained_models/s1v3.ckpt")
SOVITS_PATH = os.getenv(
    "VOICE_CLONE_SOVITS_PATH",
    "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2ProPlus.pth",
)

DEFAULT_TARGET_TEXT = os.getenv("VOICE_CLONE_DEFAULT_TEXT", "你好黑客松")
MIN_REFERENCE_SECONDS = float(os.getenv("VOICE_CLONE_MIN_SECONDS", "3"))
MAX_REFERENCE_SECONDS = float(os.getenv("VOICE_CLONE_MAX_SECONDS", "10"))

TEMP_AUDIO_DIR = Path(os.getenv("VOICE_CLONE_TEMP_DIR", "TEMP/ref_audio_wav"))

DEFAULT_TOP_K = int(os.getenv("VOICE_CLONE_TOP_K", "20"))
DEFAULT_TOP_P = float(os.getenv("VOICE_CLONE_TOP_P", "0.6"))
DEFAULT_TEMPERATURE = float(os.getenv("VOICE_CLONE_TEMPERATURE", "0.6"))
DEFAULT_SPEED = float(os.getenv("VOICE_CLONE_SPEED", "1.0"))


def apply_environment():
    os.environ["language"] = LANGUAGE
    os.environ["version"] = MODEL_VERSION
    os.environ["gpt_path"] = GPT_PATH
    os.environ["sovits_path"] = SOVITS_PATH

