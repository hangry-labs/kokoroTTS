# TTS Voice-Generation Benchmark

This benchmark measures KokoroTTS end to end through the public `/tts/generate` HTTP endpoint. `examples/voices.js` is the single source of benchmark voices and language-specific input text, so the benchmark automatically follows the examples page as voices are added or corrected.

An official run performs these steps:

1. Load every voice and its localized introduction text from `examples/voices.js`.
2. Generate one unmeasured warmup for the first voice in each language.
3. Generate WAV audio five times for every voice, rotating through all voices once per round.
4. Write raw results and overall, per-language, and per-voice aggregates to `results/latest.json`.
5. Append the overall result to `BENCHMARKS.md` and detailed language/voice tables to `DETAILS.md`.

Start the application, then run:

```bash
task benchmark-smoke
task benchmark-tts BENCHMARK_COMMENT="baseline"
```

`benchmark-smoke` checks the runner with two voices and one measured generation each without changing benchmark history. `benchmark-tts` measures all 54 current voices five times each, following one warmup request per language.

Useful overrides:

```bash
task benchmark-tts BENCHMARK_REPETITIONS=2 BENCHMARK_LIMIT=9
task benchmark-tts GPU_DEVICE=1 APP_DEVICE=cuda:0 BENCHMARK_COMMENT="second host GPU"
```

Keep the same image, host GPU, device selection, voice source, and repetition count when comparing runs. These numbers measure generation performance; voice quality still requires listening tests.
