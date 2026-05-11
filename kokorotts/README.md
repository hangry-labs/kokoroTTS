# kokorotts

Python UI + API application for Kokoro TTS.

The app exposes the bundled Kokoro-82M voice set across American English, British English, Japanese, Mandarin, Spanish, French, Hindi, Italian, and Brazilian Portuguese.

## Run without Docker

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
python kokorotts/app.py
```

- UI: `http://localhost:7860/`
- API ping: `GET /tts/ping`
- API synthesis: `POST /tts/generate`
- Backward-compatible API synthesis alias: `POST /tts/convert`

## Docker and Task workflow

From repository root:

```bash
task deps
task image
task imagerun
task imageweb
task imageapi
```

`task deps` regenerates the pinned root `requirements.txt` from `requirements.in` for the Docker/Linux runtime.

For hot-swapping local app files into the running container:

```bash
task localrun
task logs
task client-test
```

`localrun` mounts the full local `kokorotts/` directory into `/app/kokorotts` and enables auto-reload via `UVICORN_RELOAD=1`.

Optional runtime env vars:

- `HF_TOKEN`: Hugging Face access token for higher hub rate limits.
- `KOKORO_REPO_ID`: override model repo (default `hexgrad/Kokoro-82M`).
- `KOKOROTTS_DEVICE`: default hardware (`auto`, `cpu`, `cuda:0`, ...).

## Model and offline mode

- Default repo is `hexgrad/Kokoro-82M`.
- For this repo, `kokorotts/model.py` resolves weights to `kokoro-v1_0.pth` (Kokoro v1.0).
- Docker build runs `kokorotts/prefetch_assets.py` to cache model/config + UI voice packs into the image.
- Runtime sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, so serving works without internet.

API payload also supports explicit hardware selection with `device` (and keeps legacy `use_gpu` for compatibility).

## Python API client

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
