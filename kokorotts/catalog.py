"""Authoritative model, language, and voice metadata for KokoroTTS."""

DEFAULT_MODEL_REPO_ID = "hexgrad/Kokoro-82M"
CHINESE_V11_REPO_ID = "hexgrad/Kokoro-82M-v1.1-zh"
CHINESE_V11_REVISION = "01e7505bd6a7a2ac4975463114c3a7650a9f7218"

MODEL_FILES = {
    "hexgrad/Kokoro-82M": "kokoro-v1_0.pth",
    CHINESE_V11_REPO_ID: "kokoro-v1_1-zh.pth",
}

CHINESE_V11_MODEL_FAMILY = "kokoro-v1.1-zh"
CHINESE_V11_FEMALE_VOICES = (
    "zf_001",
    "zf_002",
    "zf_003",
    "zf_004",
    "zf_005",
    "zf_006",
    "zf_007",
    "zf_008",
    "zf_017",
    "zf_018",
    "zf_019",
    "zf_021",
    "zf_022",
    "zf_023",
    "zf_024",
    "zf_026",
    "zf_027",
    "zf_028",
    "zf_032",
    "zf_036",
    "zf_038",
    "zf_039",
    "zf_040",
    "zf_042",
    "zf_043",
    "zf_044",
    "zf_046",
    "zf_047",
    "zf_048",
    "zf_049",
    "zf_051",
    "zf_059",
    "zf_060",
    "zf_067",
    "zf_070",
    "zf_071",
    "zf_072",
    "zf_073",
    "zf_074",
    "zf_075",
    "zf_076",
    "zf_077",
    "zf_078",
    "zf_079",
    "zf_083",
    "zf_084",
    "zf_085",
    "zf_086",
    "zf_087",
    "zf_088",
    "zf_090",
    "zf_092",
    "zf_093",
    "zf_094",
    "zf_099",
)
CHINESE_V11_MALE_VOICES = (
    "zm_009",
    "zm_010",
    "zm_011",
    "zm_012",
    "zm_013",
    "zm_014",
    "zm_015",
    "zm_016",
    "zm_020",
    "zm_025",
    "zm_029",
    "zm_030",
    "zm_031",
    "zm_033",
    "zm_034",
    "zm_035",
    "zm_037",
    "zm_041",
    "zm_045",
    "zm_050",
    "zm_052",
    "zm_053",
    "zm_054",
    "zm_055",
    "zm_056",
    "zm_057",
    "zm_058",
    "zm_061",
    "zm_062",
    "zm_063",
    "zm_064",
    "zm_065",
    "zm_066",
    "zm_068",
    "zm_069",
    "zm_080",
    "zm_081",
    "zm_082",
    "zm_089",
    "zm_091",
    "zm_095",
    "zm_096",
    "zm_097",
    "zm_098",
    "zm_100",
)
CHINESE_V11_ENGLISH_VOICES = ("af_maple", "af_sol", "bf_vale")
CHINESE_V11_VOICE_IDS = (
    *CHINESE_V11_FEMALE_VOICES,
    *CHINESE_V11_MALE_VOICES,
    *CHINESE_V11_ENGLISH_VOICES,
)

LANGUAGE_ALIASES = {
    "en": "a",
    "en-us": "a",
    "en-gb": "b",
    "es": "e",
    "fr": "f",
    "fr-fr": "f",
    "hi": "h",
    "it": "i",
    "pt": "p",
    "pt-br": "p",
    "ja": "j",
    "zh": "z",
    "de": "d",
    "de-de": "d",
    "vi": "v",
    "vi-vn": "v",
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
    "v": "vi",
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
    "v": "Vietnamese",
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
    "🇻🇳 Diễm Trinh": "diem_trinh",
    "🇻🇳 Hưng Thịnh": "hung_thinh",
    "🇻🇳 Mai Linh": "mai_linh",
    "🇻🇳 Mai Loan": "mai_loan",
    "🇻🇳 Mạnh Dũng": "manh_dung",
    "🇻🇳 Mỹ Yến": "my_yen",
    "🇻🇳 Ngọc Huyền": "ngoc_huyen",
    "🇻🇳 Phát Tài": "phat_tai",
    "🇻🇳 Thành Đạt": "thanh_dat",
    "🇻🇳 Thục Trinh": "thuc_trinh",
    "🇻🇳 Tuấn Ngọc": "tuan_ngoc",
    "🇻🇳 Storyvert": "storyvert",
    "🇻🇳 Đức An": "duc_an",
    "🇻🇳 Đức Duy": "duc_duy",
    **{
        f"🇨🇳 🚺 v1.1 Speaker {voice_id.removeprefix('zf_')}": voice_id
        for voice_id in CHINESE_V11_FEMALE_VOICES
    },
    **{
        f"🇨🇳 🚹 v1.1 Speaker {voice_id.removeprefix('zm_')}": voice_id
        for voice_id in CHINESE_V11_MALE_VOICES
    },
    "🇺🇸 🚺 Maple (v1.1-zh)": "af_maple",
    "🇺🇸 🚺 Sol (v1.1-zh)": "af_sol",
    "🇬🇧 🚺 Vale (v1.1-zh)": "bf_vale",
}

