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
    "de": "d",
    "de-de": "d",
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
    "d": "de",
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
    "d": "German",
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
    "🇩🇪 🚺 Victoria": "df_victoria",
    "🇩🇪 🚹 Martin": "dm_martin",
}

STANDARD_MODEL_FAMILY = "kokoro-v1.0"

# German voice packs are tied to their fine-tuned checkpoint and cannot use the
# standard Kokoro weights. Only deployable inference files are listed here.
CUSTOM_VOICE_ASSETS = {
    "df_victoria": {
        "model_family": "kikiri-german-victoria",
        "repo_id": "kikiri-tts/kikiri-german-victoria",
        "voice_file": "voices/victoria.pt",
        "model_file": "kikiri_german_victoria_ep10.pth",
    },
    "dm_martin": {
        "model_family": "kikiri-german-martin",
        "repo_id": "kikiri-tts/kikiri-german-martin",
        "voice_file": "voices/martin.pt",
        "model_file": "kikiri_german_martin_ep10.pth",
    },
}

MODEL_FAMILY_CHOICES = {
    STANDARD_MODEL_FAMILY: {
        "name": "Kokoro v1.0 standard voices",
        "repo_id": DEFAULT_MODEL_REPO_ID,
    },
    "kikiri-german-martin": {
        "name": "Kikiri German Martin",
        "repo_id": "kikiri-tts/kikiri-german-martin",
    },
    "kikiri-german-victoria": {
        "name": "Kikiri German Victoria",
        "repo_id": "kikiri-tts/kikiri-german-victoria",
    },
}


def voice_ids() -> list[str]:
    return list(VOICE_CHOICES.values())


def voice_language(voice_id: str) -> str:
    if voice_id and voice_id[0] in LANGUAGE_CHOICES:
        return voice_id[0]
    return "a"


def voices_for_language(
    language_code: str, available_voices: list[str] | None = None
) -> list[str]:
    available = available_voices if available_voices is not None else voice_ids()
    return [
        voice_id
        for voice_id in available
        if voice_language(voice_id) == language_code
    ]


def voice_label(voice_id: str) -> str:
    return next(
        (label for label, value in VOICE_CHOICES.items() if value == voice_id), voice_id
    )


def voice_model_family(voice_id: str) -> str:
    asset = CUSTOM_VOICE_ASSETS.get(voice_id)
    return asset["model_family"] if asset else STANDARD_MODEL_FAMILY


def model_family_ids() -> list[str]:
    return list(MODEL_FAMILY_CHOICES)


def model_families_for_voices(voices: list[str]) -> list[str]:
    selected = {voice_model_family(voice_id) for voice_id in voices}
    return [family for family in model_family_ids() if family in selected]


def voices_for_model_families(families: list[str]) -> list[str]:
    selected = set(families)
    return [voice_id for voice_id in voice_ids() if voice_model_family(voice_id) in selected]


def model_family_inventory() -> list[dict[str, object]]:
    inventory = []
    for family, metadata in MODEL_FAMILY_CHOICES.items():
        voices = voices_for_model_families([family])
        language_codes = list(dict.fromkeys(voice_language(voice) for voice in voices))
        inventory.append(
            {
                "id": family,
                "name": metadata["name"],
                "repo_id": metadata["repo_id"],
                "voice_count": len(voices),
                "voices": voices,
                "languages": [
                    {"code": code, "name": LANGUAGE_CHOICES[code]}
                    for code in language_codes
                ],
            }
        )
    return inventory


def voice_inventory(available_voices: list[str] | None = None) -> list[dict[str, str]]:
    available = available_voices if available_voices is not None else voice_ids()
    return [
        {
            "id": voice_id,
            "name": voice_label(voice_id),
            "language": voice_language(voice_id),
            "language_name": LANGUAGE_CHOICES[voice_language(voice_id)],
        }
        for voice_id in available
    ]
