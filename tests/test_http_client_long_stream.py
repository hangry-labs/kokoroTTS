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

LONG_JAPANESE_TEXT = (
    "KokoroTTSは長い日本語の文章を最後まで読み上げられるか確認しています。"
    "文章は自然な区切りで分けられ、どの部分も失われてはいけません。"
) * 30

LONG_CHINESE_TEXT = (
    "KokoroTTS正在测试一段较长的中文内容，确认每一部分都能被正确处理。"
    "即使文本超过单个模型片段的长度，后面的内容也不应该被截断。"
) * 30


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
        self.assertGreaterEqual(status["voices"], 56)

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
        self.assertEqual(len(languages["languages"]), 10)
        self.assertIn("j", languages["loaded_languages"])
        self.assertIn("d", languages["loaded_languages"])

    def test_tts_samples_returns_language_intro(self) -> None:
        sample = self.client.sample("j")
        self.assertEqual(sample["language"], "j")
        self.assertFalse(sample["random"])
        self.assertGreater(len(sample["text"]), 20)

    def test_tts_speakers_lists_language_voices(self) -> None:
        speakers = self.client.speakers("j")
        self.assertIn("jf_alpha", speakers["speakers"])

    def test_tts_voices_lists_all_voice_metadata(self) -> None:
        voices = self.client.voices()
        self.assertGreaterEqual(len(voices["voices"]), 56)
        self.assertTrue(any(voice["id"] == "af_heart" for voice in voices["voices"]))
        self.assertTrue(any(voice["id"] == "dm_martin" for voice in voices["voices"]))

    def test_system_settings_get_lists_deployment_models(self) -> None:
        settings = self.client.deployment_settings()
        self.assertGreaterEqual(len(settings["supported_voices"]), 56)
        self.assertGreaterEqual(len(settings["supported_model_families"]), 3)

    def test_system_settings_voices_put_preserves_served_voices(self) -> None:
        served = self.client.deployment_settings()["served_voices"]
        self.assertEqual(self.client.set_served_voices(served)["served_voices"], served)

    def test_system_settings_model_families_put_preserves_served_models(self) -> None:
        families = self.client.deployment_settings()["served_model_families"]
        self.assertEqual(
            self.client.set_served_model_families(families)["served_model_families"],
            families,
        )

    def test_tts_metrics_basic_text_metrics(self) -> None:
        metrics = self.client.metrics("Hello from the Python client.", voice="af_heart")

        self.assertEqual(metrics["voice"], "af_heart")
        self.assertEqual(metrics["language"], "a")
        self.assertGreater(metrics["metrics"]["characters"], 0)
        self.assertGreater(metrics["metrics"]["segments"], 0)

    def test_tts_tokenize_returns_phoneme_segments(self) -> None:
        tokens = self.client.tokenize("Hello from KokoroTTS.", voice="af_heart")
        self.assertEqual(tokens["voice"], "af_heart")
        self.assertGreater(len(tokens["segments"]), 0)
        self.assertGreater(tokens["metrics"]["phoneme_characters"], 0)

    def test_tts_tokenize_preserves_long_japanese_text(self) -> None:
        tokens = self.client.tokenize(LONG_JAPANESE_TEXT, voice="jf_alpha")

        self.assertGreater(len(tokens["segments"]), 1)
        self.assertGreater(tokens["metrics"]["phoneme_characters"], 510)
        self.assertTrue(all(len(segment) <= 510 for segment in tokens["segments"]))

    def test_tts_tokenize_preserves_long_chinese_text(self) -> None:
        tokens = self.client.tokenize(LONG_CHINESE_TEXT, voice="zf_xiaobei")

        self.assertGreater(len(tokens["segments"]), 1)
        self.assertGreater(tokens["metrics"]["phoneme_characters"], 510)
        self.assertTrue(all(len(segment) <= 510 for segment in tokens["segments"]))

    def test_tts_purge_rejects_invalid_device_without_purging(self) -> None:
        with self.assertRaises(KokoroTTSClientError) as error:
            self.client.purge("cuda:999")

        self.assertIn("400", str(error.exception))

    def test_tts_purge_releases_loaded_models(self) -> None:
        self.client.generate("Load a model before testing purge.", output_format="mp3")
        loaded = self.client.status()["loaded_model_devices"]
        self.assertGreater(len(loaded), 0)

        result = self.client.purge()

        self.assertGreater(len(result["purged"]), 0)
        self.assertEqual(result["remaining_model_devices"], [])
        self.assertEqual(self.client.status()["loaded_model_devices"], [])

    def test_tts_generate_mp3_with_audio_controls(self) -> None:
        audio = self.client.generate(
            "Testing generate from the Python client.",
            voice="af_heart",
            output_format="mp3",
            speed=1.07,
            pitch_semitones=0.15,
            tempo=1.03,
            volume=0.93,
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
        with self.client.iter_stream(
            LONG_ENGLISH_TEXT,
            voice="af_heart",
            stream_format="mp3",
            tempo=1.05,
            pitch_semitones=1,
            chunk_size=32 * 1024,
        ) as stream:
            chunks = list(stream)
            media_type = stream.media_type
            headers = stream.headers
        content = b"".join(chunks)

        self.assertEqual(media_type, "audio/mpeg")
        self.assertEqual(headers["x-kokorotts-stream-format"], "mp3")
        self.assertGreater(len(chunks), 1)
        self.assertGreater(len(content), 100_000)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "long-english.mp3"
            output_path.write_bytes(content)
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
