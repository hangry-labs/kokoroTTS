from __future__ import annotations

import argparse
import io
import json
import statistics
import subprocess
import time
import urllib.error
import urllib.request
import wave
from collections import defaultdict
from pathlib import Path
from typing import Any


VOICE_EXAMPLES_PREFIX = "window.VOICE_EXAMPLES ="


def _project_version(start: Path) -> str:
    for directory in [start, *start.parents]:
        path = directory / "VERSION"
        if path.is_file():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
    return "unknown"


def _load_voice_cases(path: Path) -> list[dict[str, str]]:
    source = path.read_text(encoding="utf-8").strip()
    if not source.startswith(VOICE_EXAMPLES_PREFIX):
        raise ValueError(f"{path} does not define {VOICE_EXAMPLES_PREFIX}")
    payload = source[len(VOICE_EXAMPLES_PREFIX) :].strip()
    if payload.endswith(";"):
        payload = payload[:-1].rstrip()
    items = json.loads(payload)
    if not isinstance(items, list):
        raise ValueError(f"{path} must contain a JSON array")

    cases: list[dict[str, str]] = []
    seen_voices: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Voice entry {index} must be an object")
        case = {key: str(item.get(key, "")).strip() for key in ("name", "voice", "language", "text")}
        missing = [key for key, value in case.items() if not value]
        if missing:
            raise ValueError(f"Voice entry {index} is missing: {', '.join(missing)}")
        if case["voice"] in seen_voices:
            raise ValueError(f"Duplicate voice in {path}: {case['voice']}")
        seen_voices.add(case["voice"])
        cases.append(case)
    return cases


