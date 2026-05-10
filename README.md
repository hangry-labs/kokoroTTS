# kokoroTTS

`kokoroTTS` packages Kokoro TTS as a practical self-hosted app with:
- Gradio UI on `/`
- HTTP API on `/tts/*`
- One container, one port (`7860`)
- 54 voices across American English, British English, Japanese, Mandarin, Spanish, French, Hindi, Italian, and Brazilian Portuguese

This repository is a focused fork of the upstream project:
- This repo: https://github.com/TheMasterOfDisasters/kokoroTTS
- Upstream model/library: https://github.com/hexgrad/kokoro

## Release

### v0.2-snapshot
- Added a root `VERSION` file for the app/runtime release label.
- Kept Python package metadata on a PEP 440-compatible development version for reliable builds.
- Exposed the full Kokoro-82M voice set in the UI/API.
- Added optional `wav`, `mp3`, `flac`, and `ogg` output formats in the UI/API while keeping WAV as the default.
- Added multilingual Docker prefetch support, including UniDic for offline Japanese synthesis.
- Added `task imageapi-voice` for quick audible smoke tests with specific voices.

Expected Docker tags:

```bash
docker run -p 7860:7860 --gpus all sensejworld/kokorotts:v0.2
docker run -p 7860:7860 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 sensejworld/kokorotts:v0.2
```

### v0.0.1
- Initial release of the KokoroTTS Docker image.
- Trimmed the image to keep it slim and practical for deployment.
- Baked required models and assets into the image for offline use.
- Added startup/runtime details showing which specific GPU is detected.
- Introduced Dockerized WebUI + API setup for easy local or server deployment.
- Added integration-friendly API support for compatibility with the MeloTTS image, making it easier to swap between them in existing applications.
- Enabled automated build and deployment workflow.

## Quick Start (Docker)

Build:

```bash
docker build -t kokorotts:local .
```

Run (CPU):

```bash
docker run -p 7860:7860 kokorotts:local
```

Run (NVIDIA GPU):

```bash
docker run -p 7860:7860 --gpus all kokorotts:local
```

Open UI at `http://localhost:7860`.

## API

Ping:

```bash
curl -sS http://localhost:7860/tts/ping
```

Synthesize:

```bash
curl -X POST "http://localhost:7860/tts/convert" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from kokoroTTS.","voice":"af_heart","speed":1.0,"device":"auto"}' \
  --output hello.wav
```

Optional output formats:

```bash
curl -X POST "http://localhost:7860/tts/convert" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from kokoroTTS.","voice":"af_heart","output_format":"mp3"}' \
  --output hello.mp3
```

Supported `output_format` values are `wav`, `mp3`, `flac`, and `ogg`. Omitting the field keeps the original WAV response behavior.

## Taskfile Workflow (Windows-friendly)

From repo root:

```bash
task image
task imagerun
task imageweb
task imageapi
task imageapi-format API_FORMAT=mp3
```

Hot-swap local app code into container (no rebuild loop):

```bash
task localrun
task logs
```

Release from a clean tree:

```bash
task release DRY_RUN=1
task release
```

## Runtime Environment Variables

- `KOKORO_REPO_ID` (default: `hexgrad/Kokoro-82M`)
- `KOKOROTTS_DEVICE` (default: `auto`; supports `cpu`, `cuda:0`, `cuda:1`, ...)
- `CUDA_VISIBLE_DEVICES` (GPU visibility control)
- `HF_TOKEN` (optional, for higher HF Hub limits)
- `PORT` (default: `7860`)
- `UVICORN_RELOAD` (`1` for auto-reload in hot-swap mode)

## Voices and Languages

The UI voice dropdown exposes all currently bundled Kokoro-82M voices:

- American English (`a*`)
- British English (`b*`)
- Japanese (`j*`)
- Mandarin Chinese (`z*`)
- Spanish (`e*`)
- French (`f*`)
- Hindi (`h*`)
- Italian (`i*`)
- Brazilian Portuguese (`p*`)

## Offline Behavior

- Docker build prefetches model/config + voice assets into Hugging Face cache.
- Runtime sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.
- A built/pulled image is intended to run without internet access.

## Project Layout

- `kokorotts/app.py`: UI + FastAPI app mounted on one service.
- `kokorotts/model.py` and `kokorotts/pipeline.py`: core inference pipeline.
- `kokorotts/prefetch_assets.py`: build-time asset prefetch.
- `Dockerfile`: production image build/run definition.
- `Taskfile.yml`: local build/run/debug automation.
- `docs/dockerhub.md`: Docker Hub description copy.


## 📜 License
This fork is licensed under the Apache License 2.0.  
Original work by [hexgrad](https://github.com/hexgrad) in [Kokoro](https://github.com/hexgrad/kokoro).
