from __future__ import annotations

import json
import re
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from kokorotts.standalone_ui.gpu import GpuMonitor, read_gpu_stats
from kokorotts.standalone_ui.server import (
    _read_version_file,
    _snapshot_build_details,
    create_app,
)


LOCALES_DIR = Path(__file__).parents[1] / "kokorotts" / "standalone_ui" / "static" / "locales"


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

    def test_snapshot_badge_identifies_image_build_but_release_badge_stays_concise(self) -> None:
        metadata = {
            "KOKOROTTS_BUILD_DATE": "2026-10-05T13:47:26Z",
            "KOKOROTTS_VCS_REF": "1234567890abcdef",
        }
        with patch.dict("os.environ", metadata, clear=False):
            self.assertEqual(
                _snapshot_build_details("1.0-snapshot"),
                "2026-10-05 13:47 UTC · 1234567890ab",
            )
            self.assertEqual(_snapshot_build_details("1.0"), "")

            with patch(
                "kokorotts.standalone_ui.server._read_version_file",
                return_value="1.0-snapshot",
            ):
                with TestClient(create_app(api_app=self.backend_app())) as client:
                    snapshot = client.get("/")

            with patch(
                "kokorotts.standalone_ui.server._read_version_file",
                return_value="1.0",
            ):
                with TestClient(create_app(api_app=self.backend_app())) as client:
                    release = client.get("/")

        self.assertIn("UI v1.0-snapshot", snapshot.text)
        self.assertIn(
            '<span class="runtime-build">2026-10-05 13:47 UTC · 1234567890ab</span>',
            snapshot.text,
        )
        self.assertIn("UI v1.0", release.text)
        self.assertNotIn('class="runtime-build"', release.text)

    def test_static_workspace_and_api_are_available(self) -> None:
        gpu_payload = {"gpus": [], "history": {}, "sample_interval_seconds": 1, "idle_timeout_seconds": 60}
        with patch("kokorotts.standalone_ui.server.GPU_MONITOR.request_snapshot", return_value=gpu_payload):
            with TestClient(create_app(api_app=self.backend_app())) as client:
                index = client.get("/")
                script = client.get("/static/app.js")
                translations = client.get("/static/i18n.js")
                locale_manifest = client.get("/static/locales/manifest.json")
                stylesheet = client.get("/static/styles.css")
                audio_editor = client.get("/static/audio-editor.js")
                icon_stylesheet = client.get("/static/vendor/lucide/lucide.css")
                icon_font = client.get("/static/vendor/lucide/lucide.woff2")
                product_logo = client.get("/assets/kokoro_logo_horizontal.webp")
                favicon = client.get("/assets/kokoro_favicon.webp")
                labs_logo = client.get("/assets/hangrylabs_logo.webp")
                gpu = client.get("/system/gpu")
                api = client.get("/tts/ping")

        self.assertEqual(index.status_code, 200)
        self.assertIn("KokoroTTS", index.text)
        self.assertIn("https://hangry-labs.github.io/kokoroTTS/examples/?lang=en", index.text)
        self.assertIn('href="https://hangrylabs.app/"', index.text)
        stale_home = "https://hangrylabs.app/" + "software"
        self.assertNotIn(f'href="{stale_home}"', index.text)
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
        self.assertIn('id="ssml-dialog-title" data-i18n="ssml.title">SSML input', index.text)
        self.assertIn('&lt;voice name="af_heart"&gt;', index.text)
        self.assertIn('&lt;lang xml:lang="en-US"&gt;', index.text)
        self.assertIn('&lt;prosody speed="0.9" pitch="+2st"', index.text)
        self.assertIn('src="/assets/kokoro_logo_horizontal.webp"', index.text)
        self.assertIn('href="/assets/kokoro_favicon.webp"', index.text)
        self.assertIn('class="collapsed-mascot"', index.text)
        self.assertIn('class="labs-signature"', index.text)
        self.assertIn('src="/assets/hangrylabs_logo.webp"', index.text)
        self.assertNotIn('src="/assets/hangrylabs_logo_horizontal.webp"', index.text)
        self.assertLess(index.text.index('class="labs-signature"'), index.text.index('class="collapsed-mascot"'))
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
        self.assertNotIn("{{UI_BUILD_DETAILS}}", index.text)
        self.assertNotIn("{{UI_LOCALE}}", index.text)
        self.assertNotIn("{{UI_DIRECTION}}", index.text)
        self.assertNotIn("{{UI_BOOTSTRAP}}", index.text)
        self.assertIn('<html lang="en" dir="ltr">', index.text)
        self.assertIn('id="ui-locale"', index.text)
        self.assertIn('"locale":"en"', index.text)
        self.assertIn('"messages":{"app.title":"KokoroTTS"', index.text)
        self.assertNotIn("gradio", index.text.lower())
        self.assertEqual(script.status_code, 200)
        self.assertEqual(translations.status_code, 200)
        self.assertIn("localStorage.setItem(bootstrap.storageKey", translations.text)
        self.assertIn("window.location.assign", translations.text)
        self.assertEqual(locale_manifest.status_code, 200)
        self.assertEqual(locale_manifest.json()["defaultLocale"], "en")
        self.assertIn("AbortController", script.text)
        self.assertIn("/tts/generate", script.text)
        self.assertIn("/tts/stream", script.text)
        self.assertIn("[t('api.openai')]: ['/health/ready', '/v1/models']", script.text)
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
        self.assertIn("/system/settings/mcp", script.text)
        self.assertIn('id="mcp-enabled"', index.text)
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
        self.assertIn("labs-signature-pulse", stylesheet.text)
        self.assertNotIn("offset-path", stylesheet.text)
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

    def test_supported_locale_routes_and_catalogs_are_complete(self) -> None:
        expected_locales = ("en", "pl", "ja", "zh", "es", "de")
        english = json.loads((LOCALES_DIR / "en.json").read_text(encoding="utf-8"))
        static_dir = LOCALES_DIR.parent
        referenced_keys = set(
            re.findall(
                r'data-i18n(?:-[a-z-]+)?="([^"]+)"',
                (static_dir / "index.html").read_text(encoding="utf-8"),
            )
        )
        for script_name in ("app.js", "audio-editor.js", "i18n.js"):
            referenced_keys.update(
                re.findall(
                    r"\bt\(['\"]([^'\"]+)['\"]",
                    (static_dir / script_name).read_text(encoding="utf-8"),
                )
            )
        self.assertFalse(referenced_keys - set(english))

        with TestClient(create_app(api_app=self.backend_app())) as client:
            for locale in expected_locales:
                response = client.get(f"/{locale}")
                self.assertEqual(response.status_code, 200, locale)
                self.assertIn(f'<html lang="{locale}" dir="ltr">', response.text)
                self.assertIn(f'"locale":"{locale}"', response.text)
                self.assertIn('"messages":{"app.title":"KokoroTTS"', response.text)
                self.assertIn(
                    f"https://hangry-labs.github.io/kokoroTTS/examples/?lang={locale}",
                    response.text,
                )

                catalog_response = client.get(f"/static/locales/{locale}.json")
                self.assertEqual(catalog_response.status_code, 200, locale)
                catalog = catalog_response.json()
                self.assertEqual(set(catalog), set(english), locale)
                self.assertTrue(all(isinstance(value, str) and value for value in catalog.values()), locale)

            self.assertEqual(client.get("/jp").status_code, 404)

    def test_examples_page_supports_application_locale_links(self) -> None:
        root = Path(__file__).parents[1]
        page = (root / "examples" / "index.html").read_text(encoding="utf-8")
        player = (root / "examples" / "player.js").read_text(encoding="utf-8")

        self.assertIn('href="https://hangrylabs.app/"', page)
        stale_home = "https://hangrylabs.app/" + "software"
        self.assertNotIn(f'href="{stale_home}"', page)
        self.assertIn('../assets/hangrylabs_mascot.webp', page)
        self.assertIn('../assets/kokoro_logo.webp', page)
        self.assertIn('new URLSearchParams(window.location.search).get("lang")', player)
        self.assertIn('requestedVoiceLanguage = PAGE_LANGUAGES[requestedPageLanguage]', player)
        self.assertIn('title: "Hangry Labs KokoroTTS stemmeeksempler"', player)
        self.assertIn('title: "Przykłady głosów Hangry Labs KokoroTTS"', player)
        logo_rule = re.search(r"\.hero-logo \{(?P<body>.*?)\n      \}", page, re.DOTALL)
        self.assertIsNotNone(logo_rule)
        self.assertIn("height: auto", logo_rule.group("body"))
        self.assertNotIn("drop-shadow", logo_rule.group("body"))
        self.assertNotIn("box-shadow", logo_rule.group("body"))
        self.assertNotIn("background:", logo_rule.group("body"))
        self.assertNotIn("aspect-ratio", logo_rule.group("body"))
        self.assertNotIn("border:", logo_rule.group("body"))

    def test_published_release_commands_are_digest_pinned(self) -> None:
        root = Path(__file__).parents[1]
        documents = (root / "README.md", root / "docs" / "dockerhub.md")

        for document in documents:
            contents = document.read_text(encoding="utf-8")
            references = [
                line.rsplit(maxsplit=1)[-1]
                for line in contents.splitlines()
                if line.startswith("docker run")
                and re.search(r"hangrylabs/kokorotts:v\d+\.\d+", line)
            ]
            published = [reference for reference in references if not reference.endswith("-local")]
            self.assertTrue(published, document.name)
            self.assertTrue(
                all(re.search(r"@sha256:[0-9a-f]{64}$", reference) for reference in published),
                f"Unpinned published reference in {document}: {published}",
            )

        release_script = (root / "scripts" / "release.ps1").read_text(encoding="utf-8")
        self.assertIn("(?:@sha256:[0-9a-f]{64})?", release_script)

    def test_public_documentation_has_no_mojibake(self) -> None:
        root = Path(__file__).parents[1]
        readme = (root / "README.md").read_text(encoding="utf-8")
        dockerhub = (root / "docs" / "dockerhub.md").read_text(encoding="utf-8")

        expected_labels = ("Norsk bokmål", "日本語", "简体中文", "Español")
        for document in (readme, dockerhub):
            for label in expected_labels:
                self.assertIn(label, document)
            for marker in (
                "Â·",
                "bokmÃ¥l",
                "EspaÃ±ol",
                "æ—¥æœ¬èªž",
                "ç®€ä½“ä¸­æ–‡",
                "ÃƒÂ",
                "\ufffd",
            ):
                self.assertNotIn(marker, document)

        self.assertIn("ココロ テキスト読み上げへようこそ。", dockerhub)

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
                index = client.get("/ja")
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
