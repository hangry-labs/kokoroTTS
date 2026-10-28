"""Exercise both persisted chunking modes against a running TTS server."""

from __future__ import annotations

import argparse
import array
import io
import json
import sys
import tempfile
import time
import wave
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kokorotts import KokoroTTSClient


CASES = {
    "ja": ("jf_alpha", "「今日は良い天気ですね。」と彼女は言いました。次の文章も最後まで読み上げます。" * 8),
    "zh-standard": ("zf_xiaoxiao", "今天我们测试较长的中文内容，确认每一部分都能完整读出。下一句话也应该保留。" * 8),
    "zh-v11": ("zf_001", "今天我们测试较长的中文内容，确认每一部分都能完整读出。下一句话也应该保留。" * 8),
    "de": ("dm_martin", "Heute testen wir einen langen deutschen Text. Jede Aussage soll bis zum letzten Wort erhalten bleiben. " * 5),
    "vi": ("diem_trinh", "Hôm nay chúng tôi kiểm tra một đoạn văn dài. Mọi câu cần được đọc đầy đủ và rõ ràng. " * 5),
    "es": ("ef_dora", "Hoy probamos un texto largo con varias frases. Todas las palabras deben conservarse hasta el final. " * 5),
    "en": ("af_heart", "Today we test a longer passage with several sentences. Every word should remain clear until the end. " * 5),
}


def check_wav(content: bytes) -> float:
    with wave.open(io.BytesIO(content)) as audio:
        assert audio.getframerate() == 24_000
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        duration = audio.getnframes() / audio.getframerate()
        samples = array.array("h", audio.readframes(audio.getnframes()))
    assert duration > 1.0
    assert max(abs(sample) for sample in samples) > 50
    return duration


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:7860")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or Path(tempfile.mkdtemp(prefix="kokorotts-chunking-"))
    output.mkdir(parents=True, exist_ok=True)
    client = KokoroTTSClient(args.base_url, timeout=240)
    previous = client.deployment_settings()["chunking"]["experimental_natural_chunking"]
    results = []
    english = None
    try:
        for enabled in (False, True):
            mode = "natural" if enabled else "standard"
            client.set_experimental_natural_chunking(enabled)
            assert client.deployment_settings()["chunking"]["experimental_natural_chunking"] == enabled
            for name, (voice, text) in CASES.items():
                tokens = client.tokenize(text, voice)
                assert all(0 < len(ps) <= 510 for ps in tokens["segments"])
                assert tokens["metrics"]["characters"] == len(text)
                assert client.metrics(text, voice)["metrics"]["segments"] == len(tokens["segments"])
                if name == "en":
                    assert all(len(ps) <= 400 for ps in tokens["segments"])
                    if english is not None:
                        assert tokens["segments"] == english
                    english = tokens["segments"]
                started = time.monotonic()
                audio = client.generate(text, voice=voice, device=args.device)
                assert "x-kokorotts-fallback" not in audio.headers
                duration = check_wav(audio.content)
                audio.save(output / f"{mode}-{name}.wav")
                result = {
                    "mode": mode, "voice": voice, "segments": len(tokens["segments"]),
                    "phoneme_lengths": [len(ps) for ps in tokens["segments"]],
                    "audio_seconds": round(duration, 3),
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "device": audio.headers.get("x-kokorotts-inference-device"),
                }
                results.append(result)
                print(json.dumps(result), flush=True)

            dialogue = (
                '<speak><voice name="zf_001">'
                + CASES["zh-v11"][1][:160]
                + '</voice><break time="250ms"/><voice name="af_heart">'
                'Every sentence is still here.</voice><voice name="dm_martin">'
                'Und auch diese Stimme ist dabei.</voice></speak>'
            )
            audio = client.generate(dialogue, voice="zf_001", input_type="ssml", device=args.device)
            check_wav(audio.content)
            assert audio.headers["x-kokorotts-dialogue"] == "true"
            audio.save(output / f"{mode}-dialogue.wav")
            for label, text, voice, input_type in (
                ("ja", CASES["ja"][1], "jf_alpha", "text"),
                ("dialogue", dialogue, "zf_001", "ssml"),
            ):
                with client.iter_stream(
                    text, voice=voice, input_type=input_type,
                    device=args.device, stream_format="pcm_s16le",
                ) as stream:
                    content = b"".join(stream)
                assert len(content) > 48_000 and len(content) % 2 == 0
                assert max(abs(sample) for sample in array.array("h", content)) > 50
                print(f"PASS {mode} streamed PCM: {label}", flush=True)

            request = Request(
                args.base_url.rstrip("/") + "/v1/audio/speech",
                data=json.dumps({
                    "model": "kokoro", "input": CASES["zh-v11"][1][:160],
                    "voice": "zf_001", "response_format": "wav",
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urlopen(request, timeout=240) as response:
                check_wav(response.read())
            print(f"PASS {mode} SSML dialogue and OpenAI speech", flush=True)
    finally:
        client.set_experimental_natural_chunking(previous)
        (output / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"PASS both chunking modes; previous setting restored. Audio and results: {output}")


if __name__ == "__main__":
    main()
