from __future__ import annotations

import argparse
import json
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import torch

from benchmarks.tts.run_benchmark import (
    _detect_gpu,
    _gpu_label,
    _load_voice_cases,
    _md_escape,
    _project_version,
)
from kokorotts.catalog import DEFAULT_MODEL_REPO_ID
from kokorotts.runtime import InferenceRuntime


MIB = 1024 * 1024
SAMPLE_RATE = 24_000


def _mib(value: int) -> float:
    return round(value / MIB, 1)


def _process_memory(device: str) -> dict[str, float]:
    torch.cuda.synchronize(device)
    return {
        "allocated_mib": _mib(torch.cuda.memory_allocated(device)),
        "reserved_mib": _mib(torch.cuda.memory_reserved(device)),
        "peak_allocated_mib": _mib(torch.cuda.max_memory_allocated(device)),
        "peak_reserved_mib": _mib(torch.cuda.max_memory_reserved(device)),
    }


def _device_memory(device: str) -> dict[str, float]:
    free_bytes, total_bytes = torch.cuda.mem_get_info(device)
    return {
        "used_mib": _mib(total_bytes - free_bytes),
        "free_mib": _mib(free_bytes),
        "total_mib": _mib(total_bytes),
    }


class DeviceMemorySampler:
    """Sample whole-device memory while a benchmark phase is running."""

    def __init__(
        self,
        device: str,
        interval: float,
        sample: Callable[[str], dict[str, float]] = _device_memory,
    ) -> None:
        self.device = device
        self.interval = interval
        self._sample = sample
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.samples: list[dict[str, float]] = []

    def _capture(self) -> None:
        self.samples.append(self._sample(self.device))

    def _run(self) -> None:
        self._capture()
        while not self._stop.wait(self.interval):
            self._capture()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        self._capture()
        return {
            "samples": len(self.samples),
            "peak_used_mib": max(sample["used_mib"] for sample in self.samples),
            "minimum_free_mib": min(sample["free_mib"] for sample in self.samples),
            "total_mib": self.samples[-1]["total_mib"],
        }


def _measure_phase(
    device: str,
    sample_interval: float,
    operation: Callable[[], Any],
) -> tuple[Any, dict[str, Any], float]:
    sampler = DeviceMemorySampler(device, sample_interval)
    sampler.start()
    started = time.perf_counter()
    try:
        result = operation()
        torch.cuda.synchronize(device)
    finally:
        elapsed_sec = time.perf_counter() - started
        device_peak = sampler.stop()
    return result, device_peak, elapsed_sec


