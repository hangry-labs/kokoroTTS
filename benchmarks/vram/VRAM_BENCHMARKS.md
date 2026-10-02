# KokoroTTS VRAM Benchmarks

Append one row per official isolated-container run. Process allocated/reserved values come from PyTorch and exclude other applications. Device values include every process using the selected GPU.

| Version | Model | GPU | Total VRAM | Device before runtime | Weights allocated | Weights reserved | Peak allocated | Peak reserved | Inference increment | Device peak | Device increment | Voices | Sample interval | Comment | Test time |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
