import os
import re
import time
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from . import settings


def _mono_float_audio(audio_data):
    audio_data = np.asarray(audio_data)
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)

    if np.issubdtype(audio_data.dtype, np.integer):
        max_value = max(np.iinfo(audio_data.dtype).max, 1)
        return audio_data.astype(np.float32) / max_value

    audio_data = audio_data.astype(np.float32)
    max_abs = np.max(np.abs(audio_data)) if audio_data.size else 0
    if max_abs > 1:
        audio_data = audio_data / max_abs
    return audio_data


def _safe_stem(name):
    stem = re.sub(r"[^0-9A-Za-z_.-]+", "_", name).strip("_")
    return stem or "reference_audio"


def prepare_reference_audio(reference_audio):
    settings.TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    if isinstance(reference_audio, (str, os.PathLike)):
        source_path = Path(os.fspath(reference_audio))
        source_name = source_path.stem
        audio_data, sample_rate = librosa.load(str(source_path), sr=None, mono=True)
    elif isinstance(reference_audio, (tuple, list)) and len(reference_audio) == 2:
        sample_rate, audio_data = reference_audio
        source_name = "microphone"
        audio_data = _mono_float_audio(audio_data)
    else:
        raise ValueError("无法识别参考音频，请重新录制")

    if audio_data.size == 0:
        raise ValueError("参考音频为空，请重新录制")

    duration = len(audio_data) / float(sample_rate)
    if duration < settings.MIN_REFERENCE_SECONDS or duration > settings.MAX_REFERENCE_SECONDS:
        raise ValueError(
            f"参考音频时长是 {duration:.2f} 秒，请录制 "
            f"{settings.MIN_REFERENCE_SECONDS:g}-{settings.MAX_REFERENCE_SECONDS:g} 秒"
        )

    output_path = settings.TEMP_AUDIO_DIR / f"{_safe_stem(source_name)[:40]}_{int(time.time() * 1000)}.wav"
    sf.write(str(output_path), audio_data.astype(np.float32), int(sample_rate), subtype="PCM_16")
    return str(output_path), duration

