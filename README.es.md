<p align="center">
  <a href="https://github.com/Hangry-Labs/kokoroTTS">
    <img src="assets/kokoro_logo_horizontal.webp" alt="Logotipo de Hangry Labs KokoroTTS" width="900">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.nb.md">Norsk bokmål</a> ·
  <a href="README.pl.md">Polski</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.zh.md">简体中文</a> ·
  <strong>Español</strong>
</p>

# Hangry Labs KokoroTTS

Texto a voz preparado para Docker, con interfaz web local, generación por streaming y una API compatible con OpenAI.

Esta versión de Hangry Labs está diseñada para una inferencia local sencilla. Inicia un contenedor, abre la interfaz o llama a la API y genera voz sin configurar Python, modelos ni herramientas de audio manualmente.

## Qué ofrece el proyecto

- Interfaz web local para generar, transmitir, reproducir y descargar audio
- Endpoint `/v1/audio/speech` compatible con OpenAI
- API nativa de KokoroTTS con controles de voz, SSML, inspección de tokens y gestión de modelos
- Integración MCP opcional para agentes de IA con enlaces de audio temporales y gestión de paquetes de modelos
- 173 voces en 11 idiomas, con modelos dedicados de alemán, vietnamita y chino mejorado
- Salida WAV, MP3, FLAC, OGG Vorbis, Opus, AAC y PCM sin procesar
- Selección persistente de modelos, caché de modelos y supervisión de la GPU
- Imagen Docker completa que funciona sin conexión después de descargarla
- Imagen Docker reducida que descarga los modelos seleccionados en un volumen persistente

## Inicio rápido

Ejecuta la imagen completa con una GPU NVIDIA:

```bash
docker run --name kokorotts --restart unless-stopped -p 7860:7860 --gpus all -e CUDA_VISIBLE_DEVICES=0 -v kokorotts_data:/app/persistent hangrylabs/kokorotts:latest
```

El comando está en una sola línea y se puede pegar directamente en Bash, PowerShell o el Símbolo del sistema de Windows. Docker crea automáticamente el volumen con nombre.

Después, abre:

- Interfaz web: [http://localhost:7860](http://localhost:7860)
- Documentación de la API: [http://localhost:7860/tts/docs](http://localhost:7860/tts/docs)

La imagen completa `latest` incluye los modelos y puede utilizarse sin conexión después de descargarla.

## Más información

Consulta la [página completa del producto y la guía de instalación en español](https://hangrylabs.app/es/software/kokorotts). La referencia técnica completa se mantiene en el [README en inglés](README.md).
