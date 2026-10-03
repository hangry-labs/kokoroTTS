FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HF_HOME=/app/persistent/models/huggingface \
    KOKOROTTS_SETTINGS_PATH=/app/persistent/app/settings.json

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential espeak-ng ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --extra-index-url https://download.pytorch.org/whl/cu130 -r /app/requirements.txt \
    && python -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

FROM base AS language-builder

RUN python -m unidic download

FROM language-builder AS app-builder

COPY pyproject.toml README.md LICENSE VERSION /app/
COPY kokorotts /app/kokorotts
COPY assets/kokoro_favicon.webp assets/kokoro_logo_horizontal.webp assets/hangrylabs_logo_horizontal.webp /app/assets/

RUN mkdir -p /app/persistent/app /app/persistent/models/huggingface \
    && python -m pip install -e . --no-deps

FROM app-builder AS baked-builder

RUN python -u /app/kokorotts/prefetch_assets.py

FROM python:3.13-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HF_HOME=/app/persistent/models/huggingface \
    KOKOROTTS_SETTINGS_PATH=/app/persistent/app/settings.json \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    KOKOROTTS_DEVICE=auto \
    PORT=7860 \
    HOST=0.0.0.0 \
    UVICORN_RELOAD=0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng ffmpeg \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 7860

CMD ["python", "-u", "-m", "kokorotts.server"]

FROM runtime-base AS tiny

ENV HF_HUB_OFFLINE=0 \
    TRANSFORMERS_OFFLINE=0

COPY --from=app-builder /usr/local /usr/local
COPY --from=app-builder /app /app

FROM runtime-base AS baked

COPY --from=baked-builder /usr/local /usr/local
COPY --from=baked-builder /app /app
