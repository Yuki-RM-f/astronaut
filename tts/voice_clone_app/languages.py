TARGET_LANG_CHOICES = ["中文", "英文", "日文", "粤语", "韩文", "中英混合"]

_ALIASES = {
    "zh": "中文",
    "cn": "中文",
    "chinese": "中文",
    "en": "英文",
    "english": "英文",
    "ja": "日文",
    "jp": "日文",
    "japanese": "日文",
    "yue": "粤语",
    "cantonese": "粤语",
    "ko": "韩文",
    "kr": "韩文",
    "korean": "韩文",
    "韩语": "韩文",
}


def normalize_language(language, choices=TARGET_LANG_CHOICES):
    if isinstance(language, (int, float)):
        index = int(language)
        if 0 <= index < len(choices):
            return choices[index]

    if isinstance(language, str):
        value = language.strip()
        return _ALIASES.get(value.lower(), _ALIASES.get(value, value))

    return choices[0]

