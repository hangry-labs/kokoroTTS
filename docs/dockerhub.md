<p>
  <a href="https://hangry-labs.github.io/kokoroTTS/examples/">
    <img src="https://github.com/Hangry-Labs/kokoroTTS/raw/main/assets/kokoro_logo_horizontal.webp" alt="Hangry Labs KokoroTTS logo">
  </a>
</p>

# Hangry Labs KokoroTTS

Easy-to-run Kokoro text-to-speech Docker images with a browser UI and HTTP API included.

This Hangry Labs fork is built for people who want text to speech to work without a long setup. Install Docker, run one command, open the local UI, or call the API from your own application.

## Listen First

Voice examples are available here:

https://hangry-labs.github.io/kokoroTTS/examples/

The examples page includes MP3 previews for all 70 voices across American English, British English, Japanese, Mandarin Chinese, Spanish, French, Hindi, Italian, Brazilian Portuguese, German, and Vietnamese. Selecting a language filters the examples and switches the page text to that language.

## Project Links

- Voice examples: https://hangry-labs.github.io/kokoroTTS/examples/
- GitHub repository: https://github.com/Hangry-Labs/kokoroTTS
- Issues and support: https://github.com/Hangry-Labs/kokoroTTS/issues
- Hangry Labs: https://nuggies.website/

## Quick Start

### Stable version:

Run with NVIDIA GPU support:

```bash
docker run -p 7860:7860 --gpus all hangrylabs/kokorotts:v0.3
```

Run on CPU:

```bash
docker run -p 7860:7860 hangrylabs/kokorotts:v0.3
```

Run on a specific GPU:

```bash
docker run -p 7860:7860 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 hangrylabs/kokorotts:v0.3
```

Run the tiny image without baked model assets:

```bash
docker run -p 7860:7860 --gpus all -v kokorotts_hf_cache:/app/.cache/huggingface hangrylabs/kokorotts:v0.3_tiny
```

The tiny image is smaller, but it downloads model and voice files after startup and stores them in the Docker volume. If you just want KokoroTTS to work quickly, use one of the standard `v0.3` commands above.

### Latest image:

Choose one complete command below.

Run the full image with NVIDIA GPU support:

```bash
docker run -p 7860:7860 --gpus all -v kokorotts_data:/app/persistent hangrylabs/kokorotts:latest
```

Run the full image on CPU:

```bash
docker run -p 7860:7860 -v kokorotts_data:/app/persistent hangrylabs/kokorotts:latest
```

Run the full image on GPU index `1`:

```bash
docker run -p 7860:7860 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 -v kokorotts_data:/app/persistent hangrylabs/kokorotts:latest
```

Run the tiny image with NVIDIA GPU support:

```bash
docker run -p 7860:7860 --gpus all -v kokorotts_data:/app/persistent hangrylabs/kokorotts:latest_tiny
```

Use the stable version tag when you want repeatable deployments. Use `latest` when you want the newest published full image, and `latest_tiny` when you want the newest published tiny image. The `/app/persistent` volume is recommended but optional; without it, downloaded assets and saved settings remain inside the current container and are lost when it is removed.

Then open:

http://localhost:7860

The container includes the web UI and the HTTP API on the same port.

## What You Get

<p>
  <img src="https://github.com/Hangry-Labs/kokoroTTS/raw/main/assets/ui.webp" alt="KokoroTTS browser interface">
</p>

- Responsive browser audio workspace with Generate, Stream, API, and System views
- Waveform playback, seeking, download controls, and cancellable MP3 streaming
- OpenAI-compatible and Kokoro-native HTTP APIs for applications and automation
- MP3 output from the UI by default
- OpenAI-compatible MP3 defaults plus backward-compatible WAV defaults on the native API
- WAV, MP3, FLAC, OGG Vorbis, Opus, AAC, and raw PCM output support
- Full 70-voice catalog exposed in the UI and API, including dedicated German and Vietnamese models
- Persistent System controls for choosing independently loaded model packs and their served voices
- GPU support when Docker/NVIDIA support is available
- Offline-friendly usage with the standard full image once it is available locally

## API Examples

### OpenAI-Compatible API

Use this endpoint with applications and SDKs that support OpenAI text to speech. It returns MP3 by default:

```bash
curl -X POST "http://localhost:7860/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro","input":"Hello from Hangry Labs KokoroTTS","voice":"af_heart"}' \
  -o hello.mp3
```

