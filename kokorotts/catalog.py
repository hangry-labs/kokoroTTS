"""Authoritative model, language, and voice metadata for KokoroTTS."""

DEFAULT_MODEL_REPO_ID = "hexgrad/Kokoro-82M"

MODEL_FILES = {
    "hexgrad/Kokoro-82M": "kokoro-v1_0.pth",
    "hexgrad/Kokoro-82M-v1.1-zh": "kokoro-v1_1-zh.pth",
}

LANGUAGE_ALIASES = {
    "en-us": "a",
    "en-gb": "b",
    "es": "e",
    "fr-fr": "f",
    "hi": "h",
    "it": "i",
    "pt-br": "p",
    "ja": "j",
    "zh": "z",
}

# Values are the names expected by the corresponding G2P implementation.
PIPELINE_LANGUAGE_CODES = {
    "a": "American English",
    "b": "British English",
    "e": "es",
    "f": "fr-fr",
    "h": "hi",
    "i": "it",
    "p": "pt-br",
    "j": "Japanese",
    "z": "Mandarin Chinese",
}

# Public names presented by the UI and discovery API.
LANGUAGE_CHOICES = {
    "a": "American English",
    "b": "British English",
    "j": "Japanese",
    "z": "Mandarin Chinese",
    "e": "Spanish",
    "f": "French",
    "h": "Hindi",
    "i": "Italian",
    "p": "Brazilian Portuguese",
}

VOICE_CHOICES = {
    "🇺🇸 🚺 Heart ❤️": "af_heart",
    "🇺🇸 🚺 Bella 🔥": "af_bella",
    "🇺🇸 🚺 Nicole 🎧": "af_nicole",
    "🇺🇸 🚺 Aoede": "af_aoede",
    "🇺🇸 🚺 Kore": "af_kore",
    "🇺🇸 🚺 Sarah": "af_sarah",
    "🇺🇸 🚺 Nova": "af_nova",
    "🇺🇸 🚺 Sky": "af_sky",
    "🇺🇸 🚺 Alloy": "af_alloy",
    "🇺🇸 🚺 Jessica": "af_jessica",
    "🇺🇸 🚺 River": "af_river",
    "🇺🇸 🚹 Michael": "am_michael",
    "🇺🇸 🚹 Fenrir": "am_fenrir",
    "🇺🇸 🚹 Puck": "am_puck",
    "🇺🇸 🚹 Echo": "am_echo",
    "🇺🇸 🚹 Eric": "am_eric",
    "🇺🇸 🚹 Liam": "am_liam",
    "🇺🇸 🚹 Onyx": "am_onyx",
    "🇺🇸 🚹 Santa": "am_santa",
    "🇺🇸 🚹 Adam": "am_adam",
    "🇬🇧 🚺 Emma": "bf_emma",
    "🇬🇧 🚺 Isabella": "bf_isabella",
    "🇬🇧 🚺 Alice": "bf_alice",
    "🇬🇧 🚺 Lily": "bf_lily",
    "🇬🇧 🚹 George": "bm_george",
    "🇬🇧 🚹 Fable": "bm_fable",
    "🇬🇧 🚹 Lewis": "bm_lewis",
    "🇬🇧 🚹 Daniel": "bm_daniel",
    "🇯🇵 🚺 Alpha": "jf_alpha",
    "🇯🇵 🚺 Gongitsune": "jf_gongitsune",
    "🇯🇵 🚺 Nezumi": "jf_nezumi",
    "🇯🇵 🚺 Tebukuro": "jf_tebukuro",
    "🇯🇵 🚹 Kumo": "jm_kumo",
    "🇨🇳 🚺 Xiaobei": "zf_xiaobei",
    "🇨🇳 🚺 Xiaoni": "zf_xiaoni",
    "🇨🇳 🚺 Xiaoxiao": "zf_xiaoxiao",
    "🇨🇳 🚺 Xiaoyi": "zf_xiaoyi",
    "🇨🇳 🚹 Yunjian": "zm_yunjian",
    "🇨🇳 🚹 Yunxi": "zm_yunxi",
    "🇨🇳 🚹 Yunxia": "zm_yunxia",
    "🇨🇳 🚹 Yunyang": "zm_yunyang",
    "🇪🇸 🚺 Dora": "ef_dora",
    "🇪🇸 🚹 Alex": "em_alex",
    "🇪🇸 🚹 Santa": "em_santa",
    "🇫🇷 🚺 Siwis": "ff_siwis",
    "🇮🇳 🚺 Alpha": "hf_alpha",
    "🇮🇳 🚺 Beta": "hf_beta",
    "🇮🇳 🚹 Omega": "hm_omega",
    "🇮🇳 🚹 Psi": "hm_psi",
    "🇮🇹 🚺 Sara": "if_sara",
    "🇮🇹 🚹 Nicola": "im_nicola",
    "🇧🇷 🚺 Dora": "pf_dora",
    "🇧🇷 🚹 Alex": "pm_alex",
    "🇧🇷 🚹 Santa": "pm_santa",
}


def voice_ids() -> list[str]:
    return list(VOICE_CHOICES.values())


def voice_language(voice_id: str) -> str:
    if voice_id and voice_id[0] in LANGUAGE_CHOICES:
        return voice_id[0]
    return "a"


def voices_for_language(language_code: str) -> list[str]:
    return [
        voice_id
        for voice_id in voice_ids()
        if voice_language(voice_id) == language_code
    ]


def voice_label(voice_id: str) -> str:
    return next(
        (label for label, value in VOICE_CHOICES.items() if value == voice_id), voice_id
    )


def voice_inventory() -> list[dict[str, str]]:
    return [
        {
            "id": voice_id,
            "name": voice_label(voice_id),
            "language": voice_language(voice_id),
            "language_name": LANGUAGE_CHOICES[voice_language(voice_id)],
        }
        for voice_id in voice_ids()
    ]
