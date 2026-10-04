from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

PREFIX = "window.VOICE_EXAMPLES ="
ENGLISH_VOICES = {"af_maple", "af_sol", "bf_vale"}


def load_examples(path: Path) -> list[dict[str, str]]:
    source = path.read_text(encoding="utf-8").strip()
    if not source.startswith(PREFIX):
        raise ValueError(f"{path} does not define {PREFIX}")
    payload = source[len(PREFIX) :].strip().removesuffix(";").rstrip()
    examples = json.loads(payload)
    return [
        example
        for example in examples
        if example["voice"] in ENGLISH_VOICES
        or (
            example["voice"].startswith(("zf_", "zm_"))
            and example["voice"].split("_", 1)[1].isdigit()
        )
    ]


def generate(base_url: str, example: dict[str, str], output: Path, device: str) -> int:
    payload = json.dumps(
        {
            "text": example["text"],
            "voice": example["voice"],
            "device": device,
            "output_format": "mp3",
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/tts/generate",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        content = response.read()
        returned_voice = response.headers.get("X-KokoroTTS-Voice")
    if returned_voice != example["voice"]:
        raise RuntimeError(f"expected voice {example['voice']}, got {returned_voice}")
    if len(content) <= 10_000:
        raise RuntimeError(f"generated only {len(content)} bytes")

    temporary = output.with_suffix(f"{output.suffix}.pending")
    temporary.write_bytes(content)
    temporary.replace(output)
    return len(content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate v1.1 Chinese gallery audio")
    parser.add_argument("--base-url", default="http://localhost:7860")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--manifest", type=Path, default=Path("examples/voices.js"))
    parser.add_argument("--output-dir", type=Path, default=Path("examples"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    examples = load_examples(args.manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    skipped = 0
    total_bytes = 0
    for index, example in enumerate(examples, start=1):
        output = args.output_dir / example["file"]
        if output.is_file() and output.stat().st_size > 10_000 and not args.force:
            skipped += 1
            print(f"SKIP {index:03}/{len(examples)} {example['voice']}")
            continue

        for attempt in range(1, 4):
            try:
                size = generate(args.base_url, example, output, args.device)
                break
            except (OSError, RuntimeError, urllib.error.URLError) as exc:
                if attempt == 3:
                    raise RuntimeError(
                        f"failed to generate {example['voice']} after three attempts"
                    ) from exc
                time.sleep(attempt * 2)
        generated += 1
        total_bytes += size
        print(f"PASS {index:03}/{len(examples)} {example['voice']} ({size} bytes)")

    print(
        f"Chinese v1.1 examples complete: {generated} generated, {skipped} skipped, "
        f"{total_bytes} new bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