Point the official Python client at `http://localhost:7860/v1`, use `kokoro` as the model, and use a voice id from `GET /tts/voices`. This API supports MP3, Opus, AAC, FLAC, WAV, and raw PCM. Optional authentication can be enabled by setting `KOKOROTTS_API_KEY` on the container; it is disabled by default for local use.

### KokoroTTS Native API

Use the native API for pitch, tempo, volume, normalization, device selection, discovery, and segment streaming. It returns WAV by default for backward compatibility:

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
  -d '{"text":"Ã£â€šÂ³Ã£â€šÂ³Ã£Æ’Â­ Ã£Æ’â€ Ã£â€šÂ­Ã£â€šÂ¹Ã£Æ’Ë†Ã¨ÂªÂ­Ã£ÂÂ¿Ã¤Â¸Å Ã£Ââ€™Ã£ÂÂ¸Ã£â€šË†Ã£Ââ€ Ã£Ââ€œÃ£ÂÂÃ£â‚¬â€š","voice":"jf_alpha","output_format":"mp3"}' \
  -o kokoro-ja.mp3
```

`POST /tts/convert` is still available as a backward-compatible synthesis alias.

Health check:

```bash
curl http://localhost:7860/health/ready
```

Experimental SSML is opt-in on the native API and in the browser UI. Plain text remains the default:

```bash
curl -X POST "http://localhost:7860/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"input_type":"ssml","text":"<speak>Hello.<break time=\"500ms\"/>Welcome.</speak>","voice":"af_heart","output_format":"mp3"}' \
  -o ssml.mp3
```

The supported experimental subset includes bounded `<break>`, `<sub>`, `<say-as>`, and direct IPA `<phoneme>` elements. Open the SSML guide beside the UI mode button for exact rules and limits.

`GET /tts/ping` remains available for native API clients. Interactive API documentation is served at `http://localhost:7860/tts/docs`.

## Image Tags

- Current release tag: `v0.3`
- Future release tags use the same pattern: `vX.Y`
- Tiny tags use the pattern `vX.Y_tiny`

Example release tags:

```bash
docker run -p 7860:7860 --gpus all hangrylabs/kokorotts:v0.3
docker run -p 7860:7860 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 hangrylabs/kokorotts:v0.3
docker run -p 7860:7860 --gpus all -v kokorotts_hf_cache:/app/.cache/huggingface hangrylabs/kokorotts:v0.3_tiny
```

The standard `vX.Y` image is the recommended image for most users. It includes the standard Kokoro model, dedicated German and Vietnamese models, voice packs, and required language assets for offline-friendly use after the image is pulled.

Tiny images use the `vX.Y_tiny` tag pattern. They keep runtime and language dependencies, but skip baked Hugging Face model and voice files. Current images use the optional `/app/persistent` volume so downloaded assets and settings survive container replacement. The stable `v0.3_tiny` command above retains its original `/app/.cache/huggingface` layout.

All four model packs are served by default. The System controls can disable the shared standard Kokoro checkpoint, German Martin, German Victoria, or Kokoro Vietnamese. The 54 standard voices remain together, and the 14 Vietnamese voices remain together, because each group shares one model and has the same VRAM cost. Models load into CPU/GPU memory on first use, and disabling a pack releases cached models after active generations finish. With the tiny image, a disabled custom checkpoint is not downloaded unless its pack is later enabled and called.

## Links

- Voice examples: https://hangry-labs.github.io/kokoroTTS/examples/
- GitHub: https://github.com/Hangry-Labs/kokoroTTS
- Hangry Labs: https://nuggies.website/
- Issues: https://github.com/Hangry-Labs/kokoroTTS/issues

Docker Hub comments are not monitored regularly. GitHub Issues are the best place to report bugs.

## Attribution

This is an independently maintained fork of the original Kokoro project by hexgrad:

https://github.com/hexgrad/kokoro

German synthesis uses the Apache-2.0 Kikiri German Martin and Victoria releases:

- https://huggingface.co/kikiri-tts/kikiri-german-martin
- https://huggingface.co/kikiri-tts/kikiri-german-victoria

Vietnamese synthesis uses the Apache-2.0 ContextBoxAI Kokoro Vietnamese model and Kokoro-Vietnamese integration:

- https://huggingface.co/contextboxai/Kokoro-Vietnamese
- https://github.com/iamdinhthuan/Kokoro-Vietnamese

License and attribution are preserved in the repository's `LICENSE` and `THIRD_PARTY_NOTICES.md` files. Original Kokoro copyright remains with the upstream authors; Hangry Labs maintains the Docker packaging, web UI/API integration, examples page, documentation, release tooling, and other modifications in this fork.
