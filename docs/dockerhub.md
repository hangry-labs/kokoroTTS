<p>
  <a href="https://hangry-labs.github.io/kokoroTTS/examples/">
    <img src="https://github.com/Hangry-Labs/kokoroTTS/raw/main/assets/kokoro_logo_horizontal.webp" alt="Hangry Labs KokoroTTS logo">
  </a>
</p>

<p>
  <strong>English</strong> ·
  <a href="https://github.com/Hangry-Labs/kokoroTTS/blob/main/README.nb.md">Norsk bokmål</a> ·
  <a href="https://github.com/Hangry-Labs/kokoroTTS/blob/main/README.pl.md">Polski</a> ·
  <a href="https://github.com/Hangry-Labs/kokoroTTS/blob/main/README.ja.md">日本語</a> ·
  <a href="https://github.com/Hangry-Labs/kokoroTTS/blob/main/README.zh.md">简体中文</a> ·
  <a href="https://github.com/Hangry-Labs/kokoroTTS/blob/main/README.es.md">Español</a>
</p>

# Hangry Labs KokoroTTS

Easy-to-run Kokoro text-to-speech Docker images with a browser UI and HTTP API included.

This Hangry Labs fork is built for people who want text to speech to work without a long setup. Install Docker, run one command, open the local UI, or call the API from your own application.

## Listen First

Voice examples are available here:

https://hangry-labs.github.io/kokoroTTS/examples/

The examples page includes MP3 previews for all 173 voices across American English, British English, Japanese, Mandarin Chinese, Spanish, French, Hindi, Italian, Brazilian Portuguese, German, and Vietnamese. Selecting a language filters the examples and switches the page text to that language.

## Project Links

- Voice examples: https://hangry-labs.github.io/kokoroTTS/examples/
- GitHub repository: https://github.com/Hangry-Labs/kokoroTTS
- Issues and support: https://github.com/Hangry-Labs/kokoroTTS/issues
- Hangry Labs: https://hangrylabs.app/

## Quick Start

### Stable version:

Released images are pinned by both tag and registry digest so Docker verifies the exact published image.

Run with NVIDIA GPU support:

```bash
docker run -p 7860:7860 --gpus all -v kokorotts_data:/app/persistent hangrylabs/kokorotts:v1.0@sha256:5afef5b9f3d779e56248992274d46a66c0715110eb09e47e1332c39951361f24
```

Run on CPU:

```bash
docker run -p 7860:7860 -v kokorotts_data:/app/persistent hangrylabs/kokorotts:v1.0@sha256:5afef5b9f3d779e56248992274d46a66c0715110eb09e47e1332c39951361f24
```

Run on a specific GPU:

```bash
docker run -p 7860:7860 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 -v kokorotts_data:/app/persistent hangrylabs/kokorotts:v1.0@sha256:5afef5b9f3d779e56248992274d46a66c0715110eb09e47e1332c39951361f24
```

Run the tiny image without baked model assets:

```bash
docker run -p 7860:7860 --gpus all -v kokorotts_data:/app/persistent hangrylabs/kokorotts:v1.0_tiny@sha256:c8c044a2968cbd6cc49c811176fb856c000af324f8b01a027db91e38f1a863fa
```

The tiny image is smaller, but it downloads model and voice files after startup and stores them in the Docker volume. If you just want KokoroTTS to work quickly, use one of the standard `v1.0` commands above.

### Latest image (`v1.1-snapshot`):

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
- Full 173-voice catalog exposed in the UI and API, including dedicated German, Vietnamese, and enhanced Chinese models
- Persistent System controls for choosing independently loaded model packs and their served voices
- Optional Streamable HTTP MCP tools with expiring URL-only audio results for AI agents
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
  -d '{"text":"ココロ テキスト読み上げへようこそ。","voice":"jf_alpha","output_format":"mp3"}' \
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
  -d '{"input_type":"ssml","text":"<speak><voice name=\"af_heart\">Good morning.</voice><voice name=\"am_michael\">Coffee first?</voice></speak>","voice":"af_heart","output_format":"mp3"}' \
  -o dialogue.mp3
```

The supported experimental subset includes multi-voice dialogue with `<voice>`, explicit language routing with `<lang>`, optional per-segment `<prosody speed="0.9" pitch="+2st" tempo="1.05" volume="0.9">`, bounded `<break>`, `<sub>`, `<say-as>`, and direct IPA `<phoneme>` elements. Every prosody attribute is optional and omitted values do not change the sound. `<lang>` keeps the current voice and may retain its accent; `<voice>` selects an enabled native voice for reliable multilingual dialogue. Hidden model padding is removed between SSML turns: adjacent turns use a 100 ms default handoff, while `<break>` sets the complete pause and accepts `0ms` for no gap. Open the SSML guide beside the UI mode button for exact rules and limits, or listen to five complete scripts on the public [SSML examples page](https://hangry-labs.github.io/kokoroTTS/examples/ssml.html).

`GET /tts/ping` remains available for native API clients. Interactive API documentation is served at `http://localhost:7860/tts/docs`.

