from __future__ import annotations

import asyncio
import os
import urllib.request
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


STANDARD_PACK = "kokoro-v1.0"
MARTIN_PACK = "kikiri-german-martin"
PACK_FIELD_BY_ID = {
    "kokoro-v1.0": "standard_multilingual_enabled",
    "kikiri-german-martin": "german_martin_enabled",
    "kikiri-german-victoria": "german_victoria_enabled",
    "contextboxai-kokoro-vietnamese": "vietnamese_enabled",
    "kokoro-v1.1-zh": "chinese_v11_enabled",
}


def _payload(result: Any, action: str) -> dict[str, Any]:
    if getattr(result, "is_error", False):
        detail = "\n".join(
            str(getattr(item, "text", "")) for item in result.content
        )
        raise AssertionError(f"{action} failed: {detail}")
    payload = getattr(result, "structured_content", None)
    if not isinstance(payload, dict):
        raise AssertionError(f"{action} returned no structured result")
    return payload


async def _health(session: ClientSession) -> dict[str, Any]:
    return _payload(await session.call_tool("get_health", arguments={}), "read health")


async def _set_pack(session: ClientSession, pack_id: str, enabled: bool) -> dict[str, Any]:
    health = await _health(session)
    arguments = dict(health["model_pack_status"])
    arguments[PACK_FIELD_BY_ID[pack_id]] = enabled
    return _payload(
        await session.call_tool("manage_model_packs", arguments=arguments),
        f"set {pack_id} enabled={enabled}",
    )


async def _generate(
    session: ClientSession, voice_number: int, text: str
) -> dict[str, Any]:
    return _payload(
        await session.call_tool(
            "talk_simple",
            arguments={
                "text": text,
                "voice_number": voice_number,
                "ttl_seconds": 120,
            },
        ),
        f"generate with simple voice {voice_number}",
    )


async def main() -> int:
    mcp_url = os.getenv("LOCAL_MCP_URL", "http://127.0.0.1:7860/mcp")
    async with (
        streamable_http_client(mcp_url) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        initial_state = dict((await _health(session))["model_pack_status"])
        try:
            await _set_pack(session, STANDARD_PACK, True)
            await _set_pack(session, MARTIN_PACK, True)

            standard_audio = await _generate(
                session, 1, "The standard model remains loaded."
            )
            martin_audio = await _generate(
                session, 10, "Das deutsche Modell wird gezielt entladen."
            )
            if "audio" in standard_audio or "audio" in martin_audio:
                raise AssertionError("MCP generation unexpectedly returned raw audio")

            with urllib.request.urlopen(standard_audio["download_url"], timeout=30) as response:
                downloaded = response.read()
                content_type = response.headers.get_content_type()
            if len(downloaded) < 1_000 or content_type != "audio/mpeg":
                raise AssertionError(
                    f"temporary MP3 download was invalid: {len(downloaded)} bytes, {content_type}"
                )

            loaded = (await _health(session))["model_packs"]
            by_id = {item["id"]: item for item in loaded}
            if not by_id[STANDARD_PACK]["loaded_devices"]:
                raise AssertionError("standard checkpoint did not load")
            if not by_id[MARTIN_PACK]["loaded_devices"]:
                raise AssertionError("Martin checkpoint did not load")

            await _set_pack(session, MARTIN_PACK, False)
            after_disable = (await _health(session))["model_packs"]
            by_id = {item["id"]: item for item in after_disable}
            if by_id[MARTIN_PACK]["loaded_devices"]:
                raise AssertionError("disabled Martin checkpoint remained loaded")
            if not by_id[STANDARD_PACK]["loaded_devices"]:
                raise AssertionError("disabling Martin evicted the standard checkpoint")

            bad_voice = await session.call_tool(
                "talk_advanced",
                arguments={
                    "text": "This must fail clearly.",
                    "input_type": "text",
                    "voice": "definitely_not_a_voice",
                    "output_format": "mp3",
                    "ttl_seconds": 120,
                    "speed": 1,
                    "pitch_semitones": 0,
                    "tempo": 1,
                    "volume": 1,
                    "normalize": False,
                },
            )
            error_text = "\n".join(
                str(getattr(item, "text", "")) for item in bad_voice.content
            )
            if not getattr(bad_voice, "is_error", False):
                raise AssertionError("unknown voice unexpectedly succeeded")
            if "get_available_voices" not in error_text or "voice_group=0" not in error_text:
                raise AssertionError(f"unknown-voice error was not actionable: {error_text}")
        finally:
            _payload(
                await session.call_tool(
                    "manage_model_packs", arguments=initial_state
                ),
                "restore initial model packages",
            )

    print("PASS MCP live linked-audio, actionable-error, and selective-eviction test")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
