from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mcp.server.mcpserver.exceptions import ToolError

from kokorotts.api import ProcessedSynthesis
from kokorotts.artifacts import ArtifactStore
from kokorotts.catalog import model_family_ids, voices_for_model_families
from kokorotts.mcp_server import attach_mcp, create_mcp_server
from kokorotts.settings import RuntimeSettingsStore


class FakeRuntime:
    def __init__(self, settings_path: Path) -> None:
        self.settings = RuntimeSettingsStore(settings_path)
        self._families = model_family_ids()
        self.loaded_models = [
            {"model_family": self._families[0], "device": "cuda:0"}
        ]

    @property
    def served_model_families(self) -> list[str]:
        return list(self._families)

    @property
    def served_voices(self) -> list[str]:
        return voices_for_model_families(self._families)

    def serves_voice(self, voice: str) -> bool:
        return voice in self.served_voices

    def set_served_model_families(self, families: list[str]) -> list[str]:
        self._families = list(families)
        self.settings.set_served_model_families(families)
        self.loaded_models = [
            item for item in self.loaded_models if item["model_family"] in families
        ]
        return list(families)


def generation_arguments(**overrides):
    values = {
        "text": "Hello from MCP.",
        "input_type": "text",
        "voice": "af_heart",
        "output_format": "mp3",
        "ttl_seconds": 300,
        "speed": 1.0,
        "pitch_semitones": 0.0,
        "tempo": 1.0,
        "volume": 1.0,
        "normalize": False,
    }
    values.update(overrides)
    return values


def simple_arguments(**overrides):
    values = {
        "text": "Hello from MCP.",
        "voice_number": 1,
        "ttl_seconds": 300,
    }
    values.update(overrides)
    return values


def pack_arguments(**overrides):
    values = {
        "standard_multilingual_enabled": True,
        "german_martin_enabled": True,
        "german_victoria_enabled": True,
        "vietnamese_enabled": True,
        "chinese_v11_enabled": True,
    }
    values.update(overrides)
    return values


class MCPServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_use_required_schemas_and_never_offer_raw_audio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeRuntime(Path(directory) / "settings.json")
            store = ArtifactStore(Path(directory) / "output")
            with patch("kokorotts.mcp_server.RUNTIME", fake):
                server = create_mcp_server(
                    artifact_store=store,
                    base_url="http://testserver",
                )
                tools = {tool.name: tool for tool in await server.list_tools()}

        self.assertEqual(
            set(tools),
            {
                "get_health",
                "manage_model_packs",
                "get_available_voices",
                "talk_simple",
                "talk_advanced",
            },
        )
        simple_schema = tools["talk_simple"].input_schema
        advanced_schema = tools["talk_advanced"].input_schema
        pack_schema = tools["manage_model_packs"].input_schema
        voice_schema = tools["get_available_voices"].input_schema
        self.assertEqual(set(simple_schema["properties"]), set(simple_arguments()))
        self.assertEqual(set(simple_schema["required"]), set(simple_arguments()))
        self.assertEqual(set(advanced_schema["properties"]), set(generation_arguments()))
        self.assertEqual(set(advanced_schema["required"]), set(generation_arguments()))
        self.assertEqual(set(pack_schema["properties"]), set(pack_arguments()))
        self.assertEqual(set(pack_schema["required"]), set(pack_arguments()))
        self.assertEqual(set(voice_schema["properties"]), {"voice_group"})
        self.assertEqual(set(voice_schema["required"]), {"voice_group"})
        for schema in (simple_schema, advanced_schema):
            self.assertNotIn("audio", schema["properties"])
            self.assertNotIn("audio_bytes", schema["properties"])
            self.assertNotIn("base64", schema["properties"])
        self.assertIn(
            "never returns raw audio or base64", tools["talk_simple"].description
        )

    async def test_generation_returns_only_link_metadata_and_download_works(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = FakeRuntime(root / "settings.json")
            store = ArtifactStore(root / "output")
            processed = ProcessedSynthesis(
                output_format="mp3",
                sample_rate=24_000,
                waveform=np.zeros(24_000, dtype=np.int16),
                inference=None,
            )
            with (
                patch("kokorotts.mcp_server.RUNTIME", fake),
                patch("kokorotts.mcp_server.synthesize_payload", return_value=processed),
                patch("kokorotts.mcp_server.encode_audio_bytes", return_value=b"mp3-data"),
            ):
                server = create_mcp_server(
                    artifact_store=store,
                    base_url="http://testserver",
                )
                result = await server.call_tool("talk_simple", simple_arguments())

            payload = result.structured_content
            token = payload["download_url"].rsplit("/", 1)[1]
            artifact, path = store.resolve(token)
            generated_audio = path.read_bytes()

        self.assertFalse(result.is_error)
        self.assertEqual(payload["download_url"].split("/tts/")[0], "http://testserver")
        self.assertEqual(payload["ttl_seconds"], 300)
        self.assertNotIn("text", payload)
        self.assertNotIn("data", payload)
        self.assertEqual(generated_audio, b"mp3-data")
        self.assertEqual(artifact.mime_type, "audio/mpeg")
        self.assertTrue(all(block.type == "text" for block in result.content))

    async def test_disabled_voice_error_explains_exact_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeRuntime(Path(directory) / "settings.json")
            fake._families = [model_family_ids()[0]]
            with patch("kokorotts.mcp_server.RUNTIME", fake):
                server = create_mcp_server(
                    artifact_store=ArtifactStore(Path(directory) / "output"),
                    base_url="http://testserver",
                )
                with self.assertRaisesRegex(
                    ToolError, "manage_model_packs.*german_martin_enabled"
                ):
                    await server.call_tool(
                        "talk_advanced", generation_arguments(voice="dm_martin")
                    )

    async def test_numbered_voice_groups_distinguish_available_and_disabled_packs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeRuntime(Path(directory) / "settings.json")
            fake._families = ["kokoro-v1.0"]
            with patch("kokorotts.mcp_server.RUNTIME", fake):
                server = create_mcp_server(
                    artifact_store=ArtifactStore(Path(directory) / "output"),
                    base_url="http://testserver",
                )
                available = await server.call_tool(
                    "get_available_voices", {"voice_group": 0}
                )
                martin = await server.call_tool(
                    "get_available_voices", {"voice_group": 2}
                )

        available_ids = {
            voice["id"] for voice in available.structured_content["voices"]
        }
        martin_payload = martin.structured_content
        self.assertIn("af_heart", available_ids)
        self.assertNotIn("dm_martin", available_ids)
        self.assertEqual(
            [voice["id"] for voice in martin_payload["voices"]], ["dm_martin"]
        )
        self.assertFalse(martin_payload["all_selected_packs_enabled"])
        self.assertEqual(martin_payload["languages"], ["German"])

    async def test_pack_control_is_per_checkpoint_and_refuses_final_disable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeRuntime(Path(directory) / "settings.json")
            with patch("kokorotts.mcp_server.RUNTIME", fake):
                server = create_mcp_server(
                    artifact_store=ArtifactStore(Path(directory) / "output"),
                    base_url="http://testserver",
                )
                disabled = await server.call_tool(
                    "manage_model_packs",
                    pack_arguments(german_martin_enabled=False),
                )
                fake._families = ["kokoro-v1.0"]
                with self.assertRaisesRegex(ToolError, "At least one"):
                    await server.call_tool(
                        "manage_model_packs",
                        pack_arguments(
                            standard_multilingual_enabled=False,
                            german_martin_enabled=False,
                            german_victoria_enabled=False,
                            vietnamese_enabled=False,
                            chinese_v11_enabled=False,
                        ),
                    )

        packs = disabled.structured_content["model_packs"]
        martin = next(pack for pack in packs if pack["id"] == "kikiri-german-martin")
        self.assertFalse(martin["enabled"])
        self.assertFalse(disabled.structured_content["german_martin_enabled"])
        self.assertTrue(disabled.structured_content["standard_multilingual_enabled"])


class MCPTransportTests(unittest.TestCase):
    def test_streamable_http_is_opt_in_and_generated_link_downloads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = FakeRuntime(root / "settings.json")
            store = ArtifactStore(root / "output")
            app = FastAPI()
            with (
                patch("kokorotts.mcp_server.RUNTIME", fake),
                patch.dict(
                    "os.environ",
                    {
                        "KOKOROTTS_MCP_ALLOWED_HOSTS": "testserver",
                        "KOKOROTTS_MCP_BASE_URL": "http://testserver",
                    },
                ),
            ):
                attach_mcp(api_app=app, artifact_store=store)
                artifact = store.create(
                    b"downloadable",
                    extension="mp3",
                    ttl_seconds=300,
                    format="mp3",
                    mime_type="audio/mpeg",
                    duration_seconds=1,
                    sample_rate=24_000,
                    voice="af_heart",
                    language="a",
                    voices=["af_heart"],
                    languages=["a"],
                    inference_devices=["cpu"],
                    fallback_reason=None,
                )
                request = {
                    "headers": {
                        "Accept": "application/json, text/event-stream",
                        "MCP-Protocol-Version": "2025-06-18",
                    },
                    "json": {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {},
                            "clientInfo": {"name": "test-client", "version": "1.0"},
                        },
                    },
                }
                with TestClient(app) as client:
                    disabled = client.post("/mcp", **request)
                    fake.settings.set_mcp_enabled(True)
                    enabled = client.post("/mcp", **request)
                    download = client.get(f"/tts/artifacts/{artifact.token}")

        self.assertEqual(disabled.status_code, 403)
        self.assertIn("System tab", disabled.json()["error"]["message"])
        self.assertEqual(enabled.status_code, 200)
        self.assertEqual(enabled.json()["result"]["serverInfo"]["name"], "kokorotts")
        self.assertEqual(download.content, b"downloadable")
        self.assertEqual(download.headers["content-type"], "audio/mpeg")


if __name__ == "__main__":
    unittest.main()