def _group_languages(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        groups[result["language"]].append(result)

    output: list[dict[str, Any]] = []
    for language, items in groups.items():
        peak_item = max(items, key=lambda item: item["process"]["peak_reserved_mib"])
        device_peak_item = max(items, key=lambda item: item["device"]["peak_used_mib"])
        output.append(
            {
                "language": language,
                "voices": len(items),
                "peak_allocated_mib": max(
                    item["process"]["peak_allocated_mib"] for item in items
                ),
                "peak_reserved_mib": peak_item["process"]["peak_reserved_mib"],
                "peak_reserved_voice": peak_item["voice"],
                "device_peak_used_mib": device_peak_item["device"]["peak_used_mib"],
                "device_peak_voice": device_peak_item["voice"],
            }
        )
    return output


def _append_summary(path: Path, output: dict[str, Any], comment: str) -> None:
    stages = output["stages"]
    peaks = output["peaks"]
    line = (
        f"| {_md_escape(output['version'])} | {_md_escape(output['model'])} | "
        f"{_md_escape(_gpu_label(output['gpu']))} | {stages['before_runtime']['device']['total_mib']:.1f} MiB | "
        f"{stages['before_runtime']['device']['used_mib']:.1f} MiB | "
        f"{stages['after_weights']['process']['allocated_mib']:.1f} MiB | "
        f"{stages['after_weights']['process']['reserved_mib']:.1f} MiB | "
        f"{peaks['process_allocated_mib']:.1f} MiB | {peaks['process_reserved_mib']:.1f} MiB | "
        f"{peaks['inference_reserved_increment_mib']:.1f} MiB | "
        f"{peaks['device_used_mib']:.1f} MiB | {peaks['device_increment_mib']:.1f} MiB | "
        f"{output['voices']} | {output['sample_interval_ms']:.0f} ms | "
        f"{_md_escape(comment)} | {output['test_time']} |\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _append_details(path: Path, output: dict[str, Any], comment: str) -> None:
    stages = output["stages"]
    lines = [
        f"\n## {output['test_time']} - {output['version']}\n",
        f"- Model: `{output['model']}`\n",
        f"- GPU: `{_gpu_label(output['gpu'])}`\n",
        f"- Sample interval: `{output['sample_interval_ms']:.0f} ms`\n",
        f"- Comment: {_md_escape(comment) or 'None'}\n",
        "\n### Lifecycle Stages\n\n",
        "| Stage | Process allocated | Process reserved | Process peak allocated | Process peak reserved | Device used |\n",
        "| --- | ---: | ---: | ---: | ---: | ---: |\n",
    ]
    for label, key in (
        ("Before runtime", "before_runtime"),
        ("After voice preparation", "after_voice_preparation"),
        ("After initial model weights", "after_weights"),
        ("After all inference", "after_inference"),
    ):
        stage = stages[key]
        process = stage["process"]
        lines.append(
            f"| {label} | {process['allocated_mib']:.1f} MiB | {process['reserved_mib']:.1f} MiB | "
            f"{process['peak_allocated_mib']:.1f} MiB | {process['peak_reserved_mib']:.1f} MiB | "
            f"{stage['device']['used_mib']:.1f} MiB |\n"
        )

    lines.extend(
        [
            "\n### By Language\n\n",
            "| Language | Voices | Process peak allocated | Process peak reserved | Peak voice | Device peak | Device peak voice |\n",
            "| --- | ---: | ---: | ---: | --- | ---: | --- |\n",
        ]
    )
    for row in output["by_language"]:
        lines.append(
            f"| {_md_escape(row['language'])} | {row['voices']} | {row['peak_allocated_mib']:.1f} MiB | "
            f"{row['peak_reserved_mib']:.1f} MiB | `{row['peak_reserved_voice']}` | "
            f"{row['device_peak_used_mib']:.1f} MiB | `{row['device_peak_voice']}` |\n"
        )

    lines.extend(
        [
            "\n### By Voice\n\n",
            "| Language | Voice | Name | Audio | Process peak allocated | Process peak reserved | Inference increment | Device baseline | Device peak | Samples |\n",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n",
        ]
    )
    weight_reserved = stages["after_weights"]["process"]["reserved_mib"]
    for row in output["results"]:
        process = row["process"]
        device = row["device"]
        lines.append(
            f"| {_md_escape(row['language'])} | `{row['voice']}` | {_md_escape(row['name'])} | "
            f"{row['audio_duration_sec']:.3f}s | {process['peak_allocated_mib']:.1f} MiB | "
            f"{process['peak_reserved_mib']:.1f} MiB | "
            f"{max(0.0, process['peak_reserved_mib'] - weight_reserved):.1f} MiB | "
            f"{row['device_baseline_mib']:.1f} MiB | {device['peak_used_mib']:.1f} MiB | "
            f"{device['samples']} |\n"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.writelines(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure KokoroTTS GPU memory by lifecycle, language, and voice")
    parser.add_argument("--voices", default="examples/voices.js")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--gpu-index", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sample-interval", type=float, default=0.05)
    parser.add_argument("--comment", default="")
    parser.add_argument("--output", default="benchmarks/vram/results/latest.json")
    parser.add_argument("--summary-md", default="benchmarks/vram/VRAM_BENCHMARKS.md")
    parser.add_argument("--details-md", default="benchmarks/vram/DETAILS.md")
    parser.add_argument("--no-append", action="store_true")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        parser.error("A CUDA GPU is required for the VRAM benchmark")
    if args.sample_interval <= 0:
        parser.error("--sample-interval must be greater than zero")

    voices_path = Path(args.voices)
    cases = _load_voice_cases(voices_path)
    if args.limit > 0:
        cases = cases[: args.limit]
    if not cases:
        parser.error("No benchmark voices selected")

    torch.cuda.set_device(args.device)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(args.device)
    gpu = _detect_gpu(args.gpu_index)
    before_runtime = {
        "process": _process_memory(args.device),
        "device": _device_memory(args.device),
    }
    print(
        f"BEFORE RUNTIME process_reserved={before_runtime['process']['reserved_mib']:.1f} MiB "
        f"device_used={before_runtime['device']['used_mib']:.1f} MiB",
        flush=True,
    )

    runtime = InferenceRuntime(eager_voices=True)
    after_voice_preparation = {
        "process": _process_memory(args.device),
        "device": _device_memory(args.device),
    }
    print("VOICE PREPARATION COMPLETE", flush=True)

    torch.cuda.reset_peak_memory_stats(args.device)

    def load_model() -> None:
        with runtime.use_model(args.device):
            pass

    _, load_device_peak, load_elapsed_sec = _measure_phase(
        args.device, args.sample_interval, load_model
    )
    after_weights = {
        "process": _process_memory(args.device),
        "device": _device_memory(args.device),
        "device_phase_peak": load_device_peak,
        "elapsed_sec": round(load_elapsed_sec, 3),
    }
    print(
        f"WEIGHTS LOADED allocated={after_weights['process']['allocated_mib']:.1f} MiB "
        f"reserved={after_weights['process']['reserved_mib']:.1f} MiB",
        flush=True,
    )

    results: list[dict[str, Any]] = []
    print(f"MEASURE START voices={len(cases)}", flush=True)
    for case in cases:
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(args.device)
        device_baseline = _device_memory(args.device)["used_mib"]

        def synthesize():
            return runtime.synthesize(case["text"], case["voice"], 1.0, args.device)

        synthesis, device_peak, elapsed_sec = _measure_phase(
            args.device, args.sample_interval, synthesize
        )
        process = _process_memory(args.device)
        audio_duration_sec = (
            len(synthesis.audio) / SAMPLE_RATE if synthesis is not None else 0.0
        )
        result = {
            "language": case["language"],
            "voice": case["voice"],
            "name": case["name"],
            "characters": len(case["text"]),
            "audio_duration_sec": round(audio_duration_sec, 4),
            "elapsed_sec": round(elapsed_sec, 4),
            "process": process,
            "device_baseline_mib": device_baseline,
            "device": device_peak,
        }
        results.append(result)
        print(
            f"PASS language={case['language']} voice={case['voice']} "
            f"peak_allocated={process['peak_allocated_mib']:.1f} MiB "
            f"peak_reserved={process['peak_reserved_mib']:.1f} MiB "
            f"device_peak={device_peak['peak_used_mib']:.1f} MiB",
            flush=True,
        )

    torch.cuda.empty_cache()
    after_inference = {
        "process": _process_memory(args.device),
        "device": _device_memory(args.device),
    }
    peak_process_allocated = max(
        item["process"]["peak_allocated_mib"] for item in results
    )
    peak_process_reserved = max(
        item["process"]["peak_reserved_mib"] for item in results
    )
    peak_device_used = max(item["device"]["peak_used_mib"] for item in results)
    after_inference["process"]["peak_allocated_mib"] = peak_process_allocated
    after_inference["process"]["peak_reserved_mib"] = peak_process_reserved
    output = {
        "version": _project_version(voices_path.parent),
        "model": runtime.repo_id or DEFAULT_MODEL_REPO_ID,
        "gpu": gpu,
        "device": args.device,
        "source": str(voices_path),
        "voices": len(cases),
        "languages": len({case["language"] for case in cases}),
        "sample_interval_ms": args.sample_interval * 1000,
        "test_time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "stages": {
            "before_runtime": before_runtime,
            "after_voice_preparation": after_voice_preparation,
            "after_weights": after_weights,
            "after_inference": after_inference,
        },
        "peaks": {
            "process_allocated_mib": peak_process_allocated,
            "process_reserved_mib": peak_process_reserved,
            "inference_reserved_increment_mib": round(
                max(0.0, peak_process_reserved - after_weights["process"]["reserved_mib"]), 1
            ),
            "device_used_mib": peak_device_used,
            "device_increment_mib": round(
                max(0.0, peak_device_used - before_runtime["device"]["used_mib"]), 1
            ),
        },
        "by_language": _group_languages(results),
        "results": results,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"PEAK process_allocated={peak_process_allocated:.1f} MiB "
        f"process_reserved={peak_process_reserved:.1f} MiB "
        f"device_used={peak_device_used:.1f} MiB",
        flush=True,
    )
    print(f"RESULT {output_path}", flush=True)
    if not args.no_append:
        _append_summary(Path(args.summary_md), output, args.comment)
        _append_details(Path(args.details_md), output, args.comment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
