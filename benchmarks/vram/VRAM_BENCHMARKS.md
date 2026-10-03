# KokoroTTS VRAM Benchmarks

Append one row per official isolated-container run. Process allocated/reserved values come from PyTorch and exclude other applications. Device values include every process using the selected GPU.

| Version | Model | GPU | Total VRAM | Device before runtime | Initial weights allocated | Initial weights reserved | Peak allocated | Peak reserved | Inference increment | Device peak | Device increment | Voices | Sample interval | Comment | Test time |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 0.4-snapshot | hexgrad/Kokoro-82M | NVIDIA GeForce RTX 5070 Ti (16303 MiB) | 16302.6 MiB | 1293.6 MiB | 317.6 MiB | 332.0 MiB | 1725.1 MiB | 2052.0 MiB | 1720.0 MiB | 3413.6 MiB | 2120.0 MiB | 70 | 50 ms | Official quiet-GPU RTX 5070 Ti baseline for v0.4-snapshot; full catalog with lifecycle, per-language, and per-voice measurements | 2026-10-03 03:20:48 UTC |
