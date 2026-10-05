from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = Path(__file__).with_name("cases.json")
DEFAULT_OUTPUT = ROOT / "testbench" / "results" / "local-ai-mcp-latest.json"

SYSTEM_PROMPT = """You are an agent using a private local KokoroTTS MCP server.
Use the available tools for deployment health, model-package controls, voice discovery, and speech generation.
Model packages are checkpoint families that consume memory. Never interpret them as one package per language.
Use get_available_voices with voice_group 0 for all enabled voices or groups 1 through 5 for one checkpoint family.
Use talk_simple directly for neutral plain-text MP3 speech. Its voice_number schema maps 1-11 to one default voice per supported language, so do not call discovery first. Use talk_advanced only when the user provides an exact voice or requests custom controls, SSML, or another format. Both return an expiring HTTP link and metadata, never audio bytes.
manage_model_packs requires all five Boolean fields. Preserve current values from get_health except for changes the user requested.
Never invent a tool result or download link. If a tool returns an error, report the cause and the corrective action from that error. Retry only when the user explicitly requested a valid recovery.
Do not change package state unless the user explicitly requests it. Do not add unsupported arguments."""


def _request_json(
    url: str,
    *,
    timeout: float,
    api_key: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=(
            json.dumps(body, ensure_ascii=False).encode("utf-8")
            if body is not None
            else None
        ),
        headers={
            "Authorization": f"Bearer {api_key}",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM endpoint returned HTTP {exc.code}: {detail}") from exc


def _discover_model(base_url: str, timeout: float, api_key: str) -> str:
    payload = _request_json(
        f"{base_url.rstrip('/')}/models", timeout=timeout, api_key=api_key
    )
    for item in payload.get("data") or payload.get("models") or []:
        if isinstance(item, dict):
            model = item.get("id") or item.get("name") or item.get("model")
            if model:
                return str(model)
    raise RuntimeError("The local model endpoint returned no model from /models.")


def _openai_tools(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    result = []
    for tool in mcp_tools:
        payload = tool.model_dump(mode="json", by_alias=True)
        result.append(
            {
                "type": "function",
                "function": {
                    "name": payload["name"],
                    "description": payload.get("description")
                    or payload.get("title")
                    or payload["name"],
                    "parameters": payload.get("inputSchema")
                    or payload.get("input_schema")
                    or {"type": "object"},
                },
            }
        )
    return result


def _content_text(result: Any) -> str:
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False)
    parts = [
        str(item.text)
        for item in (getattr(result, "content", None) or [])
        if getattr(item, "text", None)
    ]
    return "\n".join(parts) or "{}"


def _parse_arguments(raw: Any) -> tuple[dict[str, Any] | None, str | None]:
    if isinstance(raw, dict):
        return raw, None
    try:
        parsed = json.loads(str(raw or "{}"))
    except json.JSONDecodeError as exc:
        return None, f"Tool arguments are not valid JSON: {exc.msg}."
    if not isinstance(parsed, dict):
        return None, "Tool arguments must decode to a JSON object."
    return parsed, None


def _tool_error_payload(message: str) -> str:
    return json.dumps(
        {
            "ok": False,
            "error": {
                "code": "invalid_tool_call",
                "message": message,
                "guidance": (
                    "Correct the tool name or arguments using the supplied schema. "
                    "Never invent a tool result."
                ),
            },
        },
        ensure_ascii=False,
    )


def _redact(value: str, limit: int = 3000) -> str:
    value = re.sub(
        r"[A-Za-z0-9+/]{256,}={0,2}",
        lambda match: f"<redacted opaque value: {len(match.group(0))} characters>",
        value,
    )
    return value if len(value) <= limit else f"{value[:limit]}... <truncated>"


async def _run_case(
    *,
    case: dict[str, Any],
    session: ClientSession,
    tool_names: set[str],
    tools: list[dict[str, Any]],
    chat_url: str,
    model: str,
    timeout: float,
    api_key: str,
    max_turns: int,
    max_tokens: int,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": str(case["prompt"])},
    ]
    invocations: list[dict[str, Any]] = []
    final_text = ""
    stop_reason = "turn_limit"
    started = time.perf_counter()

    for turn in range(max_turns):
        try:
            response = await asyncio.to_thread(
                _request_json,
                chat_url,
                timeout=timeout,
                api_key=api_key,
                body={
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": 0,
                    "max_tokens": max_tokens,
                },
            )
        except (OSError, RuntimeError, TimeoutError) as exc:
            stop_reason = f"llm_endpoint_error: {_redact(str(exc))}"
            break
        choices = response.get("choices") or []
        if not choices:
            raise RuntimeError(f"LLM response contained no choices: {_redact(str(response))}")
        choice = choices[0]
        message = choice.get("message") or {}
        assistant = {"role": "assistant", "content": message.get("content") or ""}
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            assistant["tool_calls"] = tool_calls
        messages.append(assistant)
        if not tool_calls:
            final_text = str(message.get("content") or "").strip()
            stop_reason = str(choice.get("finish_reason") or "no_tool_call")
            break

        for tool_call in tool_calls:
            call_id = str(tool_call.get("id") or f"call-{turn}-{len(invocations)}")
            function = tool_call.get("function") or {}
            name = str(function.get("name") or "")
            arguments, parse_error = _parse_arguments(function.get("arguments"))
            invocation = {
                "name": name,
                "arguments": arguments if arguments is not None else function.get("arguments"),
                "outcome": "error",
                "error": None,
            }
            if parse_error:
                tool_text = _tool_error_payload(parse_error)
                invocation["error"] = parse_error
            elif name not in tool_names:
                error = (
                    f"Unknown tool {name!r}. Available tools: "
                    f"{', '.join(sorted(tool_names))}."
                )
                tool_text = _tool_error_payload(error)
                invocation["error"] = error
            else:
                try:
                    called = await session.call_tool(name, arguments=arguments or {})
                    tool_text = _content_text(called)
                    if getattr(called, "is_error", False):
                        invocation["error"] = tool_text
                    else:
                        invocation["outcome"] = "success"
                except Exception as exc:  # Tool failures are evaluator evidence.
                    tool_text = _tool_error_payload(str(exc))
                    invocation["error"] = str(exc)
            invocation["result"] = _redact(tool_text)
            invocations.append(invocation)
            messages.append(
                {"role": "tool", "tool_call_id": call_id, "content": tool_text}
            )

    return {
        "id": case["id"],
        "prompt": case["prompt"],
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "invocations": invocations,
        "final_text": final_text,
        "stop_reason": stop_reason,
    }


def _rule_matches(actual: Any, rule: dict[str, Any]) -> bool:
    if "equals" in rule:
        return actual == rule["equals"]
    if "contains" in rule:
        return str(rule["contains"]).casefold() in str(actual).casefold()
    return False


def _score(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    invocations = result["invocations"]
    actual_tools = [item["name"] for item in invocations]
    expected_tools = case.get("expected_tools") or []
    allowed_tool_sequences = case.get("allowed_tool_sequences") or []
    if allowed_tool_sequences:
        if actual_tools not in allowed_tool_sequences:
            failures.append(
                f"tool sequence {actual_tools!r} not in {allowed_tool_sequences!r}"
            )
    elif case.get("exact_tool_sequence"):
        if actual_tools != expected_tools:
            failures.append(f"tool sequence {actual_tools!r} != {expected_tools!r}")
    elif actual_tools[: len(expected_tools)] != expected_tools:
        failures.append(f"tool prefix {actual_tools!r} != {expected_tools!r}")

    actual_outcomes = [item["outcome"] for item in invocations]
    expected_outcomes = case.get("expected_outcomes") or []
    allowed_outcome_sequences = case.get("allowed_outcome_sequences") or []
    if allowed_outcome_sequences and actual_outcomes not in allowed_outcome_sequences:
        failures.append(
            f"outcomes {actual_outcomes!r} not in {allowed_outcome_sequences!r}"
        )
    elif (
        not allowed_outcome_sequences
        and actual_outcomes[: len(expected_outcomes)] != expected_outcomes
    ):
        failures.append(f"outcomes {actual_outcomes!r} != {expected_outcomes!r}")

    required_count = case.get("required_argument_count")
    for index, invocation in enumerate(invocations):
        arguments = invocation.get("arguments")
        if (
            required_count is not None
            and invocation.get("name") in {"talk_simple", "talk_advanced"}
            and (not isinstance(arguments, dict) or len(arguments) != required_count)
        ):
            failures.append(
                f"invocation {index + 1} supplied "
                f"{len(arguments) if isinstance(arguments, dict) else 0} arguments; "
                f"expected {required_count}"
            )

    for index, rules in enumerate(case.get("argument_rules") or []):
        if index >= len(invocations):
            failures.append(f"missing invocation {index + 1} for argument checks")
            continue
        arguments = invocations[index].get("arguments")
        if not isinstance(arguments, dict):
            failures.append(f"invocation {index + 1} arguments were not an object")
            continue
        for name, rule in rules.items():
            if not _rule_matches(arguments.get(name), rule):
                failures.append(
                    f"invocation {index + 1} argument {name!r} failed {rule!r}: "
                    f"{arguments.get(name)!r}"
                )

    observed_errors = "\n".join(str(item.get("error") or "") for item in invocations)
    for expected in case.get("expected_error_contains") or []:
        if str(expected).casefold() not in observed_errors.casefold():
            failures.append(f"tool error did not contain {expected!r}")

    final_text = str(result.get("final_text") or "")
    if not final_text:
        failures.append("model did not produce a final answer")
    required_final = case.get("final_contains_any") or []
    if required_final and not any(
        str(value).casefold() in final_text.casefold() for value in required_final
    ):
        failures.append(f"final answer contained none of {required_final!r}")

    for invocation in invocations:
        if invocation["name"] in {"talk_simple", "talk_advanced"} and invocation["outcome"] == "success":
            payload = invocation.get("result") or ""
            if "download_url" not in payload:
                failures.append("successful generation returned no download_url")
            if any(marker in payload.casefold() for marker in ["base64", "audio_bytes"]):
                failures.append("generation result appeared to contain raw audio")
    return {"passed": not failures, "failures": failures}


async def _pack_state(session: ClientSession) -> dict[str, bool]:
    result = await session.call_tool("get_health", arguments={})
    if getattr(result, "is_error", False):
        raise RuntimeError(f"Could not read initial package state: {_content_text(result)}")
    payload = getattr(result, "structured_content", None) or {}
    return {
        str(name): bool(enabled)
        for name, enabled in (payload.get("model_pack_status") or {}).items()
    }


async def _restore_pack_state(
    session: ClientSession, initial: dict[str, bool]
) -> list[str]:
    messages: list[str] = []
    current = await _pack_state(session)
    if current != initial:
        result = await session.call_tool("manage_model_packs", arguments=initial)
        if getattr(result, "is_error", False):
            messages.append(f"failed to restore package state: {_content_text(result)}")
        else:
            messages.append("restored complete model package state")
    return messages


async def _main(args: argparse.Namespace) -> int:
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if args.case_ids:
        selected = set(args.case_ids)
        cases = [case for case in cases if case["id"] in selected]
    model = args.model or await asyncio.to_thread(
        _discover_model, args.base_url, args.timeout, args.api_key
    )
    chat_url = f"{args.base_url.rstrip('/')}/chat/completions"
    all_results: list[dict[str, Any]] = []
    restoration: list[str] = []

    async with (
        streamable_http_client(args.mcp_url) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        initialized = await session.initialize()
        listed = await session.list_tools()
        tool_names = {tool.name for tool in listed.tools}
        tools = _openai_tools(listed.tools)
        initial_state = await _pack_state(session)
        print(f"LLM: {model} at {args.base_url}", flush=True)
        print(f"MCP: {initialized.server_info.name} at {args.mcp_url}", flush=True)
        print(f"Tools: {', '.join(sorted(tool_names))}", flush=True)
        try:
            for case in cases:
                result = await _run_case(
                    case=case,
                    session=session,
                    tool_names=tool_names,
                    tools=tools,
                    chat_url=chat_url,
                    model=model,
                    timeout=args.timeout,
                    api_key=args.api_key,
                    max_turns=args.max_turns,
                    max_tokens=args.max_tokens,
                )
                result["score"] = _score(case, result)
                all_results.append(result)
                marker = "PASS" if result["score"]["passed"] else "FAIL"
                used = ", ".join(item["name"] for item in result["invocations"]) or "none"
                print(
                    f"[{marker}] case={case['id']} tools={used} "
                    f"time={result['elapsed_seconds']:.3f}s",
                    flush=True,
                )
                for failure in result["score"]["failures"]:
                    print(f"  - {failure}", flush=True)
        finally:
            restoration = await _restore_pack_state(session, initial_state)
            for message in restoration:
                print(f"State: {message}", flush=True)

    passed = sum(1 for result in all_results if result["score"]["passed"])
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "llm_base_url": args.base_url,
        "llm_model": model,
        "mcp_url": args.mcp_url,
        "summary": {
            "passed": passed,
            "failed": len(all_results) - passed,
            "total": len(all_results),
        },
        "state_restoration": restoration,
        "results": all_results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], indent=2), flush=True)
    print(f"Report: {args.output}", flush=True)
    return 0 if passed == len(all_results) else 1


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exercise KokoroTTS MCP tools through a local OpenAI-compatible model"
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("LOCAL_AI_BASE_URL", "http://192.168.0.172:18080/v1"),
    )
    parser.add_argument("--model", default=os.getenv("LOCAL_AI_MODEL", ""))
    parser.add_argument("--api-key", default=os.getenv("LOCAL_AI_API_KEY", "local"))
    parser.add_argument(
        "--mcp-url",
        default=os.getenv("LOCAL_MCP_URL", "http://127.0.0.1:7860/mcp"),
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-turns", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout", type=float, default=240.0)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(_arguments())))
