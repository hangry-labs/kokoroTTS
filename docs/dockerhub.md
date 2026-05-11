<p>
  <a href="https://hangry-labs.github.io/kokoroTTS/examples/">
    <img src="https://github.com/Hangry-Labs/kokoroTTS/raw/main/logo.jpg" alt="Hangry Labs KokoroTTS logo">
  </a>
</p>

# Hangry Labs KokoroTTS

Easy-to-run Kokoro text-to-speech Docker images with a browser UI and HTTP API included.

This Hangry Labs fork is built for people who want text to speech to work without a long setup. Install Docker, run one command, open the local UI, or call the API from your own application.

## Listen First

Voice examples are available here:

https://hangry-labs.github.io/kokoroTTS/examples/

The examples page includes MP3 previews for all 54 Kokoro voices across American English, British English, Japanese, Mandarin Chinese, Spanish, French, Hindi, Italian, and Brazilian Portuguese. Selecting a language filters the examples and switches the page text to that language.

## Project Links

- Voice examples: https://hangry-labs.github.io/kokoroTTS/examples/
- GitHub repository: https://github.com/Hangry-Labs/kokoroTTS
- Issues and support: https://github.com/Hangry-Labs/kokoroTTS/issues
- Hangry Labs: https://nuggies.website/

## Quick Start

### Stable version:

Run with NVIDIA GPU support:

```bash
docker run -p 7860:7860 --gpus all hangrylabs/kokorotts:v0.2
```

Run on CPU:

```bash
docker run -p 7860:7860 hangrylabs/kokorotts:v0.2
```

Run on a specific GPU:

```bash
docker run -p 7860:7860 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 hangrylabs/kokorotts:v0.2
```

Run the tiny image without baked model assets:

```bash
docker run -p 7860:7860 --gpus all -v kokorotts_hf_cache:/app/.cache/huggingface hangrylabs/kokorotts:v0.2_tiny
```

The tiny image is smaller, but it downloads model and voice files after startup and stores them in the Docker volume. If you just want KokoroTTS to work quickly, use one of the standard `v0.2` commands above.

### Latest image:

```bash
docker run -p 7860:7860 --gpus all hangrylabs/kokorotts:latest
docker run -p 7860:7860 hangrylabs/kokorotts:latest
docker run -p 7860:7860 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 hangrylabs/kokorotts:latest
docker run -p 7860:7860 --gpus all -v kokorotts_hf_cache:/app/.cache/huggingface hangrylabs/kokorotts:latest_tiny
```

Use the stable version tag when you want repeatable deployments. Use `latest` when you want the newest published full image, and `latest_tiny` when you want the newest published tiny image.

Then open:

http://localhost:7860

The container includes the web UI and the HTTP API on the same port.

## What You Get

- Browser UI for manual text-to-speech generation
- HTTP API for applications and automation
- MP3 output from the UI by default
- Backward-compatible WAV API responses unless `output_format` or `format` is requested
- WAV, MP3, FLAC, and OGG output support
- Full Kokoro-82M voice set exposed in the UI and API
- GPU support when Docker/NVIDIA support is available
- Offline-friendly usage with the standard full image once it is available locally

## API Example

Default API behavior returns WAV for backward compatibility:

```bash
curl -X POST "http://localhost:7860/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Hangry Labs KokoroTTS","voice":"af_heart"}' \
  -o hello.wav
```

Request MP3 when you want compact output:

```bash
curl -X POST "http://localhost:7860/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Hangry Labs KokoroTTS","voice":"af_heart","output_format":"mp3"}' \
  -o hello.mp3
```

Optional audio controls are neutral by default and can be enabled per request:

```bash
curl -X POST "http://localhost:7860/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Hangry Labs KokoroTTS","voice":"af_heart","output_format":"mp3","pitch_semitones":2,"tempo":1.1,"volume":0.9,"normalize":true}' \
  -o hello-styled.mp3
```

Use another voice:

```bash
curl -X POST "http://localhost:7860/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"text":"ã‚³ã‚³ãƒ­ ãƒ†ã‚­ã‚¹ãƒˆèª­ã¿ä¸Šã’ã¸ã‚ˆã†ã“ãã€‚","voice":"jf_alpha","output_format":"mp3"}' \
  -o kokoro-ja.mp3
```

`POST /tts/convert` is still available as a backward-compatible synthesis alias.

Health check:

```bash
curl http://localhost:7860/tts/ping
```

## Image Tags

- Current release tag: `v0.2`
- Future release tags use the same pattern: `vX.Y`
- Tiny tags use the pattern `vX.Y_tiny`

Example release tags:

```bash
docker run -p 7860:7860 --gpus all hangrylabs/kokorotts:v0.2
docker run -p 7860:7860 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 hangrylabs/kokorotts:v0.2
docker run -p 7860:7860 --gpus all -v kokorotts_hf_cache:/app/.cache/huggingface hangrylabs/kokorotts:v0.2_tiny
```

The standard `vX.Y` image is the recommended image for most users. It includes Kokoro model, voices, and required language assets for offline-friendly use after the image is pulled.

Tiny images use the `vX.Y_tiny` tag pattern. They keep runtime and language dependencies, but skip baked Hugging Face model and voice files. Use a persistent volume mounted at `/app/.cache/huggingface` so downloaded assets survive container replacement.

## Links

- Voice examples: https://hangry-labs.github.io/kokoroTTS/examples/
- GitHub: https://github.com/Hangry-Labs/kokoroTTS
- Hangry Labs: https://nuggies.website/
- Issues: https://github.com/Hangry-Labs/kokoroTTS/issues

Docker Hub comments are not monitored regularly. GitHub Issues are the best place to report bugs.

## Attribution

This is an independently maintained fork of the original Kokoro project by hexgrad:

https://github.com/hexgrad/kokoro

License and attribution are preserved in the repository. Original Kokoro copyright remains with the upstream authors; Hangry Labs maintains the Docker packaging, Web UI/API integration, examples page, documentation, release tooling, and other modifications in this fork.
