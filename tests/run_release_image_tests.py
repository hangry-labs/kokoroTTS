"""Qualify packaged KokoroTTS HTTP inference across every shipped model family."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


EXPECTED_MODEL_FAMILIES = {
    "kokoro-v1.0",
    "kikiri-german-martin",
    "kikiri-german-victoria",
    "contextboxai-kokoro-vietnamese",
    "kokoro-v1.1-zh",
}


@dataclass(frozen=True)
class SynthesisCase:
    name: str
    voice: str
    language: str
    model_family: str
    text: str


CASES = (
    SynthesisCase("american_english", "af_heart", "a", "kokoro-v1.0", "Release qualification is ready."),
    SynthesisCase("british_english", "bf_emma", "b", "kokoro-v1.0", "Release qualification is ready."),
    SynthesisCase("japanese", "jf_alpha", "j", "kokoro-v1.0", "\u30ea\u30ea\u30fc\u30b9\u5019\u88dc\u306e\u97f3\u58f0\u30c6\u30b9\u30c8\u3067\u3059\u3002"),
    SynthesisCase("standard_chinese", "zf_xiaoxiao", "z", "kokoro-v1.0", "\u8fd9\u662f\u53d1\u5e03\u5019\u9009\u7248\u7684\u8bed\u97f3\u6d4b\u8bd5\u3002"),
    SynthesisCase("spanish", "ef_dora", "e", "kokoro-v1.0", "Esta es la prueba de audio de la version candidata."),
    SynthesisCase("french", "ff_siwis", "f", "kokoro-v1.0", "Ceci est le test audio de la version candidate."),
    SynthesisCase("hindi", "hf_alpha", "h", "kokoro-v1.0", "\u092f\u0939 \u0930\u093f\u0932\u0940\u091c\u093c \u0909\u092e\u094d\u092e\u0940\u0926\u0935\u093e\u0930 \u0915\u093e \u0911\u0921\u093f\u092f\u094b \u092a\u0930\u0940\u0915\u094d\u0937\u0923 \u0939\u0948\u0964"),
    SynthesisCase("italian", "if_sara", "i", "kokoro-v1.0", "Questo e il test audio della versione candidata."),
    SynthesisCase("portuguese", "pf_dora", "p", "kokoro-v1.0", "Este e o teste de audio da versao candidata."),
    SynthesisCase("german_martin", "dm_martin", "d", "kikiri-german-martin", "Dies ist der Audiotest des Release-Kandidaten."),
    SynthesisCase("german_victoria", "df_victoria", "d", "kikiri-german-victoria", "Dies ist der Audiotest des Release-Kandidaten."),
    SynthesisCase("vietnamese", "diem_trinh", "v", "contextboxai-kokoro-vietnamese", "\u0110\u00e2y l\u00e0 b\u00e0i ki\u1ec3m tra \u00e2m thanh cho b\u1ea3n ph\u00e1t h\u00e0nh."),
    SynthesisCase("enhanced_chinese", "zf_001", "z", "kokoro-v1.1-zh", "\u8fd9\u662f\u589e\u5f3a\u4e2d\u6587\u6a21\u578b\u7684\u53d1\u5e03\u6d4b\u8bd5\u3002"),
)


def request_json(base_url: str, path: str) -> dict:
    with urlopen(f"{base_url}{path}", timeout=30) as response:
        return json.load(response)


def wait_until_ready(base_url: str, timeout_seconds: int) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            payload = request_json(base_url, "/health/ready")
            if payload.get("status") == "ok":
                return payload
        except (HTTPError, URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
        time.sleep(2)
    raise RuntimeError(
        f"KokoroTTS did not become ready within {timeout_seconds}s: {last_error}"
    )


def synthesize(base_url: str, case: SynthesisCase) -> None:
    body = json.dumps(
        {
            "text": case.text,
            "voice": case.voice,
            "device": "cuda:0",
            "output_format": "mp3",
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        f"{base_url}/tts/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=300) as response:
        audio = response.read()
        headers = response.headers

    assert len(audio) >= 1_000, f"{case.name}: generated only {len(audio)} bytes"
    assert headers.get_content_type() == "audio/mpeg", (
        f"{case.name}: unexpected content type {headers.get_content_type()}"
    )
    assert headers.get("X-KokoroTTS-Voice") == case.voice, (
        f"{case.name}: wrong voice header {headers.get('X-KokoroTTS-Voice')}"
    )
    assert headers.get("X-KokoroTTS-Language") == case.language, (
        f"{case.name}: wrong language header {headers.get('X-KokoroTTS-Language')}"
    )
    assert headers.get("X-KokoroTTS-Inference-Device") == "cuda:0", (
        f"{case.name}: inference did not stay on cuda:0: "
        f"{headers.get('X-KokoroTTS-Inference-Device')}"
    )
    assert headers.get("X-KokoroTTS-Fallback") is None, (
        f"{case.name}: inference fell back to CPU"
    )
    print(
        f"PASS {case.name}: voice={case.voice} family={case.model_family} "
        f"bytes={len(audio)} device=cuda:0",
        flush=True,
    )


def qualify(base_url: str, timeout_seconds: int) -> None:
    ready = wait_until_ready(base_url, timeout_seconds)
    assert ready.get("voices") == 173, f"expected 173 served voices, got {ready}"
    print("PASS readiness: 173 voices", flush=True)

    settings = request_json(base_url, "/system/settings")
    served_families = set(settings.get("served_model_families") or [])
    assert served_families == EXPECTED_MODEL_FAMILIES, (
        f"unexpected served model families: {sorted(served_families)}"
    )
    print("PASS settings: all five model families enabled", flush=True)

    for case in CASES:
        synthesize(base_url, case)

    status = request_json(base_url, "/tts/status")
    loaded_families = {
        item["model_family"] for item in status.get("loaded_models") or []
    }
    assert loaded_families == EXPECTED_MODEL_FAMILIES, (
        f"unexpected loaded model families: {sorted(loaded_families)}"
    )
    assert status.get("last_inference_fallback") is None, status.get(
        "last_inference_fallback"
    )
    assert status.get("build_date"), "image is missing build_date"
    assert status.get("revision"), "image is missing revision"
    print(
        "PASS lifecycle: all five model families loaded without fallback; "
        f"build={status['build_date']}@{status['revision']}",
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:7860")
    parser.add_argument("--ready-timeout", type=int, default=300)
    args = parser.parse_args()
    qualify(args.base_url.rstrip("/"), args.ready_timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
