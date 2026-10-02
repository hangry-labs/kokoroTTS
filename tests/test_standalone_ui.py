from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from kokorotts.standalone_ui.gpu import gpu_history_points, gpu_monitor_html, read_gpu_stats
from kokorotts.standalone_ui.server import _read_version_file, create_app


class StandaloneUiTests(unittest.TestCase):
    @staticmethod
    def backend_app() -> FastAPI:
        backend = FastAPI()

        @backend.get("/tts/ping")
        async def ping() -> dict[str, str]:
            return {"msg": "pong"}

        return backend

    def test_static_workspace_and_api_are_available(self) -> None:
        with TestClient(create_app(api_app=self.backend_app())) as client:
            index = client.get("/")
            script = client.get("/static/app.js")
            audio_editor = client.get("/static/audio-editor.js")
            gpu = client.get("/system/gpu")
            api = client.get("/tts/ping")

        self.assertEqual(index.status_code, 200)
        self.assertIn("KokoroTTS", index.text)
        self.assertIn('data-tab="generate"', index.text)
        self.assertIn('data-tab="stream"', index.text)
        self.assertIn('id="generate-output"', index.text)
        self.assertIn('id="stream-stop"', index.text)
        self.assertIn('id="speed-slider"', index.text)
        self.assertIn('id="speed" class="number-input" type="number"', index.text)
        self.assertIn('id="volume-control"', index.text)
        self.assertIn('id="reset-voice-controls"', index.text)
        self.assertIn('class="data-output json-output" id="api-output"', index.text)
        self.assertIn('id="gpu-output"', index.text)
        self.assertLess(index.text.index('id="text-input"'), index.text.index('id="generate-button"'))
        self.assertLess(index.text.index('id="generate-button"'), index.text.index('id="generate-output"'))
        self.assertLess(index.text.index('id="generate-output"'), index.text.index('id="output-format"'))
        self.assertLess(index.text.index('id="tokenize-button"'), index.text.index('id="text-input"'))
        self.assertLess(index.text.index('id="stream-start"'), index.text.index('id="stream-output"'))
        self.assertIn(f"UI v{_read_version_file()}", index.text)
        self.assertNotIn("{{UI_VERSION}}", index.text)
        self.assertNotIn("gradio", index.text.lower())
        self.assertEqual(script.status_code, 200)
        self.assertIn("AbortController", script.text)
        self.assertIn("/tts/generate", script.text)
        self.assertIn("/tts/stream", script.text)
        self.assertIn("volume: normalize ? 1", script.text)
        self.assertIn("$('#volume').disabled = normalized", script.text)
        self.assertIn("function resetVoiceControls()", script.text)
        self.assertIn("function renderJsonTree(", script.text)
        self.assertIn("fetch('/system/gpu')", script.text)
        self.assertEqual(audio_editor.status_code, 200)
        self.assertIn("WaveSurfer", audio_editor.text)
        self.assertEqual(gpu.status_code, 200)
        self.assertIn("GPU Monitor", gpu.text)
        self.assertEqual(gpu.headers["cache-control"], "no-store")
        self.assertEqual(api.json(), {"msg": "pong"})

    @patch("kokorotts.standalone_ui.gpu.subprocess.run")
    def test_gpu_monitor_parses_and_renders_nvidia_smi(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = "0, NVIDIA RTX Test, 37, 4096, 16384, 52, 61.5\n"

        stats = read_gpu_stats()
        rendered = gpu_monitor_html()

        self.assertEqual(stats[0]["utilization"], 37)
        self.assertEqual(stats[0]["memory_total"], 16384)
        self.assertIn("NVIDIA RTX Test", rendered)
        self.assertIn("37%", rendered)
        self.assertIn("4.0/16.0 GB", rendered)
        self.assertIn("52 C", rendered)
        self.assertIn("62 W", rendered)

    def test_gpu_history_points_cover_monitor_width(self) -> None:
        self.assertEqual(gpu_history_points([0, 50, 100]), "0.0,44.0 90.0,22.0 180.0,0.0")

    def test_development_assets_disable_browser_caching(self) -> None:
        with patch.dict("os.environ", {"KOKOROTTS_UI_DEV": "1"}):
            with TestClient(create_app(api_app=self.backend_app())) as client:
                index = client.get("/")
                stylesheet = client.get("/static/styles.css")
                logo = client.get("/brand/logo_small.png")

        self.assertEqual(index.headers["cache-control"], "no-store")
        self.assertEqual(stylesheet.headers["cache-control"], "no-store")
        self.assertEqual(logo.headers["cache-control"], "no-store")

    def test_unknown_paths_return_not_found(self) -> None:
        with TestClient(create_app(api_app=self.backend_app())) as client:
            response = client.get("/not-allowed")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
