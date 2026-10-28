from __future__ import annotations

import asyncio
import io
import json
import struct
import tempfile
import time
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from kokorotts.audio import encode_audio_bytes
from kokorotts.ssml_h import compile_dialogue, parse_dialogue
from kokorotts.standalone_ui.magic_api import MagicTakeRequest, attach_magic
from kokorotts.standalone_ui.script_api import attach_scripts
from tests.test_ssml_h import document


class FakeRuntime:
    def __init__(self):
        self.settings = SimpleNamespace(experimental_natural_chunking=lambda: False)
        self.calls = 0
        self.streams_opened = 0
        self.streams_closed = 0

    def serves_voice(self, voice):
        return voice in {"af_heart", "am_michael"}

    def _pipeline_for(self, *_):
        return lambda text, *_args, **_kwargs: [(text, text, None)]

    def prepare_dialogue(self, text, voice):
        turns = parse_dialogue(text, voice, self.serves_voice)
        return turns, compile_dialogue(turns, lambda text, *_: [text])

    def iter_synthesis(self, *args):
        self.streams_opened += 1
        try:
            for unit in args[-1]:
                self.calls += 1
                yield SimpleNamespace(
                    audio=np.full(2400, 0.2, dtype=np.float32), prosody=unit.prosody
                )
        finally:
            self.streams_closed += 1


def unpack(response):
    length = struct.unpack("<I", response.content[:4])[0]
    manifest = json.loads(response.content[4 : 4 + length])
    payload = response.content[4 + length :]
    return manifest, lambda item: payload[
        item["offset"] : item["offset"] + item["length"]
    ]


class MagicApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.runtime = FakeRuntime()
        self.mock = patch("kokorotts.api.RUNTIME", self.runtime)
        self.mock.start()
        app = FastAPI()
        attach_magic(app)
        attach_scripts(app, Path(self.directory.name))
        self.client = TestClient(app)
        self.payload = {
            "text": document(
                '<voice name="af_heart">One.</voice><break time="0ms"/><voice name="am_michael">Two!</voice>'
            ),
            "input_type": "ssml-h",
            "voice": "af_heart",
            "device": "cpu",
            "output_format": "wav",
        }

    def tearDown(self):
        self.mock.stop()
        self.directory.cleanup()

    def test_plan_take_and_binary_bundle_routes_are_implemented(self):
        plan = self.client.post("/tts/plan", json=self.payload)
        self.assertEqual(plan.status_code, 200, plan.text)
        self.assertEqual(plan.json()["speech_units"], 2)
        preview = self.client.post(
            "/tts/magic/take", json={"payload": self.payload, "speech_index": 1}
        )
        self.assertEqual(preview.status_code, 200, preview.text[:200])
        self.assertEqual(preview.content[:4], b"RIFF")
        response = self.client.post(
            "/tts/magic/render",
            data={"payload": json.dumps(self.payload), "speech_ids": '["one","two"]'},
        )
        self.assertEqual(response.status_code, 200, response.text[:200])
        manifest, data = unpack(response)
        self.assertEqual([t["id"] for t in manifest["takes"]], ["one", "two"])
        self.assertEqual(data(manifest["output"])[:4], b"RIFF")
        self.assertEqual(manifest["committed_profiles"], {})

    def test_retained_audio_is_byte_identical_and_not_regenerated(self):
        wav = encode_audio_bytes(np.full(3600, 500, dtype=np.int16), "wav", 24000)
        response = self.client.post(
            "/tts/magic/render",
            data={
                "payload": json.dumps(self.payload),
                "speech_ids": '["one","two"]',
                "retained": '[{"id":"one","seed":0}]',
            },
            files=[("takes", ("one.wav", wav, "audio/wav"))],
        )
        self.assertEqual(response.status_code, 200, response.text[:200])
        manifest, data = unpack(response)
        self.assertEqual(data(manifest["takes"][0]), wav)
        self.assertEqual(self.runtime.calls, 1)

    def test_malformed_requests_are_actionable_client_errors(self):
        invalid = self.client.post(
            "/tts/magic/take", json={"payload": self.payload, "speech_index": 99}
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("speech_index", invalid.json()["detail"])
        wrong = self.client.post(
            "/tts/magic/render",
            data={"payload": json.dumps(self.payload), "speech_ids": '["same","same"]'},
        )
        self.assertEqual(wrong.status_code, 400)
        bad_upload = self.client.post(
            "/tts/magic/render",
            data={
                "payload": json.dumps(self.payload),
                "speech_ids": '["one","two"]',
                "retained": '[{"id":"one"}]',
            },
            files=[("takes", ("one.wav", b"not audio", "audio/wav"))],
        )
        self.assertEqual(bad_upload.status_code, 400)
        self.assertEqual(self.runtime.calls, 0)

    def test_complete_document_uses_one_runtime_lease_and_repeated_requests_finish(
        self,
    ):
        for _ in range(5):
            response = self.client.post(
                "/tts/magic/render",
                data={
                    "payload": json.dumps(self.payload),
                    "speech_ids": '["one","two"]',
                },
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.runtime.streams_opened, 5)
        self.assertEqual(self.runtime.streams_closed, 5)

    def test_cross_origin_writes_are_rejected_before_generation(self):
        response = self.client.post(
            "/tts/magic/take",
            json={"payload": self.payload, "speech_index": 0},
            headers={"Origin": "https://untrusted.example"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.runtime.calls, 0)

    def test_disconnected_preview_stops_and_closes_the_runtime_generator(self):
        original = self.runtime.iter_synthesis

        def delayed(*args):
            for chunk in original(*args):
                time.sleep(0.1)
                yield chunk

        async def disconnected():
            return True

        endpoint = next(
            route.endpoint
            for route in self.client.app.routes
            if route.path == "/tts/magic/take"
        )
        with patch.object(self.runtime, "iter_synthesis", delayed):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    endpoint(
                        MagicTakeRequest(payload=self.payload, speech_index=0),
                        SimpleNamespace(is_disconnected=disconnected),
                    )
                )
        self.assertEqual(raised.exception.status_code, 499)
        self.assertLessEqual(self.runtime.calls, 1)
        self.assertEqual(self.runtime.streams_opened, self.runtime.streams_closed)

    def test_assembly_preserves_zero_pause_and_explicit_timing(self):
        wav = encode_audio_bytes(np.full(2400, 800, dtype=np.int16), "wav", 24000)
        response = self.client.post(
            "/tts/magic/assemble-upload",
            data={
                "options": json.dumps(
                    {
                        "items": [
                            {"type": "speech", "id": "one"},
                            {"type": "break", "milliseconds": 250},
                            {"type": "speech", "id": "two"},
                        ]
                    }
                ),
                "take_metadata": '[{"id":"one"},{"id":"two"}]',
            },
            files=[("takes", ("one.wav", wav)), ("takes", ("two.wav", wav))],
        )
        self.assertEqual(response.status_code, 200, response.text[:200])
        with wave.open(io.BytesIO(response.content)) as audio:
            self.assertEqual(audio.getnframes(), 10800)
        self.assertEqual(self.runtime.calls, 0)

    def test_script_library_and_workspace_survive_a_new_app(self):
        source = {
            "name": "Test dialogue",
            "document": self.payload["text"],
            "tags": ["test"],
        }
        saved = self.client.post("/tts/dialogue-scripts", json=source)
        self.assertEqual(saved.status_code, 200, saved.text)
        identity = saved.json()["id"]
        self.assertEqual(self.client.get("/tts/dialogue-scripts").json()["count"], 1)
        second = FastAPI()
        attach_scripts(second, Path(self.directory.name))
        self.assertEqual(
            TestClient(second)
            .get(f"/tts/dialogue-scripts/{identity}")
            .json()["document"]
            .strip(),
            source["document"],
        )
        duplicate = self.client.post("/tts/dialogue-scripts", json=source)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(
            self.client.get("/tts/dialogue-scripts/not-present").status_code, 404
        )
        self.assertEqual(
            self.client.delete(f"/tts/dialogue-scripts/{identity}").status_code, 200
        )
        self.assertEqual(self.client.get("/tts/dialogue-scripts").json()["count"], 0)

    def test_workspace_upload_decodes_before_persisting(self):
        metadata = {
            "name": "With audio",
            "document": self.payload["text"],
            "workspace": {"takes": [{"speech_index": 0, "seed": 0, "locked": True}]},
        }
        bad = self.client.post(
            "/tts/dialogue-workspaces",
            data={"metadata": json.dumps(metadata)},
            files=[("takes", ("bad.wav", b"not audio"))],
        )
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.client.get("/tts/dialogue-scripts").json()["count"], 0)
        wav = encode_audio_bytes(np.full(2400, 800, dtype=np.int16), "wav", 24000)
        good = self.client.post(
            "/tts/dialogue-workspaces",
            data={"metadata": json.dumps(metadata)},
            files=[("takes", ("take.wav", wav))],
        )
        self.assertEqual(good.status_code, 200, good.text)
        asset = good.json()["workspace"]["takes"][0]["url"]
        self.assertEqual(self.client.get(asset).content[:4], b"RIFF")
        self.assertTrue(good.json()["workspace"]["takes"][0]["locked"])


if __name__ == "__main__":
    unittest.main()
