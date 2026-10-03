# kokorotts

Standalone browser UI + HTTP API application for Kokoro TTS.

The app exposes 70 voices across American English, British English, Japanese, Mandarin, Spanish, French, Hindi, Italian, Brazilian Portuguese, German, and Vietnamese. Dedicated German and Vietnamese model families are selected automatically by voice.

## Run without Docker

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
python kokorotts/app.py
```

- UI: `http://localhost:7860/`
- OpenAI-compatible synthesis: `POST /v1/audio/speech`
- OpenAI-compatible models: `GET /v1/models`
- Health/readiness: `GET /health/ready`
- API ping: `GET /tts/ping`
- Native synthesis: `POST /tts/generate`
- Native streaming: `POST /tts/stream`
- Backward-compatible native synthesis alias: `POST /tts/convert`

## Docker and Task workflow

From repository root:

```bash
task deps
task image
task image-tiny
task imagerun
task imagerun-tiny
task imageweb
task imageapi
```

`task deps` regenerates the pinned root `requirements.txt` from `requirements.in` for the Docker/Linux runtime.

For hot-swapping local app files into the running container:

```bash
task localrun
task localrun-tiny
task logs
task client-test
```

`localrun` mounts the full local `kokorotts/` directory into `/app/kokorotts` and enables auto-reload via `UVICORN_RELOAD=1`.
It also enables `KOKOROTTS_UI_DEV=1`, which disables browser caching for the standalone UI and `/assets` files during development.
Both `imagerun` and `localrun` mount the named Docker volume `kokorotts_data` at `/app/persistent`, so lazy-downloaded Hugging Face assets and operator settings survive container and image rebuilds. Baked run tasks seed missing model files from the full image into the volume before startup; tiny run tasks keep runtime/language dependencies but skip baked Hugging Face model/voice assets and run online on first use. Direct Docker runs may omit the volume and keep the same data inside the current container. `task nuke` removes the data volume for true from-scratch tests.

Optional runtime env vars:

- `HF_TOKEN`: Hugging Face access token for higher hub rate limits.
- `KOKORO_REPO_ID`: override model repo (default `hexgrad/Kokoro-82M`).
- `KOKOROTTS_DEVICE`: default hardware (`auto`, `cpu`, `cuda:0`, ...).
- `KOKOROTTS_API_KEY`: optional bearer key required only for `/v1/*` routes.

## Model and offline mode

- Default repo is `hexgrad/Kokoro-82M`.
- For this repo, `kokorotts/model.py` resolves weights to `kokoro-v1_0.pth` (Kokoro v1.0).
- Default baked Docker build runs `kokorotts/prefetch_assets.py` to cache model/config + UI voice packs into the image.
- The baked image includes only deployable PyTorch assets for the dedicated German and Vietnamese families; the Vietnamese ONNX export and training checkpoints are not downloaded.
- Default baked runtime sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, so serving works without internet.
- Tiny Docker build target keeps runtime/language dependencies but does not bake Hugging Face model/voice assets. Start it with `task imagerun-tiny` or `task localrun-tiny` while online to populate the persistent cache volume.

API payload also supports explicit hardware selection with `device` (and keeps legacy `use_gpu` for compatibility).

## OpenAI-compatible Python client

Use the official OpenAI client with the local base URL:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:7860/v1", api_key="local")
audio = client.audio.speech.create(
    model="kokoro",
    input="Hello from Python.",
    voice="af_heart",
)
audio.write_to_file("hello.mp3")
```

The OpenAI-compatible route defaults to MP3 and supports `mp3`, `opus`, `aac`, `flac`, `wav`, and `pcm`.

## Native Python client

Use `KokoroTTSClient` when your Python code should call a running KokoroTTS server:

```python
from kokorotts import KokoroTTSClient

tts = KokoroTTSClient("http://localhost:7860")
tts.generate("Hello from Python.", voice="af_heart", output_format="mp3").save("hello.mp3")
```

Optional post-synthesis audio controls are available in the UI and API:

- `pitch_semitones`: `-12` to `12`, default `0`.
- `tempo`: `0.5` to `2.0`, default `1`.
- `volume`: `0` to `2.0`, default `1`.
- `normalize`: boolean, default `false`.

Neutral defaults skip the extra ffmpeg processing pass.
