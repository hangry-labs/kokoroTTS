"""Live studio/API checks; run through task studio-test against a local server."""

from __future__ import annotations

import argparse
import io
import json
import struct
import time
import unittest
import wave
from pathlib import Path

import httpx

from kokorotts import KokoroTTSClient

BASE_URL = "http://localhost:7860"
EVIDENCE = None


def document(body):
    return (
        '<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:h="https://hangrylabs.app/ns/ssml-h/1.0">'
        + body
        + "</speak>"
    )


class StudioLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        deadline = time.monotonic() + 60
        while True:
            try:
                if httpx.get(BASE_URL + '/tts/ping', timeout=2).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError(f'KokoroTTS is not ready at {BASE_URL}. Start the container and check its logs before running studio-test.')
            time.sleep(.5)

    def setUp(self):
        self.http = httpx.Client(base_url=BASE_URL, timeout=180)
        self.client = KokoroTTSClient(BASE_URL, timeout=180)
        self.payload = {
            "text": document(
                '<voice name="af_heart">Did you remember the release tests?</voice><break time="120ms"/><voice name="am_michael"><prosody pitch="-1st" rate="fast">Of course! The coffee has not finished testing yet.</prosody></voice>'
            ),
            "input_type": "ssml-h",
            "voice": "af_heart",
            "device": "auto",
            "output_format": "wav",
        }

    def tearDown(self):
        self.http.close()

    def bundle(self, response):
        self.assertEqual(
            response.status_code,
            200,
            response.text[:300] if response.status_code != 200 else "",
        )
        self.assertTrue(
            response.headers["content-type"].startswith(
                "application/vnd.hangrylabs.magic-takes"
            )
        )
        size = struct.unpack("<I", response.content[:4])[0]
        manifest = json.loads(response.content[4 : 4 + size])
        audio = response.content[4 + size :]
        return manifest, lambda item: audio[
            item["offset"] : item["offset"] + item["length"]
        ]

    def test_tts_plan_and_capabilities(self):
        capabilities = self.http.get("/tts/ssml/capabilities").raise_for_status().json()
        self.assertFalse(capabilities["ssml_h"]["voice_definitions_supported"])
        plan = self.http.post("/tts/plan", json=self.payload).raise_for_status().json()
        self.assertEqual(plan["speech_units"], 2)

    def test_magic_take_render_retention_and_assembly(self):
        preview = self.http.post(
            "/tts/magic/take", json={"payload": self.payload, "speech_index": 0}
        ).raise_for_status()
        self.assertEqual(preview.content[:4], b"RIFF")
        response = self.http.post(
            "/tts/magic/render",
            data={
                "payload": json.dumps(self.payload),
                "speech_ids": '["heart","michael"]',
                "retained": '[{"id":"heart","seed":0}]',
            },
            files=[("takes", ("heart.wav", preview.content, "audio/wav"))],
        )
        manifest, audio = self.bundle(response)
        self.assertEqual(audio(manifest["takes"][0]), preview.content)
        full = audio(manifest["output"])
        with wave.open(io.BytesIO(full)) as reader:
            self.assertEqual(reader.getframerate(), 24000)
            self.assertGreater(reader.getnframes(), 24000)
        assembled = self.http.post(
            "/tts/magic/assemble-upload",
            data={
                "options": json.dumps(
                    {
                        "items": [
                            {"type": "speech", "id": "heart"},
                            {"type": "break", "milliseconds": 120},
                            {"type": "speech", "id": "michael"},
                        ],
                        "output_format": "wav",
                    }
                ),
                "take_metadata": '[{"id":"heart"},{"id":"michael"}]',
            },
            files=[
                ("takes", (item["id"] + ".wav", audio(item), "audio/wav"))
                for item in manifest["takes"]
            ],
        ).raise_for_status()
        self.assertEqual(assembled.content, full)
        if EVIDENCE:
            (EVIDENCE / "magic-dialogue.wav").write_bytes(full)

    def test_tts_generate_and_stream_ssml_h_multifamily(self):
        source = document(
            '<voice name="af_heart">Good morning!</voice><voice name="dm_martin">Guten Morgen! Der Kaffee ist fertig.</voice><voice name="zf_001">你好！今天是美好的一天。</voice><voice name="diem_trinh">Xin chào! Chúc bạn một ngày tốt lành.</voice>'
        )
        output = self.client.generate(
            source, input_type="ssml-h", voice="af_heart", output_format="wav"
        )
        self.assertEqual(output.content[:4], b"RIFF")
        stream = b"".join(
            self.client.iter_stream(
                source, input_type="ssml-h", voice="af_heart", stream_format="pcm_s16le"
            )
        )
        self.assertGreater(len(stream), 48000)
        if EVIDENCE:
            (EVIDENCE / "ssml-h-multilingual.wav").write_bytes(output.content)

    def test_magic_long_turn_has_multiple_model_chunks_and_one_take(self):
        payload = {
            **self.payload,
            "text": document(
                '<voice name="af_heart">'
                + "A careful test keeps every sentence complete, including the very last word. "
                * 12
                + "</voice>"
            ),
        }
        plan = self.http.post("/tts/plan", json=payload).raise_for_status().json()
        self.assertEqual(plan["speech_units"], 1)
        self.assertGreater(len(plan["units"][0]["phoneme_chunks"]), 1)
        response = self.http.post(
            "/tts/magic/render",
            data={"payload": json.dumps(payload), "speech_ids": '["long"]'},
        )
        manifest, _ = self.bundle(response)
        self.assertEqual(len(manifest["takes"]), 1)
        self.assertGreater(manifest["metrics"]["duration_seconds"], 10)

    def test_dialogue_workspace_roundtrip_and_cleanup(self):
        name = f"studio-validation-{time.time_ns()}"
        identity = None
        try:
            response = self.http.post(
                "/tts/dialogue-workspaces",
                data={
                    "metadata": json.dumps(
                        {
                            "name": name,
                            "document": self.payload["text"],
                            "workspace": {
                                "takes": [],
                                "settings": {"voice": "af_heart"},
                            },
                        }
                    )
                },
            ).raise_for_status()
            identity = response.json()["id"]
            restored = (
                self.http.get(f"/tts/dialogue-scripts/{identity}")
                .raise_for_status()
                .json()
            )
            self.assertEqual(restored["document"].strip(), self.payload["text"])
            self.assertEqual(restored["workspace"]["settings"]["voice"], "af_heart")
        finally:
            if identity:
                self.http.delete(f"/tts/dialogue-scripts/{identity}").raise_for_status()

    def test_magic_rejects_design_unsafe_xml_and_invalid_take_index(self):
        for source in [
            document('<voice name="af_heart" h:direction="angry">No.</voice>'),
            "<!DOCTYPE speak>" + document("No."),
        ]:
            response = self.http.post(
                "/tts/plan", json={**self.payload, "text": source}
            )
            self.assertEqual(response.status_code, 400)
            self.assertTrue(response.json()["detail"])
        response = self.http.post(
            "/tts/magic/take", json={"payload": self.payload, "speech_index": 999}
        )
        self.assertEqual(response.status_code, 400)


class ConciseResult(unittest.TextTestResult):
    def getDescription(self, test):
        return test._testMethodName


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    BASE_URL = args.base_url
    EVIDENCE = args.output_dir
    if EVIDENCE:
        EVIDENCE.mkdir(parents=True, exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StudioLiveTests)
    result = unittest.TextTestRunner(verbosity=2, resultclass=ConciseResult).run(suite)
    raise SystemExit(not result.wasSuccessful())
