from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable


GpuValue = float | int | str | None
GPU_HISTORY_FIELDS = (
    "utilization",
    "memory_utilization",
    "memory_used",
    "temperature",
    "power",
    "fan_speed",
    "graphics_clock",
    "memory_clock",
)


def _number(value: str, *, integer: bool = False) -> float | int | None:
    if value.strip().lower() in {"", "n/a", "[n/a]", "not supported"}:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return int(number) if integer else number


def read_gpu_stats() -> list[dict[str, GpuValue]]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,fan.speed,power.draw,power.limit,clocks.current.graphics,clocks.max.graphics,clocks.current.memory,clocks.max.memory,pstate,pcie.link.gen.current,pcie.link.width.current",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
            shell=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []

    rows: list[dict[str, GpuValue]] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 17:
            continue
        index = _number(parts[0], integer=True)
        if index is None:
            continue
        utilization = _number(parts[2], integer=True)
        memory_utilization = _number(parts[3], integer=True)
        rows.append(
            {
                "index": index,
                "name": parts[1],
                "utilization": None if utilization is None else min(100, max(0, utilization)),
                "memory_utilization": (
                    None if memory_utilization is None else min(100, max(0, memory_utilization))
                ),
                "memory_used": _number(parts[4], integer=True),
                "memory_total": _number(parts[5], integer=True),
                "temperature": _number(parts[6], integer=True),
                "fan_speed": _number(parts[7], integer=True),
                "power": _number(parts[8]),
                "power_limit": _number(parts[9]),
                "graphics_clock": _number(parts[10], integer=True),
                "graphics_clock_max": _number(parts[11], integer=True),
                "memory_clock": _number(parts[12], integer=True),
                "memory_clock_max": _number(parts[13], integer=True),
                "performance_state": parts[14] if parts[14] not in {"", "N/A", "[N/A]"} else None,
                "pcie_generation": _number(parts[15], integer=True),
                "pcie_width": _number(parts[16], integer=True),
            }
        )
    return rows


class GpuMonitor:
    def __init__(
        self,
        reader: Callable[[], list[dict[str, GpuValue]]] = read_gpu_stats,
        *,
        sample_interval: float = 1.0,
        idle_timeout: float = 60.0,
        history_seconds: float = 600.0,
    ) -> None:
        self._reader = reader
        self._sample_interval = sample_interval
        self._idle_timeout = idle_timeout
        self._history_seconds = history_seconds
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_request = 0.0
        self._stats: list[dict[str, GpuValue]] = []
        self._history: dict[int, list[dict[str, float | int]]] = {}

    def request_snapshot(self) -> dict[str, object]:
        thread_to_start: threading.Thread | None = None
        with self._lock:
            self._last_request = time.monotonic()
            if self._thread is None:
                thread_to_start = threading.Thread(
                    target=self._run,
                    name="kokorotts-gpu-monitor",
                    daemon=True,
                )
                self._thread = thread_to_start

        if thread_to_start is not None:
            self._sample()
            thread_to_start.start()
        return self._snapshot_payload()

    def close(self) -> None:
        self._stop.set()
        with self._lock:
            thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=max(1.0, self._sample_interval * 2))

    def _run(self) -> None:
        try:
            while not self._stop.wait(self._sample_interval):
                with self._lock:
                    idle_for = time.monotonic() - self._last_request
                if idle_for >= self._idle_timeout:
                    return
                self._sample()
        finally:
            with self._lock:
                if self._thread is threading.current_thread():
                    self._thread = None

    def _sample(self) -> None:
        stats = self._reader()
        timestamp = int(time.time() * 1000)
        cutoff = timestamp - int(self._history_seconds * 1000)
        with self._lock:
            self._stats = [dict(gpu) for gpu in stats]
            for gpu in stats:
                index = gpu.get("index")
                if not isinstance(index, int):
                    continue
                sample: dict[str, float | int] = {"timestamp": timestamp}
                for field in GPU_HISTORY_FIELDS:
                    value = gpu.get(field)
                    if isinstance(value, (float, int)):
                        sample[field] = value
                self._history.setdefault(index, []).append(sample)
            for index, samples in list(self._history.items()):
                recent = [sample for sample in samples if sample["timestamp"] >= cutoff]
                if recent:
                    self._history[index] = recent
                else:
                    del self._history[index]

    def _snapshot_payload(self) -> dict[str, object]:
        with self._lock:
            return {
                "gpus": [dict(gpu) for gpu in self._stats],
                "history": {
                    str(index): [dict(sample) for sample in samples]
                    for index, samples in self._history.items()
                },
                "sample_interval_seconds": self._sample_interval,
                "idle_timeout_seconds": self._idle_timeout,
            }


GPU_MONITOR = GpuMonitor()
