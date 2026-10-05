<p align="center">
  <a href="https://github.com/Hangry-Labs/kokoroTTS">
    <img src="assets/kokoro_logo_horizontal.webp" alt="Hangry Labs KokoroTTS 标志" width="900">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.nb.md">Norsk bokmål</a> ·
  <a href="README.pl.md">Polski</a> ·
  <a href="README.ja.md">日本語</a> ·
  <strong>简体中文</strong> ·
  <a href="README.es.md">Español</a>
</p>

# Hangry Labs KokoroTTS

以 Docker 为优先的文本转语音服务，包含本地浏览器界面、流式生成和 OpenAI 兼容 API。

这个 Hangry Labs 版本专为简单的本地推理而设计。只需启动一个容器，即可通过界面或 API 生成语音，无需手动配置 Python、模型或音频工具。

## 项目功能

- 用于生成、流式处理、播放和下载音频的本地浏览器界面
- OpenAI 兼容端点 `/v1/audio/speech`
- 支持语音控制、SSML、Token 检查和模型管理的 KokoroTTS 原生 API
- 11 种语言、173 个音色，包括专用德语、越南语和增强中文模型
- 支持 WAV、MP3、FLAC、OGG Vorbis、Opus、AAC 和原始 PCM
- 持久化模型设置、模型缓存和 GPU 监控
- 下载后可离线运行的完整 Docker 镜像
- 将选定模型下载到持久卷的小型 Docker 镜像

## 快速开始

使用 NVIDIA GPU 运行完整镜像：

```bash
docker run --name kokorotts --restart unless-stopped -p 7860:7860 --gpus all -e CUDA_VISIBLE_DEVICES=0 -v kokorotts_data:/app/persistent hangrylabs/kokorotts:latest
```

该命令只有一行，可直接粘贴到 Bash、PowerShell 或 Windows 命令提示符。Docker 会自动创建命名卷。

然后打开：

- 浏览器界面：[http://localhost:7860](http://localhost:7860)
- API 文档：[http://localhost:7860/tts/docs](http://localhost:7860/tts/docs)

完整的 `latest` 镜像已包含模型，下载镜像后即可离线使用。

## 更多信息

请查看[完整的中文产品介绍和安装指南](https://hangrylabs.app/zh/software/kokorotts)。完整技术参考仍在[英文 README](README.md)中维护。
