ARG PYOPENJTALK_VERSION=0.4.1

FROM python:3.13-slim AS pyopenjtalk-wheel-builder

ARG PYOPENJTALK_VERSION

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip wheel \
    --no-cache-dir \
    --no-deps \
    --wheel-dir /wheels \
    "pyopenjtalk==${PYOPENJTALK_VERSION}"

FROM scratch AS pyopenjtalk-wheel

COPY --from=pyopenjtalk-wheel-builder /wheels/ /

FROM python:3.13-slim AS base

ARG PYOPENJTALK_VERSION

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

RUN python -m pip install --upgrade pip setuptools wheel

RUN --mount=type=bind,source=.build-cache/wheels,target=/tmp/wheel-cache,ro \
    wheel_count="$(find /tmp/wheel-cache -maxdepth 1 -type f -name 'pyopenjtalk-*.whl' | wc -l)" \
    && if [ "${wheel_count}" -gt 0 ]; then \
        python -m pip install --no-deps --no-index --find-links=/tmp/wheel-cache "pyopenjtalk==${PYOPENJTALK_VERSION}"; \
    else \
        python -m pip install --no-deps "pyopenjtalk==${PYOPENJTALK_VERSION}"; \
    fi

RUN python -m pip install --extra-index-url https://download.pytorch.org/whl/cu130 -r /app/requirements.txt \
    && python -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

FROM base AS language-builder

ARG UNIDIC_VERSION=3.1.0+2021-08-31
ARG UNIDIC_DOWNLOAD_URL=https://cotonoha-dic.s3-ap-northeast-1.amazonaws.com/unidic-3.1.0.zip
ARG UNIDIC_SHA256=638718c4c63625ab300de4c92c67925d54c0e9e3830009eaa992f29819d59c43

COPY scripts/install_unidic.py /tmp/install_unidic.py

RUN --mount=type=bind,source=.build-cache/unidic,target=/tmp/unidic-cache,ro \
    python /tmp/install_unidic.py \
        --version "${UNIDIC_VERSION}" \
        --url "${UNIDIC_DOWNLOAD_URL}" \
        --sha256 "${UNIDIC_SHA256}" \
        --archive /tmp/unidic-cache/unidic-3.1.0.zip \
    && rm /tmp/install_unidic.py

FROM language-builder AS app-builder

COPY pyproject.toml README.md LICENSE THIRD_PARTY_NOTICES.md VERSION /app/
COPY kokorotts /app/kokorotts
COPY assets/kokoro_favicon.webp assets/kokoro_logo_horizontal.webp assets/hangrylabs_logo_horizontal.webp /app/assets/

RUN mkdir -p /app/persistent/app /app/persistent/models/huggingface \
    && python -m pip install -e . --no-deps

FROM base AS asset-builder

COPY VERSION /app/VERSION
COPY kokorotts/__init__.py kokorotts/catalog.py kokorotts/client.py kokorotts/prefetch_assets.py /app/kokorotts/

RUN python -u -m kokorotts.prefetch_assets

FROM python:3.13-slim AS runtime-base

LABEL org.opencontainers.image.source="https://github.com/Hangry-Labs/kokoroTTS"

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

COPY --from=app-builder /usr/local /usr/local
COPY --from=app-builder /app /app
COPY --from=asset-builder /app/persistent /app/persistent
