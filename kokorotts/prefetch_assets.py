import os

from huggingface_hub import hf_hub_download

from kokorotts.catalog import (
    CUSTOM_VOICE_ASSETS,
    DEFAULT_MODEL_REPO_ID,
    MODEL_FILES,
    voice_ids,
)

REPO_ID = os.getenv("KOKORO_REPO_ID", DEFAULT_MODEL_REPO_ID)

VOICE_IDS = voice_ids()


def main() -> None:
    if REPO_ID not in MODEL_FILES:
        supported = ", ".join(sorted(MODEL_FILES))
        raise ValueError(f"Unsupported KOKORO_REPO_ID '{REPO_ID}'. Supported: {supported}")

    files = [
        "config.json",
        MODEL_FILES[REPO_ID],
        *[
            f"voices/{voice_id}.pt"
            for voice_id in VOICE_IDS
            if voice_id not in CUSTOM_VOICE_ASSETS
        ],
    ]

    for filename in files:
        print(f"Prefetching {REPO_ID}:{filename}")
        hf_hub_download(repo_id=REPO_ID, filename=filename)

    for asset in CUSTOM_VOICE_ASSETS.values():
        for filename in (asset["model_file"], asset["voice_file"]):
            print(f"Prefetching {asset['repo_id']}:{filename}")
            hf_hub_download(repo_id=asset["repo_id"], filename=filename)


if __name__ == "__main__":
    main()

