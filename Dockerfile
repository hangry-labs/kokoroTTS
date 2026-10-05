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
ARG OPEN_JTALK_DICT_VERSION=1.11
ARG OPEN_JTALK_DICT_URL=https://github.com/r9y9/open_jtalk/releases/download/v1.11.1/open_jtalk_dic_utf_8-1.11.tar.gz
ARG OPEN_JTALK_DICT_SHA256=fe6ba0e43542cef98339abdffd903e062008ea170b04e7e2a35da805902f382a

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

COPY scripts/install_open_jtalk_dictionary.py /tmp/install_open_jtalk_dictionary.py

RUN python /tmp/install_open_jtalk_dictionary.py \
        --version "${OPEN_JTALK_DICT_VERSION}" \
        --url "${OPEN_JTALK_DICT_URL}" \
        --sha256 "${OPEN_JTALK_DICT_SHA256}" \
    && rm /tmp/install_open_jtalk_dictionary.py

COPY third_party/README.md /app/third_party/README.md
COPY Dockerfile requirements.in requirements.txt pyproject.toml /app/third_party/build/
COPY scripts/install_compliance_sources.py scripts/install_open_jtalk_dictionary.py scripts/verify_compliance_bundle.py /app/third_party/build/

RUN python /app/third_party/build/install_compliance_sources.py \
        --output /app/third_party \
    && python /app/third_party/build/verify_compliance_bundle.py \
        /app/third_party

FROM base AS app-builder

COPY pyproject.toml README.md LICENSE THIRD_PARTY_NOTICES.md VERSION /app/
COPY kokorotts /app/kokorotts
COPY assets/kokoro_favicon.webp assets/kokoro_logo_horizontal.webp assets/hangrylabs_logo.webp /app/assets/

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
    KOKOROTTS_ENABLE_MCP=0 \
    KOKOROTTS_MCP_OUTPUT_DIR=/app/persistent/mcp-output \
    KOKOROTTS_MCP_DNS_REBINDING_PROTECTION=1 \
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

ARG BUILD_DATE=unknown
ARG VCS_REF=unknown

LABEL org.opencontainers.image.created="${BUILD_DATE}" \
    org.opencontainers.image.revision="${VCS_REF}"

ENV KOKOROTTS_BUILD_DATE="${BUILD_DATE}" \
    KOKOROTTS_VCS_REF="${VCS_REF}" \
    BUILD_ID="${BUILD_DATE}@${VCS_REF}"

EXPOSE 7860

CMD ["python", "-u", "-m", "kokorotts.server"]

FROM runtime-base AS runtime-app

COPY --from=app-builder /usr/local /usr/local
COPY --from=app-builder /app /app

RUN python /app/third_party/build/verify_compliance_bundle.py \
        /app/third_party

FROM runtime-app AS tiny

ENV HF_HUB_OFFLINE=0 \
    TRANSFORMERS_OFFLINE=0

FROM runtime-app AS baked

COPY --from=asset-builder /app/persistent /app/persistent
