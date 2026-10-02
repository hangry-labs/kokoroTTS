from __future__ import annotations

import html
import subprocess


GPU_HISTORY: dict[int, list[int]] = {}


def read_gpu_stats() -> list[dict[str, float | int | str]]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
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

    rows: list[dict[str, float | int | str]] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 7:
            continue
        try:
            rows.append(
                {
                    "index": int(float(parts[0])),
                    "name": parts[1],
                    "utilization": min(100, max(0, int(float(parts[2])))),
                    "memory_used": max(0, int(float(parts[3]))),
                    "memory_total": max(0, int(float(parts[4]))),
                    "temperature": int(float(parts[5])),
                    "power": max(0, float(parts[6])),
                }
            )
        except ValueError:
            continue
    return rows


def gpu_history_points(values: list[int], width: int = 180, height: int = 44) -> str:
    if not values:
        return f"0,{height} {width},{height}"
    if len(values) == 1:
        y = height - (values[0] / 100 * height)
        return f"0,{y:.1f} {width},{y:.1f}"
    return " ".join(
        f"{index * width / (len(values) - 1):.1f},{height - (value / 100 * height):.1f}"
        for index, value in enumerate(values)
    )


def gpu_monitor_html() -> str:
    stats = read_gpu_stats()
    if not stats:
        return """
<div class="gpu-monitor">
  <div class="gpu-monitor-title">GPU Monitor</div>
  <div class="gpu-monitor-muted">nvidia-smi unavailable</div>
</div>
"""

    cards = []
    for item in stats:
        index = int(item["index"])
        usage = int(item["utilization"])
        history = GPU_HISTORY.setdefault(index, [])
        history.append(usage)
        del history[:-60]
        points = gpu_history_points(history)
        memory_used = float(item["memory_used"]) / 1024
        memory_total = float(item["memory_total"]) / 1024
        memory_percent = 0 if memory_total <= 0 else min(100, memory_used / memory_total * 100)
        cards.append(
            f"""
  <div class="gpu-card">
    <div class="gpu-card-head">
      <strong>GPU {index}</strong>
      <span>{html.escape(str(item["name"]))}</span>
    </div>
    <div class="gpu-metric-row">
      <span>Load</span>
      <strong>{usage}%</strong>
    </div>
    <div class="gpu-bar"><span style="width:{usage}%"></span></div>
    <svg class="gpu-sparkline" viewBox="0 0 180 44" preserveAspectRatio="none" aria-hidden="true">
      <polyline points="{points}" fill="none" stroke="#ff8a1f" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"></polyline>
    </svg>
    <div class="gpu-metric-row">
      <span>VRAM</span>
      <strong>{memory_used:.1f}/{memory_total:.1f} GB</strong>
    </div>
    <div class="gpu-bar gpu-vram"><span style="width:{memory_percent:.1f}%"></span></div>
    <div class="gpu-foot">
      <span>{int(item["temperature"])} C</span>
      <span>{float(item["power"]):.0f} W</span>
    </div>
  </div>
"""
        )

    return f"""
<div class="gpu-monitor">
  <div class="gpu-monitor-title">GPU Monitor</div>
  <div class="gpu-card-grid">{''.join(cards)}</div>
</div>
"""
