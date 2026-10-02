# KokoroTTS Performance Benchmarks

Append one row per official voice-generation benchmark. Warmup requests are excluded. RTF is request time divided by generated audio duration, so lower is better; realtime speed is generated audio duration divided by request time, so higher is better.

| Version | Model | GPU | Device | Voices | Repeats | Requests | Characters | Audio | Total time | Mean request | P95 request | RTF | Realtime speed | Comment | Test time |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 0.4-snapshot | hexgrad/Kokoro-82M | NVIDIA GeForce RTX 5070 Ti (16303 MiB) | auto | 54 | 5 | 270 | 78060 | 5793.000s | 363.145s | 1.345s | 2.027s | 0.0627 | 15.95x | Python 3.13 v0.4 all-voice baseline | 03.10.2026 00:27:33 |
| 0.4-snapshot | hexgrad/Kokoro-82M | NVIDIA GeForce RTX 5070 Ti (16303 MiB) | auto | 54 | 5 | 270 | 78060 | 5793.000s | 365.698s | 1.354s | 2.061s | 0.0631 | 15.84x |  | 03.10.2026 00:41:38 |