STANDARD_MODEL_FAMILY = "kokoro-v1.0"
VIETNAMESE_MODEL_FAMILY = "contextboxai-kokoro-vietnamese"
VIETNAMESE_REPO_ID = "contextboxai/Kokoro-Vietnamese"

VIETNAMESE_VOICE_FILES = {
    "diem_trinh": "voicepacks/diem_trinh.pt",
    "hung_thinh": "voicepacks/hung_thinh.pt",
    "mai_linh": "voicepacks/mai_linh.pt",
    "mai_loan": "voicepacks/mai_loan.pt",
    "manh_dung": "voicepacks/manh_dung.pt",
    "my_yen": "voicepacks/my_yen.pt",
    "ngoc_huyen": "voicepacks/ngoc_huyen.pt",
    "phat_tai": "voicepacks/phat_tai.pt",
    "thanh_dat": "voicepacks/thanh_dat.pt",
    "thuc_trinh": "voicepacks/thuc_trinh.pt",
    "tuan_ngoc": "voicepacks/tuan_ngoc.pt",
    "storyvert": "voicepacks/storyvert.pt",
    "duc_an": "voicepacks/duc_an.pt",
    "duc_duy": "voicepacks/duc_duy.pt",
}

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
    **{
        voice_id: {
            "model_family": VIETNAMESE_MODEL_FAMILY,
            "repo_id": VIETNAMESE_REPO_ID,
            "voice_file": voice_file,
            "model_file": "kokoro_vi.pth",
            "config_file": "config.json",
            "language": "v",
        }
        for voice_id, voice_file in VIETNAMESE_VOICE_FILES.items()
    },
    **{
        voice_id: {
            "model_family": CHINESE_V11_MODEL_FAMILY,
            "repo_id": CHINESE_V11_REPO_ID,
            "voice_file": f"voices/{voice_id}.pt",
            "model_file": MODEL_FILES[CHINESE_V11_REPO_ID],
            "config_file": "config.json",
            "pipeline_repo_id": CHINESE_V11_REPO_ID,
            "revision": CHINESE_V11_REVISION,
        }
        for voice_id in CHINESE_V11_VOICE_IDS
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
    VIETNAMESE_MODEL_FAMILY: {
        "name": "Kokoro Vietnamese",
        "repo_id": VIETNAMESE_REPO_ID,
    },
    CHINESE_V11_MODEL_FAMILY: {
        "name": "Kokoro v1.1 Chinese",
        "repo_id": CHINESE_V11_REPO_ID,
    },
}


def voice_ids() -> list[str]:
    return list(VOICE_CHOICES.values())


def resolve_language_code(language: str) -> str:
    """Resolve a Kokoro code or BCP-47-style language tag."""
    normalized = language.strip().lower().replace("_", "-")
    if normalized in LANGUAGE_CHOICES:
        return normalized
    resolved = LANGUAGE_ALIASES.get(normalized)
    if resolved:
        return resolved
    base = normalized.partition("-")[0]
    resolved = LANGUAGE_ALIASES.get(base)
    if resolved:
        return resolved
    raise ValueError(f"Unsupported language '{language}'.")


def voice_language(voice_id: str) -> str:
    asset = CUSTOM_VOICE_ASSETS.get(voice_id)
    if asset and "language" in asset:
        return asset["language"]
    if voice_id and voice_id[0] in LANGUAGE_CHOICES:
        return voice_id[0]
    return "a"


def voices_for_language(
    language_code: str, available_voices: list[str] | None = None
) -> list[str]:
    available = available_voices if available_voices is not None else voice_ids()
    return [
        voice_id for voice_id in available if voice_language(voice_id) == language_code
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
    return [
        voice_id for voice_id in voice_ids() if voice_model_family(voice_id) in selected
    ]


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
