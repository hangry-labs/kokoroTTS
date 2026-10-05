<p align="center">
  <a href="https://github.com/Hangry-Labs/kokoroTTS">
    <img src="assets/kokoro_logo_horizontal.webp" alt="Logo Hangry Labs KokoroTTS" width="900">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.nb.md">Norsk bokmål</a> ·
  <strong>Polski</strong> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.zh.md">简体中文</a> ·
  <a href="README.es.md">Español</a>
</p>

# Hangry Labs KokoroTTS

Gotowy do uruchomienia w Dockerze system zamiany tekstu na mowę z lokalnym interfejsem, strumieniowaniem i API zgodnym z OpenAI.

Ta wersja Hangry Labs jest przeznaczona do prostej lokalnej inferencji. Uruchom jeden kontener, otwórz interfejs lub wywołaj API i generuj mowę bez ręcznej konfiguracji Pythona, modeli ani narzędzi audio.

## Co oferuje projekt

- Lokalny interfejs do generowania, strumieniowania, odtwarzania i pobierania dźwięku
- Endpoint `/v1/audio/speech` zgodny z OpenAI
- Natywne API KokoroTTS ze sterowaniem głosem, SSML, podglądem tokenów i zarządzaniem modelami
- Opcjonalna integracja MCP dla agentów AI z wygasającymi linkami audio i zarządzaniem pakietami modeli
- 173 głosy w 11 językach, w tym dedykowane modele niemieckie, wietnamskie i ulepszone chińskie
- Format WAV, MP3, FLAC, OGG Vorbis, Opus, AAC oraz surowy PCM
- Trwałe ustawienia modeli, pamięć modeli i monitorowanie GPU
- Pełny obraz Docker działający offline po pobraniu
- Mniejszy obraz Docker pobierający wybrane modele do trwałego woluminu

## Szybki start

Uruchom pełny obraz na karcie NVIDIA:

```bash
docker run --name kokorotts --restart unless-stopped -p 7860:7860 --gpus all -e CUDA_VISIBLE_DEVICES=0 -v kokorotts_data:/app/persistent hangrylabs/kokorotts:latest
```

Polecenie jest zapisane w jednej linii i można je wkleić bezpośrednio do Bash, PowerShell lub Wiersza polecenia Windows. Docker automatycznie utworzy nazwany wolumin.

Następnie otwórz:

- Interfejs: [http://localhost:7860](http://localhost:7860)
- Dokumentacja API: [http://localhost:7860/tts/docs](http://localhost:7860/tts/docs)

Pełny obraz `latest` zawiera modele i po pobraniu może działać offline.

## Więcej informacji

Przeczytaj [pełny polski opis produktu i instrukcję instalacji](https://hangrylabs.app/pl/software/kokorotts). Pełna dokumentacja techniczna jest utrzymywana w [angielskim README](README.md).
