# VRAM Usage Benchmark

This benchmark is intentionally separate from the HTTP generation-performance benchmark. It runs the real Kokoro runtime in a fresh disposable Docker container so PyTorch can report memory for the Kokoro process without including other applications.

The benchmark records:

1. Process and whole-device memory before the runtime is created.
2. Memory after all voice files and language pipelines are prepared.
3. Memory after model weights are loaded onto the GPU without inference.
4. Exact PyTorch peak allocated and reserved memory for every voice.
5. Whole-device peak memory sampled every 50 ms during every generation.
6. Per-language and per-voice peak summaries.

Prepare the host first by stopping Kokoro and other avoidable GPU workloads, then run:

```bash
task imagestop
task benchmark-vram VRAM_BENCHMARK_COMMENT="clean GPU baseline"
```

The process values are isolated to Kokoro. Whole-device values include display usage, drivers, and other processes and are included to capture CUDA context or native allocations outside PyTorch's allocator. The benchmark calls `torch.cuda.empty_cache()` before every voice so each voice begins with the same model-resident baseline.

For a non-recording implementation check using one voice:

```bash
task benchmark-vram-smoke
```

Do not compare official runs unless they use the same image, GPU, voice source, and sampling interval. A future concurrency benchmark should remain separate because concurrent requests have different latency and VRAM characteristics.
