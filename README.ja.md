<p align="center">
  <a href="https://github.com/Hangry-Labs/kokoroTTS">
    <img src="assets/kokoro_logo_horizontal.webp" alt="Hangry Labs KokoroTTS ロゴ" width="900">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.nb.md">Norsk bokmål</a> ·
  <a href="README.pl.md">Polski</a> ·
  <strong>日本語</strong> ·
  <a href="README.zh.md">简体中文</a> ·
  <a href="README.es.md">Español</a>
</p>

# Hangry Labs KokoroTTS

ローカルのブラウザー UI、ストリーミング、OpenAI 互換 API を備えた Docker ファーストのテキスト読み上げ環境です。

この Hangry Labs 版は、ローカル推論を簡単に使うためのものです。コンテナーを 1 つ起動し、UI または API から、Python・モデル・音声ツールを手動設定せずに音声を生成できます。

## 主な機能

- 生成、ストリーミング、再生、ダウンロードに対応したローカル UI
- OpenAI 互換の `/v1/audio/speech` エンドポイント
- 音声調整、SSML、トークン確認、モデル管理に対応した KokoroTTS ネイティブ API
- 有効期限付き音声リンクとモデルパック管理を提供する、AIエージェント向けのオプションMCP連携
- 専用のドイツ語・ベトナム語・強化中国語モデルを含む、11 言語 173 音声
- WAV、MP3、FLAC、OGG Vorbis、Opus、AAC、raw PCM 出力
- 永続的なモデル設定、モデルキャッシュ、GPU モニター
- ダウンロード後はオフラインで動作する完全版 Docker イメージ
- 選択したモデルを永続ボリュームへダウンロードする小型 Docker イメージ

## クイックスタート

NVIDIA GPU で完全版イメージを実行します。

```bash
docker run --name kokorotts --restart unless-stopped -p 7860:7860 --gpus all -e CUDA_VISIBLE_DEVICES=0 -v kokorotts_data:/app/persistent hangrylabs/kokorotts:latest
```

コマンドは 1 行で、Bash、PowerShell、Windows コマンドプロンプトへそのまま貼り付けられます。名前付きボリュームは Docker が自動作成します。

起動後に開きます。

- ブラウザー UI: [http://localhost:7860](http://localhost:7860)
- API ドキュメント: [http://localhost:7860/tts/docs](http://localhost:7860/tts/docs)

完全版の `latest` イメージにはモデルが含まれ、イメージの取得後はオフラインで利用できます。

## 詳細情報

[日本語の製品説明とインストールガイド](https://hangrylabs.app/ja/software/kokorotts)をご覧ください。完全な技術リファレンスは[英語版 README](README.md)で管理しています。
