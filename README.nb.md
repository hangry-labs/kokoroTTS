<p align="center">
  <a href="https://github.com/Hangry-Labs/kokoroTTS">
    <img src="assets/kokoro_logo_horizontal.webp" alt="Hangry Labs KokoroTTS-logo" width="900">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <strong>Norsk bokmål</strong> ·
  <a href="README.pl.md">Polski</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.zh.md">简体中文</a> ·
  <a href="README.es.md">Español</a>
</p>

# Hangry Labs KokoroTTS

Docker-først tekst-til-tale med et lokalt nettlesergrensesnitt, strømming og OpenAI-kompatibelt API.

Denne Hangry Labs-versjonen er laget for enkel lokal inferens. Start én container, åpne grensesnittet eller kall API-et og lag tale uten å sette opp Python, modeller eller lydverktøy manuelt.

## Dette får du

- Lokalt nettlesergrensesnitt for generering, strømming, avspilling og nedlasting
- OpenAI-kompatibelt endepunkt: `/v1/audio/speech`
- KokoroTTS-API med stemmekontroller, SSML, tokeninspeksjon og modellstyring
- Valgfri MCP-integrasjon for KI-agenter med utløpende lydlenker og styring av modellpakker
- 173 stemmer på 11 språk, inkludert egne tyske, vietnamesiske og forbedrede kinesiske modeller
- WAV, MP3, FLAC, OGG Vorbis, Opus, AAC og rå PCM
- Vedvarende modellvalg, modellbuffer og GPU-overvåking
- Komplett Docker-bilde for bruk uten nett etter nedlasting
- Lite Docker-bilde som laster ned valgte modeller til et vedvarende volum

## Hurtigstart

Kjør det komplette bildet med en NVIDIA-GPU:

```bash
docker run --name kokorotts --restart unless-stopped -p 7860:7860 --gpus all -e CUDA_VISIBLE_DEVICES=0 -v kokorotts_data:/app/persistent hangrylabs/kokorotts:latest
```

Kommandoen står på én linje og kan limes direkte inn i Bash, PowerShell eller Windows Ledetekst. Docker oppretter det navngitte volumet automatisk.

Åpne deretter:

- Nettlesergrensesnitt: [http://localhost:7860](http://localhost:7860)
- API-dokumentasjon: [http://localhost:7860/tts/docs](http://localhost:7860/tts/docs)

Det komplette `latest`-bildet inkluderer modellene og kan brukes uten nett etter at bildet er lastet ned.

## Mer informasjon

Les den [komplette norske produkt- og installasjonsveiledningen](https://hangrylabs.app/nb/software/kokorotts). Den fullstendige tekniske referansen vedlikeholdes i den [engelske README-filen](README.md).
