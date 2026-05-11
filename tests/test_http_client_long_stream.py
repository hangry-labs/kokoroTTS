"""Server-backed smoke tests for the KokoroTTS HTTP client.

These tests expect a running KokoroTTS server. Start one with:

    task localrun

The tests are intentionally outside the Docker image build context.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from kokorotts import KokoroTTSClient, KokoroTTSClientError


BASE_URL = os.getenv("KOKOROTTS_TEST_BASE_URL", "http://localhost:7860")

LONG_ENGLISH_TEXT = (
    "KokoroTTS is reading a longer passage so we can check streamed audio across "
    "multiple chunks. The text keeps going for a while, with complete sentences, "
    "short pauses, and enough words to exercise the pipeline. A developer might "
    "send a paragraph like this from an application, then save the returned audio "
    "as an MP3 for a tutorial, a notification, or a friendly product demo. "
    "Streaming should return useful audio without dropping the second half of the "
    "message, even when the text is longer than a tiny hello world. "
) * 4

LONG_SPANISH_TEXT = (
    "Hola desde KokoroTTS. Esta es una prueba larga para revisar la salida en "
    "streaming con texto en espanol. Queremos confirmar que el sistema divide el "
    "contenido, genera audio completo, y devuelve suficientes datos para que una "
    "aplicacion pueda reproducir o guardar el resultado sin sorpresas. "
) * 4


class HttpClientServerSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = KokoroTTSClient(BASE_URL, timeout=240)
        try:
            cls.client.ping()
        except Exception as exc:  # pragma: no cover - only used for local smoke gating
            raise unittest.SkipTest(f"KokoroTTS server is not available at {BASE_URL}: {exc}") from exc

    def test_tts_ping_returns_service_health(self) -> None:
        ping = self.client.ping()
        self.assertEqual(ping["msg"], "pong")

    def test_tts_status_returns_runtime_metadata(self) -> None:
        status = self.client.status()
        self.assertEqual(status["type"], "KokoroTTS")
        self.assertGreaterEqual(status["voices"], 54)

    def test_tts_defaults_returns_default_request_values(self) -> None:
        defaults = self.client.defaults()
        self.assertEqual(defaults["voice"], "af_heart")
        self.assertEqual(defaults["audio_controls"]["tempo"], 1.0)

    def test_tts_formats_lists_output_formats(self) -> None:
        formats = self.client.formats()
        self.assertIn("mp3", formats["formats"])
        self.assertIn("wav", formats["formats"])

    def test_tts_stream_formats_lists_stream_formats(self) -> None:
        stream_formats = self.client.stream_formats()
        self.assertIn("pcm_s16le", stream_formats["formats"])
        self.assertIn("mp3", stream_formats["formats"])

    def test_tts_languages_lists_loaded_languages(self) -> None:
        languages = self.client.languages()
        self.assertEqual(len(languages["languages"]), 9)
        self.assertIn("j", languages["loaded_languages"])

    def test_tts_speakers_lists_language_voices(self) -> None:
        speakers = self.client.speakers("j")
        self.assertIn("jf_alpha", speakers["speakers"])

    def test_tts_voices_lists_all_voice_metadata(self) -> None:
        voices = self.client.voices()
        self.assertGreaterEqual(len(voices["voices"]), 54)
        self.assertTrue(any(voice["id"] == "af_heart" for voice in voices["voices"]))

    def test_tts_metrics_basic_text_metrics(self) -> None:
        metrics = self.client.metrics("Hello from the Python client.", voice="af_heart")

        self.assertEqual(metrics["voice"], "af_heart")
        self.assertEqual(metrics["language"], "a")
        self.assertGreater(metrics["metrics"]["characters"], 0)
        self.assertGreater(metrics["metrics"]["segments"], 0)

    def test_tts_purge_rejects_invalid_device_without_purging(self) -> None:
        with self.assertRaises(KokoroTTSClientError) as error:
            self.client.purge("cuda:999")

        self.assertIn("400", str(error.exception))

    def test_tts_generate_mp3_with_audio_controls(self) -> None:
        audio = self.client.generate(
            "Testing generate from the Python client.",
            voice="af_heart",
            output_format="mp3",
            pitch_semitones=1,
            tempo=1.05,
            volume=0.9,
        )

        self.assertEqual(audio.media_type, "audio/mpeg")
        self.assertGreater(len(audio.content), 10_000)
        self.assertEqual(audio.headers["x-kokorotts-voice"], "af_heart")
        self.assertEqual(audio.filename, "kokorotts_af_heart.mp3")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = audio.save(Path(temp_dir) / "generate.mp3")
            self.assertGreater(output_path.stat().st_size, 10_000)

    def test_tts_convert_wav_compatibility_alias(self) -> None:
        audio = self.client.convert(
            "Testing compatibility convert from the Python client.",
            voice="af_heart",
        )

        self.assertEqual(audio.media_type, "audio/wav")
        self.assertGreater(len(audio.content), 10_000)
        self.assertEqual(audio.headers["x-kokorotts-route"], "/tts/convert")
        self.assertEqual(audio.filename, "kokorotts_af_heart.wav")

    def test_tts_stream_mp3_short_text(self) -> None:
        audio = self.client.stream(
            "Testing short MP3 stream from the Python client.",
            voice="af_heart",
            stream_format="mp3",
        )

        self.assertEqual(audio.media_type, "audio/mpeg")
        self.assertGreater(len(audio.content), 10_000)
        self.assertEqual(audio.headers["x-kokorotts-stream-format"], "mp3")

    def test_tts_stream_mp3_long_english_text(self) -> None:
        audio = self.client.stream(
            LONG_ENGLISH_TEXT,
            voice="af_heart",
            stream_format="mp3",
            tempo=1.05,
            pitch_semitones=1,
        )

        self.assertEqual(audio.media_type, "audio/mpeg")
        self.assertGreater(len(audio.content), 100_000)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = audio.save(Path(temp_dir) / "long-english.mp3")
            self.assertGreater(output_path.stat().st_size, 100_000)

    def test_tts_stream_pcm_long_spanish_text(self) -> None:
        audio = self.client.stream(
            LONG_SPANISH_TEXT,
            voice="ef_dora",
            stream_format="pcm_s16le",
        )

        self.assertEqual(audio.media_type, "audio/pcm")
        self.assertGreater(len(audio.content), 200_000)

    def test_tts_generate_rejects_invalid_audio_control(self) -> None:
        with self.assertRaises(KokoroTTSClientError) as error:
            self.client.generate("Invalid pitch test.", pitch_semitones=13)

        self.assertIn("422", str(error.exception))
        self.assertIn("pitch_semitones", str(error.exception))


if __name__ == "__main__":
    unittest.main()
