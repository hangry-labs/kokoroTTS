# 🗣️ KokoroTTS WebUI & API (Docker)

This is the Hangry Labs Docker image for [KokoroTTS](https://github.com/Hangry-Labs/kokoroTTS), based on the original [Kokoro](https://github.com/hexgrad/kokoro), with a focus on making it **easy to run, integrate, and use offline** without extra setup.

## ✅ Features
- Web interface (Gradio) on `/`
- HTTP API on `/tts/*`
- UI and API served from one container, one port
- Docker-ready for local or cloud use
- GPU acceleration when available
- Offline-ready image with prefetched model and voice assets
- Full Kokoro-82M voice set exposed in the UI/API

## 🚀 Quick Start
**CPU:**
```bash
docker run -p 7860:7860 hangrylabs/kokorotts:v0.2
```

**NVIDIA GPU:**
```bash
docker run -p 7860:7860 --gpus all hangrylabs/kokorotts:v0.2
```

**Specific GPU (example: GPU index `1`):**
```bash
docker run -p 7860:7860 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 hangrylabs/kokorotts:v0.2
```

Visit: [http://localhost:7860](http://localhost:7860) for the UI.  
*(First synthesis may take a little longer while the model and device warm up.)*

### 📡 API Usage Examples
**Ping:**
```bash
curl -sS http://localhost:7860/tts/ping
```

**Simple:**
```bash
curl -X POST "http://localhost:7860/tts/convert" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world from Kokoro.","voice":"af_heart","speed":1.0,"device":"auto"}' \
  --output hello.wav
```

**MP3 output:**
```bash
curl -X POST "http://localhost:7860/tts/convert" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world from Kokoro.","voice":"af_heart","output_format":"mp3"}' \
  --output hello.mp3
```

**Force CPU:**
```bash
curl -X POST "http://localhost:7860/tts/convert" \
  -H "Content-Type: application/json" \
  -d '{"text":"CPU synthesis","voice":"af_heart","speed":1.0,"device":"cpu"}' \
  --output cpu.wav
```

## ⚙️ Runtime Environment Variables
- `KOKORO_REPO_ID` (default: `hexgrad/Kokoro-82M`)
- `KOKOROTTS_DEVICE` (default: `auto`; options: `auto`, `cpu`, `cuda:0`, `cuda:1`, ...)
- `CUDA_VISIBLE_DEVICES` (Docker/NVIDIA visibility control)
- `HF_TOKEN` (optional, for higher Hugging Face rate limits)
- `PORT` (default: `7860`)

## 🗣️ Voices and Languages
The image exposes 54 bundled voices across American English, British English, Japanese, Mandarin Chinese, Spanish, French, Hindi, Italian, and Brazilian Portuguese.

Voice examples are available here:
https://hangry-labs.github.io/kokoroTTS/examples/

## 🌐 Offline Support
The image prefetches model files, configuration, and UI voice assets during the Docker build.

At runtime, offline flags are enabled:
- `HF_HUB_OFFLINE=1`
- `TRANSFORMERS_OFFLINE=1`

This means a pulled or prebuilt image can run on a machine without internet access.

## 🆘 Support & Issues
If you encounter a bug, have a feature request, or want to contribute:
- 📄 Open a **[GitHub Issue](https://github.com/Hangry-Labs/kokoroTTS/issues)** with full details
- 💬 Use the project repository for discussion and improvement ideas
- 🛠 Check existing issues before reporting duplicates

I respond fastest on GitHub — Docker Hub comments aren’t monitored regularly.

### 🔗 Common Help Topics
- **[KokoroTTS Project](https://github.com/Hangry-Labs/kokoroTTS)**
- **[Original Kokoro Project](https://github.com/hexgrad/kokoro)**
- **[Docker Hub Tags](https://hub.docker.com/r/hangrylabs/kokorotts/tags)**

## 📦 Notes
- The container serves both the Gradio UI and HTTP API from the same port.
- Default UI path: `/`
- API base path: `/tts/*`
- The `/tts/convert` endpoint returns WAV by default and also supports `mp3`, `flac`, and `ogg` through the optional `output_format` field.
- Recommended image tag: `hangrylabs/kokorotts:v0.2`

## Releases

### v0.2-snapshot
- Moved public project direction under Hangry Labs.
- Added a root `VERSION` file for the app/runtime release label.
- Kept Python package metadata on a PEP 440-compatible development version for reliable builds.
- Exposed the full Kokoro-82M voice set in the UI/API.
- Added optional `wav`, `mp3`, `flac`, and `ogg` output formats in the UI/API while keeping WAV as the default.
- Added language-aware UI sample texts with 10 lighthearted prompts per served language prefix.
- Added a Hangry Labs examples page with generated MP3 samples for all 54 voices.
- Added multilingual Docker prefetch support, including UniDic for offline Japanese synthesis.
- Added `task imageapi-voice` for quick audible smoke tests with specific voices.

Expected Docker tags:

```bash
docker run -p 7860:7860 --gpus all hangrylabs/kokorotts:v0.2
docker run -p 7860:7860 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 hangrylabs/kokorotts:v0.2
```

### v0.0.1
- Initial release of the KokoroTTS Docker image.
- Trimmed the image to keep it slim and practical for deployment.
- Baked required models and assets into the image for offline use.
- Added startup/runtime details showing which specific GPU is detected.
- Introduced Dockerized WebUI + API setup for easy local or server deployment.
- Added integration-friendly API support for compatibility with the MeloTTS image, making it easier to swap between them in existing applications.
- Enabled automated build and deployment workflow.

## 📜 License
This fork is licensed under the Apache License 2.0.  
Original work by [hexgrad](https://github.com/hexgrad) in [Kokoro](https://github.com/hexgrad/kokoro).
