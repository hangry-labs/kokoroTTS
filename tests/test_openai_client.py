"""Server-backed compatibility tests using the official OpenAI Python SDK."""

from __future__ import annotations

import os
import unittest

from openai import BadRequestError, OpenAI


BASE_URL = os.getenv("KOKOROTTS_TEST_BASE_URL", "http://localhost:7860")
API_KEY = os.getenv("KOKOROTTS_TEST_API_KEY", "").strip() or "local"


class OpenAIClientServerSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = OpenAI(base_url=f"{BASE_URL.rstrip('/')}/v1", api_key=API_KEY)
        try:
            cls.client.models.list()
        except Exception as exc:  # pragma: no cover - local smoke gating
            raise unittest.SkipTest(
                f"KokoroTTS OpenAI API is not available at {BASE_URL}: {exc}"
            ) from exc

    def test_models_list_exposes_kokoro(self) -> None:
        models = self.client.models.list()

        self.assertEqual([model.id for model in models.data], ["kokoro"])

    def test_audio_speech_generates_mp3_with_voice_alias(self) -> None:
        audio = self.client.audio.speech.create(
            model="kokoro",
            input="Hello from the OpenAI-compatible KokoroTTS API.",
            voice="alloy",
            response_format="mp3",
        )

        self.assertGreater(len(audio.content), 10_000)
        self.assertTrue(audio.content.startswith((b"ID3", b"\xff\xfb", b"\xff\xf3")))

    def test_audio_speech_supports_raw_pcm(self) -> None:
        audio = self.client.audio.speech.create(
            model="kokoro-82m",
            input="Testing raw PCM output.",
            voice="af_heart",
            response_format="pcm",
            speed=1.1,
        )

        self.assertGreater(len(audio.content), 20_000)
        self.assertEqual(len(audio.content) % 2, 0)

    def test_audio_speech_rejects_unsupported_instructions(self) -> None:
        with self.assertRaises(BadRequestError) as error:
            self.client.audio.speech.create(
                model="kokoro",
                input="This request should fail before inference.",
                voice="af_heart",
                instructions="Whisper dramatically.",
            )

        payload = error.exception.body
        self.assertEqual(payload["param"], "instructions")
        self.assertEqual(payload["code"], "unsupported_parameter")


if __name__ == "__main__":
    unittest.main()
