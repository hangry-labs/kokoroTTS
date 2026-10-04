from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.responses import Response
from fastapi.testclient import TestClient

from kokorotts.api import api, openai_speed_controls


class OpenAICompatibilityApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(api)

    def test_health_routes_report_ready(self) -> None:
        for path in ("/health", "/health/live", "/health/ready"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "ok")

    def test_models_list_and_retrieve_canonical_model(self) -> None:
        models = self.client.get("/v1/models")
        alias = self.client.get("/v1/models/kokoro-82m")

        self.assertEqual(models.status_code, 200)
        self.assertEqual(models.json()["data"][0]["id"], "kokoro")
        self.assertEqual(alias.status_code, 200)
        self.assertEqual(alias.json()["id"], "kokoro")

    def test_model_lookup_uses_openai_error_envelope(self) -> None:
        response = self.client.get("/v1/models/unknown")

        self.assertEqual(response.status_code, 400)
        error = response.json()["error"]
        self.assertEqual(error["param"], "model")
        self.assertEqual(error["code"], "model_not_found")

    def test_optional_bearer_authentication(self) -> None:
        with patch.dict(os.environ, {"KOKOROTTS_API_KEY": "secret"}):
            missing = self.client.get("/v1/models")
            valid = self.client.get(
                "/v1/models", headers={"Authorization": "Bearer secret"}
            )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.json()["error"]["type"], "authentication_error")
        self.assertEqual(missing.headers["www-authenticate"], "Bearer")
        self.assertEqual(valid.status_code, 200)

    def test_validation_errors_use_openai_shape_and_status(self) -> None:
        response = self.client.post(
            "/v1/audio/speech",
            json={"model": "kokoro", "voice": "af_heart"},
        )

        self.assertEqual(response.status_code, 400)
        error = response.json()["error"]
        self.assertEqual(error["param"], "input")
        self.assertEqual(error["code"], "invalid_parameter")

    def test_unknown_v1_routes_use_openai_error_envelope(self) -> None:
        response = self.client.get("/v1/not-a-route")

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())
        self.assertNotIn("detail", response.json())

    def test_unsupported_semantic_parameters_are_not_silently_ignored(self) -> None:
        cases = (
            ({"instructions": "sound cheerful"}, "instructions"),
            ({"stream_format": "sse"}, "stream_format"),
            ({"response_format": "ogg"}, "response_format"),
        )
        for extra, expected_param in cases:
            with self.subTest(param=expected_param):
                response = self.client.post(
                    "/v1/audio/speech",
                    json={
                        "model": "kokoro",
                        "input": "Test.",
                        "voice": "af_heart",
                        **extra,
                    },
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["param"], expected_param)

    def test_custom_voice_objects_fail_explicitly(self) -> None:
        response = self.client.post(
            "/v1/audio/speech",
            json={
                "model": "kokoro",
                "input": "Test.",
                "voice": {"id": "voice_123"},
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "unsupported_voice")

    def test_speech_maps_exact_voice_alias_and_openai_defaults(self) -> None:
        response = Response(content=b"audio", media_type="audio/mpeg")
        with patch("kokorotts.api.audio_response", return_value=response) as audio_response:
            result = self.client.post(
                "/v1/audio/speech",
                json={"model": "kokoro", "input": "Test.", "voice": "alloy"},
            )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.content, b"audio")
        self.assertEqual(result.headers["x-kokorotts-model"], "kokoro")
        payload = audio_response.call_args.args[0]
        self.assertEqual(payload.voice, "af_alloy")
        self.assertEqual(payload.output_format, "mp3")
        self.assertEqual(payload.speed, 1.0)
        self.assertEqual(payload.tempo, 1.0)

    def test_speed_range_uses_model_and_postprocessing_controls(self) -> None:
        self.assertEqual(openai_speed_controls(0.25), (0.5, 0.5))
        self.assertEqual(openai_speed_controls(1.25), (1.25, 1.0))
        self.assertEqual(openai_speed_controls(4.0), (2.0, 2.0))

    def test_system_purge_and_legacy_alias_share_the_runtime_operation(self) -> None:
        with patch("kokorotts.api.RUNTIME.purge", return_value=(["cuda:0"], [])) as purge:
            canonical = self.client.post("/system/models/purge", json={})
            legacy = self.client.post("/tts/purge", json={})

        self.assertEqual(canonical.status_code, 200)
        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(purge.call_count, 2)

    def test_native_input_type_defaults_to_plain_text(self) -> None:
        defaults = self.client.get("/tts/defaults")

        self.assertEqual(defaults.status_code, 200)
        self.assertEqual(defaults.json()["input_type"], "text")
        self.assertTrue(defaults.json()["input_types"]["ssml"]["experimental"])

    def test_native_tokenize_accepts_explicit_ssml(self) -> None:
        response = self.client.post(
            "/tts/tokenize",
            json={
                "text": "<speak>Hello <sub alias='World Wide Web Consortium'>W3C</sub>.</speak>",
                "voice": "af_heart",
                "input_type": "ssml",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["input_type"], "ssml")
        self.assertGreater(len(response.json()["phonemes"]), 0)

    def test_native_ssml_rejects_malformed_and_implicit_markup(self) -> None:
        malformed = self.client.post(
            "/tts/tokenize",
            json={
                "text": "<speak><break time='500ms'></speak>",
                "voice": "af_heart",
                "input_type": "ssml",
            },
        )
        plain = self.client.post(
            "/tts/tokenize",
            json={
                "text": "The value 2 < 3 remains plain text.",
                "voice": "af_heart",
            },
        )

        self.assertEqual(malformed.status_code, 400)
        self.assertIn("Invalid or unsafe SSML", malformed.json()["detail"])
        self.assertEqual(plain.status_code, 200)
        self.assertEqual(plain.json()["input_type"], "text")


if __name__ == "__main__":
    unittest.main()
