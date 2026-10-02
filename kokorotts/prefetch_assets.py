import os

from huggingface_hub import hf_hub_download

from kokorotts.catalog import DEFAULT_MODEL_REPO_ID, MODEL_FILES, voice_ids

REPO_ID = os.getenv("KOKORO_REPO_ID", DEFAULT_MODEL_REPO_ID)

VOICE_IDS = voice_ids()


def main() -> None:
    if REPO_ID not in MODEL_FILES:
        supported = ", ".join(sorted(MODEL_FILES))
        raise ValueError(f"Unsupported KOKORO_REPO_ID '{REPO_ID}'. Supported: {supported}")

    files = [
        "config.json",
        MODEL_FILES[REPO_ID],
        *[f"voices/{voice_id}.pt" for voice_id in VOICE_IDS],
    ]

    for filename in files:
        print(f"Prefetching {REPO_ID}:{filename}")
        hf_hub_download(repo_id=REPO_ID, filename=filename)


if __name__ == "__main__":
    main()