def _warmup_cases(cases: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    seen_languages: set[str] = set()
    for case in cases:
        if case["language"] not in seen_languages:
            selected.append(case)
            seen_languages.add(case["language"])
    return selected


def _detect_gpu(requested_index: int | None = None) -> dict[str, Any] | None:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    devices: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        cells = [cell.strip() for cell in line.split(",", maxsplit=3)]
        if len(cells) != 4:
            continue
        try:
            index = int(cells[0])
            memory_total_mib = int(cells[2])
        except ValueError:
            continue
        devices.append(
            {
                "index": index,
                "name": cells[1],
                "memory_total_mib": memory_total_mib,
                "driver_version": cells[3],
            }
        )
    if requested_index is not None:
        return next((device for device in devices if device["index"] == requested_index), None)
    return devices[0] if len(devices) == 1 else None


def _gpu_label(gpu: dict[str, Any] | None) -> str:
    if not gpu:
        return "Not detected"
    return f"{gpu['name']} ({gpu['memory_total_mib']} MiB)"


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _wav_duration_seconds(audio: bytes) -> float:
    with wave.open(io.BytesIO(audio), "rb") as source:
        rate = source.getframerate()
        if rate <= 0:
            raise ValueError("Generated WAV has an invalid sample rate")
        return source.getnframes() / rate


def _json_get(url: str, timeout: float) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_audio(
    base_url: str,
    case: dict[str, str],
    device: str,
    timeout: float,
    repetition: int,
) -> dict[str, Any]:
    payload = {
        "text": case["text"],
        "voice": case["voice"],
        "speed": 1.0,
        "device": device,
        "output_format": "wav",
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/tts/generate",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            audio = response.read()
        elapsed_sec = time.perf_counter() - started
        if not audio:
            raise ValueError("Server returned empty audio")
        duration_sec = _wav_duration_seconds(audio)
        return {
            "language": case["language"],
            "voice": case["voice"],
            "name": case["name"],
            "repetition": repetition,
            "characters": len(case["text"]),
            "bytes": len(audio),
            "audio_duration_sec": round(duration_sec, 4),
            "elapsed_sec": round(elapsed_sec, 4),
            "error": "",
        }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        error = f"HTTP {exc.code}: {detail}"
    except (OSError, ValueError, wave.Error) as exc:
        error = str(exc)
    return {
        "language": case["language"],
        "voice": case["voice"],
        "name": case["name"],
        "repetition": repetition,
        "characters": len(case["text"]),
        "bytes": 0,
        "audio_duration_sec": None,
        "elapsed_sec": round(time.perf_counter() - started, 4),
        "error": error,
    }


def _performance_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [item for item in results if not item.get("error")]
    latencies = [float(item["elapsed_sec"]) for item in successful]
    durations = [float(item["audio_duration_sec"]) for item in successful]
    elapsed_sec = sum(latencies)
    audio_duration_sec = sum(durations)
    return {
        "requests": len(results),
        "successful": len(successful),
        "characters": sum(int(item["characters"]) for item in successful),
        "elapsed_sec": round(elapsed_sec, 3),
        "audio_duration_sec": round(audio_duration_sec, 3),
        "mean_request_sec": round(statistics.fmean(latencies), 3) if latencies else None,
        "median_request_sec": round(statistics.median(latencies), 3) if latencies else None,
        "p95_request_sec": round(_percentile(latencies, 0.95) or 0.0, 3) if latencies else None,
        "realtime_factor": round(elapsed_sec / audio_duration_sec, 4) if audio_duration_sec else None,
        "realtime_speed": round(audio_duration_sec / elapsed_sec, 2) if elapsed_sec else None,
    }


def _group_metrics(results: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        groups[str(result[key])].append(result)

    grouped: list[dict[str, Any]] = []
    for value, group in groups.items():
        row = {key: value, **_performance_metrics(group)}
        row["voices"] = len({item["voice"] for item in group})
        if key == "voice":
            row["name"] = group[0]["name"]
            row["language"] = group[0]["language"]
        grouped.append(row)
    return grouped


def _metric(value: float | None, suffix: str = "", digits: int = 3) -> str:
    return "Unavailable" if value is None else f"{value:.{digits}f}{suffix}"


def _md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _append_summary(path: Path, output: dict[str, Any], comment: str) -> None:
    metrics = output["metrics"]
    line = (
        f"| {_md_escape(output['version'])} | {_md_escape(output['model'])} | "
        f"{_md_escape(_gpu_label(output['gpu']))} | {_md_escape(output['device'])} | "
        f"{output['voices']} | {output['repetitions']} | {metrics['requests']} | "
        f"{metrics['characters']} | {_metric(metrics['audio_duration_sec'], 's')} | "
        f"{_metric(metrics['elapsed_sec'], 's')} | {_metric(metrics['mean_request_sec'], 's')} | "
        f"{_metric(metrics['p95_request_sec'], 's')} | {_metric(metrics['realtime_factor'], '', 4)} | "
        f"{_metric(metrics['realtime_speed'], 'x', 2)} | {_md_escape(comment)} | {output['test_time']} |\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _append_details(path: Path, output: dict[str, Any], comment: str) -> None:
    lines = [
        f"\n## {output['test_time']} - {output['version']}\n",
        f"Model: `{output['model']}`  \n",
        f"GPU: `{_gpu_label(output['gpu'])}`  \n",
        f"Device: `{output['device']}`  \n",
        f"Repetitions per voice: `{output['repetitions']}`  \n",
        f"Comment: {_md_escape(comment) or 'None'}\n",
        "\n### By Language\n\n",
        "| Language | Voices | Requests | Audio | Total | Mean | P95 | RTF | Realtime speed |\n",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n",
    ]
    for row in output["by_language"]:
        lines.append(
            f"| {_md_escape(row['language'])} | {row['voices']} | {row['requests']} | "
            f"{_metric(row['audio_duration_sec'], 's')} | {_metric(row['elapsed_sec'], 's')} | "
            f"{_metric(row['mean_request_sec'], 's')} | {_metric(row['p95_request_sec'], 's')} | "
            f"{_metric(row['realtime_factor'], '', 4)} | {_metric(row['realtime_speed'], 'x', 2)} |\n"
        )
    lines.extend(
        [
            "\n### By Voice\n\n",
            "| Language | Voice | Name | Requests | Audio | Mean | P95 | RTF | Realtime speed |\n",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |\n",
        ]
    )
    for row in output["by_voice"]:
        lines.append(
            f"| {_md_escape(row['language'])} | `{_md_escape(row['voice'])}` | {_md_escape(row['name'])} | "
            f"{row['requests']} | {_metric(row['audio_duration_sec'], 's')} | "
            f"{_metric(row['mean_request_sec'], 's')} | {_metric(row['p95_request_sec'], 's')} | "
            f"{_metric(row['realtime_factor'], '', 4)} | {_metric(row['realtime_speed'], 'x', 2)} |\n"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.writelines(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark every KokoroTTS voice through its HTTP API")
    parser.add_argument("--base-url", default="http://127.0.0.1:7860")
    parser.add_argument("--voices", default="examples/voices.js")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--request-timeout", type=float, default=240.0)
    parser.add_argument("--gpu-index", type=int, default=None)
    parser.add_argument("--comment", default="")
    parser.add_argument("--output", default="benchmarks/tts/results/latest.json")
    parser.add_argument("--summary-md", default="benchmarks/tts/BENCHMARKS.md")
    parser.add_argument("--details-md", default="benchmarks/tts/DETAILS.md")
    parser.add_argument("--no-append", action="store_true")
    parser.add_argument("--allow-failures", action="store_true")
    args = parser.parse_args()

    if args.repetitions < 1:
        parser.error("--repetitions must be at least 1")
    voices_path = Path(args.voices)
    try:
        cases = _load_voice_cases(voices_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if args.limit > 0:
        cases = cases[: args.limit]
    if not cases:
        parser.error("No benchmark voices selected")

    gpu = _detect_gpu(args.gpu_index)
    if args.gpu_index is not None and gpu is None:
        parser.error(f"GPU index {args.gpu_index} was not found by nvidia-smi")

    status = _json_get(f"{args.base_url.rstrip('/')}/tts/status", args.request_timeout)
    print(f"SERVER {status.get('type')} {status.get('version')} model={status.get('repo_id')}", flush=True)
    print(f"GPU {_gpu_label(gpu)} device={args.device}", flush=True)

    warmup_results: list[dict[str, Any]] = []
    warmups = _warmup_cases(cases)
    print(f"WARMUP START languages={len(warmups)}", flush=True)
    for case in warmups:
        result = _request_audio(args.base_url, case, args.device, args.request_timeout, 0)
        warmup_results.append(result)
        state = "PASS" if not result["error"] else "FAIL"
        print(
            f"{state} warmup language={case['language']} voice={case['voice']} "
            f"total={result['elapsed_sec']:.3f}s",
            flush=True,
        )
        if result["error"]:
            print(f"ERROR {result['error']}", flush=True)

    results: list[dict[str, Any]] = []
    total_requests = len(cases) * args.repetitions
    print(
        f"MEASURE START voices={len(cases)} repetitions={args.repetitions} requests={total_requests}",
        flush=True,
    )
    for repetition in range(1, args.repetitions + 1):
        for case in cases:
            result = _request_audio(args.base_url, case, args.device, args.request_timeout, repetition)
            results.append(result)
            state = "PASS" if not result["error"] else "FAIL"
            print(
                f"{state} round={repetition}/{args.repetitions} language={case['language']} "
                f"voice={case['voice']} total={result['elapsed_sec']:.3f}s "
                f"audio={_metric(result['audio_duration_sec'], 's')}",
                flush=True,
            )
            if result["error"]:
                print(f"ERROR {result['error']}", flush=True)

    metrics = _performance_metrics(results)
    failures = [item for item in results if item["error"]]
    output = {
        "version": _project_version(voices_path.parent),
        "server_version": status.get("version"),
        "model": status.get("repo_id", "unknown"),
        "runtime": status.get("runtime"),
        "device": args.device,
        "gpu": gpu,
        "source": str(voices_path),
        "voices": len(cases),
        "languages": len({case["language"] for case in cases}),
        "repetitions": args.repetitions,
        "warmup_requests": len(warmup_results),
        "warmup_failures": sum(bool(item["error"]) for item in warmup_results),
        "failures": len(failures),
        "test_time": time.strftime("%d.%m.%Y %H:%M:%S"),
        "metrics": metrics,
        "by_language": _group_metrics(results, "language"),
        "by_voice": _group_metrics(results, "voice"),
        "warmup_results": warmup_results,
        "results": results,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"PERFORMANCE mean={_metric(metrics['mean_request_sec'], 's')} "
        f"p95={_metric(metrics['p95_request_sec'], 's')} "
        f"rtf={_metric(metrics['realtime_factor'], '', 4)} "
        f"speed={_metric(metrics['realtime_speed'], 'x', 2)}",
        flush=True,
    )
    print(f"RESULT {output_path} failures={len(failures)}", flush=True)
    if not args.no_append:
        _append_summary(Path(args.summary_md), output, args.comment)
        _append_details(Path(args.details_md), output, args.comment)
    return 0 if (not failures and not output["warmup_failures"]) or args.allow_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