## MCP for AI Agents

The opt-in MCP endpoint at `/mcp` exposes five intentionally simple tools: `get_health`, `manage_model_packs`, `get_available_voices`, `talk_simple`, and `talk_advanced`. Package management uses five explicit Boolean fields and confirms the complete resulting state. Voice discovery uses one required group number: `0` for every currently enabled voice or `1-5` for a specific checkpoint family. `talk_simple` needs only text, a self-contained default voice number from `1-11`, and link TTL, so an agent can speak any supported language without a discovery call. `talk_advanced` accepts exact voice IDs and exposes format, SSML, speed, pitch, tempo, volume, and normalization. Generated audio is returned as an expiring HTTP link plus metadata, never as audio bytes or base64 in the MCP response. The complete request schemas, number mappings, and examples are in the repository README.

For a trusted private network, enable it and publish a link address reachable by the caller:

```bash
docker run -p 7860:7860 --gpus all \
  -e KOKOROTTS_ENABLE_MCP=1 \
  -e KOKOROTTS_MCP_BASE_URL=http://192.168.0.10:7860 \
  -v kokorotts_data:/app/persistent \
  hangrylabs/kokorotts:latest
```

Replace the example address with the KokoroTTS host. Connect the agent to `http://<kokoro-host>:7860/mcp`. MCP has no authentication in this release and is disabled by default; use it only on a trusted local/private network. The API key option for `/v1/*` does not protect MCP.

## Image Tags

- Current release tag: `v1.0`
- Future release tags use the same pattern: `vX.Y`
- Tiny tags use the pattern `vX.Y_tiny`

Example release tags:

```bash
docker run -p 7860:7860 --gpus all -v kokorotts_data:/app/persistent hangrylabs/kokorotts:v1.0@sha256:5afef5b9f3d779e56248992274d46a66c0715110eb09e47e1332c39951361f24
docker run -p 7860:7860 --gpus "device=1" -e CUDA_VISIBLE_DEVICES=1 -v kokorotts_data:/app/persistent hangrylabs/kokorotts:v1.0@sha256:5afef5b9f3d779e56248992274d46a66c0715110eb09e47e1332c39951361f24
docker run -p 7860:7860 --gpus all -v kokorotts_data:/app/persistent hangrylabs/kokorotts:v1.0_tiny@sha256:c8c044a2968cbd6cc49c811176fb856c000af324f8b01a027db91e38f1a863fa
```

The standard `vX.Y` image is the recommended image for most users. It includes the standard Kokoro model, dedicated German and Vietnamese models, the enhanced Kokoro v1.1 Chinese model, all voice packs, and required language assets for offline-friendly use after the image is pulled.

Tiny images use the `vX.Y_tiny` tag pattern. They keep runtime and language dependencies, but skip baked Hugging Face model and voice files. Current images use the optional `/app/persistent` volume so downloaded assets and settings survive container replacement.

All five model packs are served by default. The System controls can disable the shared standard Kokoro checkpoint, German Martin, German Victoria, Kokoro Vietnamese, or Kokoro v1.1 Chinese. The 54 standard voices, 14 Vietnamese voices, and 103 v1.1 Chinese/English voices remain together within their respective packs because each group shares one model and has the same VRAM cost. Models load into CPU/GPU memory on first use, and disabling a pack releases cached models after active generations finish. With the tiny image, a disabled custom checkpoint is not downloaded unless its pack is later enabled and called.

## Links

- Voice examples: https://hangry-labs.github.io/kokoroTTS/examples/
- GitHub: https://github.com/Hangry-Labs/kokoroTTS
- Hangry Labs: https://hangrylabs.app/
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

Enhanced Mandarin and mixed Chinese-English synthesis uses the Apache-2.0 Kokoro v1.1 Chinese model and voices:

- https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh

KokoroTTS-owned and adapted upstream source remains Apache-2.0. The server
image is a mixed-license distribution containing GPL, LGPL, and other
third-party components. Commercial use is permitted, while redistribution
must follow the applicable notices, license, and corresponding-source terms.
Every full and tiny image includes a checksum-verified compliance bundle at
`/app/third_party`; details are maintained in the repository's `LICENSE` and
`THIRD_PARTY_NOTICES.md` files. Original Kokoro copyright remains with the
upstream authors; Hangry Labs maintains the Docker packaging, web UI/API
integration, examples page, documentation, release tooling, and other
modifications in this fork.
