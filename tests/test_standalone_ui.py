from __future__ import annotations

import re
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from kokorotts.standalone_ui.gpu import GpuMonitor, read_gpu_stats
from kokorotts.standalone_ui.server import _read_version_file, create_app


class StandaloneUiTests(unittest.TestCase):
    @staticmethod
    def backend_app() -> FastAPI:
        backend = FastAPI()

        @backend.get("/tts/ping")
        async def ping() -> dict[str, str]:
            return {"msg": "pong"}

        return backend

    def test_ssml_examples_page_includes_playable_dialogue(self) -> None:
        examples = Path(__file__).resolve().parents[1] / "examples"
        page = (examples / "ssml.html").read_text(encoding="utf-8")

        self.assertRegex(
            page,
            r'src="kokorotts\-ssml\-dialogue\.mp3(?:\?[^\"]*)?"',
        )
        self.assertIn('&lt;voice name="af_heart"&gt;', page)
        self.assertIn('&lt;lang xml:lang="en-US"&gt;', page)
        self.assertIn('&lt;prosody speed="0.95" pitch="+1st"&gt;', page)
        self.assertIn('id="gallery-title"', page)
        self.assertIn('id="british-script"', page)
        self.assertIn('id="navigation-script"', page)
        self.assertIn('id="mother-daughter-script"', page)
        self.assertIn('id="multilingual-script"', page)
        self.assertIn('href="index.html"', page)
        self.assertTrue((examples / "ssml.css").is_file())
        self.assertTrue((examples / "ssml.js").is_file())
        for filename in (
            "kokorotts-ssml-dialogue.mp3",
            "kokorotts-ssml-british-deploy.mp3",
            "kokorotts-ssml-moon-navigation.mp3",
            "kokorotts-ssml-mother-daughter.mp3",
            "kokorotts-ssml-multilingual-coffee.mp3",
        ):
            with self.subTest(filename=filename):
                self.assertRegex(page, rf'src="{re.escape(filename)}(?:\?[^\"]*)?"')
                self.assertGreater((examples / filename).stat().st_size, 100_000)

    def test_static_workspace_and_api_are_available(self) -> None:
        gpu_payload = {"gpus": [], "history": {}, "sample_interval_seconds": 1, "idle_timeout_seconds": 60}
        with patch("kokorotts.standalone_ui.server.GPU_MONITOR.request_snapshot", return_value=gpu_payload):
            with TestClient(create_app(api_app=self.backend_app())) as client:
                index = client.get("/")
                script = client.get("/static/app.js")
                stylesheet = client.get("/static/styles.css")
                audio_editor = client.get("/static/audio-editor.js")
                icon_stylesheet = client.get("/static/vendor/lucide/lucide.css")
                icon_font = client.get("/static/vendor/lucide/lucide.woff2")
                product_logo = client.get("/assets/kokoro_logo_horizontal.webp")
                favicon = client.get("/assets/kokoro_favicon.webp")
                labs_logo = client.get("/assets/hangrylabs_logo_horizontal.webp")
                gpu = client.get("/system/gpu")
                api = client.get("/tts/ping")

        self.assertEqual(index.status_code, 200)
        self.assertIn("KokoroTTS", index.text)
        self.assertIn('data-tab="generate"', index.text)
        self.assertIn('data-tab="stream"', index.text)
        self.assertNotIn('data-tab="settings"', index.text)
        self.assertIn('data-tab="system"', index.text)
        self.assertIn('id="generate-output"', index.text)
        self.assertIn('id="stream-stop"', index.text)
        self.assertIn('id="speed-slider"', index.text)
        self.assertIn('id="speed" class="number-input" type="number"', index.text)
        self.assertIn('id="volume-control"', index.text)
        self.assertIn('id="reset-voice-controls"', index.text)
        self.assertIn('id="ssml-mode-button"', index.text)
        self.assertIn('aria-pressed="false"', index.text)
        self.assertIn('id="ssml-help-dialog"', index.text)
        self.assertIn('id="ssml-dialog-title">SSML input', index.text)
        self.assertIn('&lt;voice name="af_heart"&gt;', index.text)
        self.assertIn('&lt;lang xml:lang="en-US"&gt;', index.text)
        self.assertIn('&lt;prosody speed="0.9" pitch="+2st"', index.text)
        self.assertIn('src="/assets/kokoro_logo_horizontal.webp"', index.text)
        self.assertIn('href="/assets/kokoro_favicon.webp"', index.text)
        self.assertIn('class="collapsed-mascot"', index.text)
        self.assertIn('class="labs-badge"', index.text)
        self.assertIn('src="/assets/hangrylabs_logo_horizontal.webp"', index.text)
        self.assertIn('href="https://github.com/hangry-labs/kokoroTTS/releases"', index.text)
        self.assertIn('id="hero-toggle"', index.text)
        self.assertIn("document.documentElement.dataset.headerCollapsed = 'true'", index.text)
        self.assertNotIn('/assets/banner.jpg', index.text)
        self.assertNotIn('class="brand-lockup"', index.text)
        self.assertNotIn("product-highlight", index.text)
        self.assertIn('class="data-output json-output" id="api-output"', index.text)
        self.assertIn('id="gpu-output"', index.text)
        self.assertIn('id="model-settings-groups"', index.text)
        self.assertIn('id="save-model-settings"', index.text)
        self.assertGreater(index.text.index('data-panel="system"'), index.text.index('data-panel="api"'))
        self.assertLess(index.text.index('id="model-settings-groups"'), index.text.index('id="runtime-output"'))
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
        self.assertIn("'OpenAI-compatible API': ['/health/ready', '/v1/models']", script.text)
        self.assertIn("config.browser_playback !== false", script.text)
        self.assertIn("volume: normalize ? 1", script.text)
        self.assertIn("$('#volume').disabled = normalized", script.text)
        self.assertIn("function resetVoiceControls()", script.text)
        self.assertIn("function setInputType(", script.text)
        self.assertIn("input_type: state.inputType", script.text)
        self.assertIn("ssmlDialog.showModal()", script.text)
        self.assertIn("state.plainTextDraft", script.text)
        self.assertIn("state.ssmlDraft", script.text)
        self.assertIn("function setHeroCollapsed(", script.text)
        self.assertIn("headerCollapsed: state.headerCollapsed", script.text)
        self.assertIn("document.documentElement.dataset.headerCollapsed", script.text)
        self.assertIn("hero.animate(", script.text)
        self.assertIn("function renderJsonTree(", script.text)
        self.assertIn("/system/settings/model-families", script.text)
        self.assertIn("function renderDeploymentSettings(", script.text)
        self.assertIn("gpuWindowMs: 60 * 1000", script.text)
        self.assertIn("GPU_HISTORY_RETENTION_MS = 10 * 60 * 1000", script.text)
        self.assertIn("GPU_POLL_INTERVAL_MS = 1000", script.text)
        self.assertIn("function renderGpuMonitor(", script.text)
        self.assertIn("Array.isArray(payload.gpus) ? payload.gpus : []", script.text)
        self.assertIn("renderGpuMonitor(state.gpuStats)", script.text)
        self.assertIn("function addGpuChartGrid(", script.text)
        self.assertIn("function attachGpuChartHover(", script.text)
        self.assertIn("function stopGpuMonitor(", script.text)
        self.assertIn("sessionStorage.setItem(GPU_SESSION_KEY", script.text)
        self.assertNotIn('id="system-refresh"', index.text)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("labs-badge-orbit", stylesheet.text)
        self.assertIn("offset-path", stylesheet.text)
        self.assertIn(".runtime-copy span { display: block", stylesheet.text)
        self.assertIn(".ssml-mode-button.active", stylesheet.text)
        self.assertIn("@keyframes ssml-active-pulse", stylesheet.text)
        self.assertIn(".ssml-dialog::backdrop", stylesheet.text)
        self.assertIn("@media (min-width: 1101px)", stylesheet.text)
        self.assertIn(".brand-hero { height: 237px; min-height: 237px; }", stylesheet.text)
        self.assertEqual(audio_editor.status_code, 200)
        self.assertIn("WaveSurfer", audio_editor.text)
        self.assertEqual(icon_stylesheet.status_code, 200)
        for icon in (
            "activity", "audio-lines", "audio-waveform", "book-open", "boxes", "braces", "check",
            "chevron-down", "chevron-up", "download", "fast-forward", "file-audio", "git-branch",
            "message-square-text", "pause", "play", "radio", "refresh-cw", "rewind", "rotate-ccw",
            "scissors", "share-2", "shuffle", "sliders-horizontal", "sparkles", "square", "volume-2", "x",
        ):
            self.assertIn(f".icon-{icon}::before", icon_stylesheet.text)
        self.assertNotIn(".icon-alarm-clock::before", icon_stylesheet.text)
        self.assertEqual(icon_font.status_code, 200)
        self.assertEqual(icon_font.headers["content-type"], "font/woff2")
        self.assertEqual(product_logo.status_code, 200)
        self.assertEqual(product_logo.headers["content-type"], "image/webp")
        self.assertEqual(favicon.status_code, 200)
        self.assertEqual(favicon.headers["content-type"], "image/webp")
        self.assertEqual(labs_logo.status_code, 200)
        self.assertEqual(labs_logo.headers["content-type"], "image/webp")
        self.assertEqual(gpu.status_code, 200)
        self.assertIn("gpus", gpu.json())
        self.assertIn("history", gpu.json())
        self.assertIsInstance(gpu.json()["gpus"], list)
        self.assertEqual(gpu.headers["cache-control"], "no-store")
        self.assertEqual(api.json(), {"msg": "pong"})

    @patch("kokorotts.standalone_ui.gpu.subprocess.run")
    def test_gpu_monitor_parses_nvidia_smi(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = (
            "0, NVIDIA RTX Test, 37, 12, 4096, 16384, 52, 30, 61.5, 300, "
            "2400, 3000, 13000, 14000, P2, 5, 16\n"
        )

        stats = read_gpu_stats()

        self.assertEqual(stats[0]["utilization"], 37)
        self.assertEqual(stats[0]["memory_total"], 16384)
        self.assertEqual(stats[0]["name"], "NVIDIA RTX Test")
        self.assertEqual(stats[0]["temperature"], 52)
        self.assertEqual(stats[0]["power"], 61.5)
        self.assertEqual(stats[0]["fan_speed"], 30)
        self.assertEqual(stats[0]["graphics_clock"], 2400)
        self.assertEqual(stats[0]["performance_state"], "P2")

    @patch("kokorotts.standalone_ui.gpu.subprocess.run")
    def test_gpu_monitor_keeps_gpu_when_optional_values_are_unavailable(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = (
            "0, NVIDIA Compute GPU, 75, N/A, 1024, 8192, 48, [N/A], 125, 250, "
            "1800, N/A, N/A, N/A, P0, 4, 16\n"
        )

        stats = read_gpu_stats()

        self.assertEqual(len(stats), 1)
        self.assertIsNone(stats[0]["fan_speed"])
        self.assertIsNone(stats[0]["memory_utilization"])
        self.assertEqual(stats[0]["power"], 125.0)

    def test_gpu_monitor_samples_until_idle_timeout(self) -> None:
        calls = 0

        def reader():
            nonlocal calls
            calls += 1
            return [{"index": 0, "name": "Test GPU", "utilization": calls}]

        monitor = GpuMonitor(reader, sample_interval=0.01, idle_timeout=0.04, history_seconds=1)
        try:
            first = monitor.request_snapshot()
            self.assertEqual(first["gpus"][0]["utilization"], 1)
            time.sleep(0.03)
            self.assertGreaterEqual(calls, 3)

            time.sleep(0.05)
            stopped_at = calls
            time.sleep(0.03)
            self.assertEqual(calls, stopped_at)
            self.assertGreaterEqual(len(monitor.request_snapshot()["history"]["0"]), 3)
        finally:
            monitor.close()

    def test_development_assets_disable_browser_caching(self) -> None:
        with patch.dict("os.environ", {"KOKOROTTS_UI_DEV": "1"}):
            with TestClient(create_app(api_app=self.backend_app())) as client:
                index = client.get("/")
                stylesheet = client.get("/static/styles.css")
                logo = client.get("/assets/kokoro_favicon.webp")

        self.assertEqual(index.headers["cache-control"], "no-store")
        self.assertEqual(stylesheet.headers["cache-control"], "no-store")
        self.assertEqual(logo.headers["cache-control"], "no-store")

    def test_unknown_paths_return_not_found(self) -> None:
        with TestClient(create_app(api_app=self.backend_app())) as client:
            response = client.get("/not-allowed")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
