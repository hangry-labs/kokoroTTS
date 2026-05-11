const PAGE_LANGUAGES = {
  en: "American English",
  ja: "Japanese",
  zh: "Mandarin Chinese",
  es: "Spanish",
  fr: "French",
  hi: "Hindi",
  it: "Italian",
  pt: "Brazilian Portuguese",
};

const PAGE_LANGUAGE_BY_VOICE_LANGUAGE = Object.fromEntries(
  Object.entries(PAGE_LANGUAGES).map(([pageLanguage, voiceLanguage]) => [voiceLanguage, pageLanguage]),
);

const LANGUAGE_LABELS = {
  en: {
    "American English": "American English",
    "British English": "British English",
    Japanese: "Japanese",
    "Mandarin Chinese": "Mandarin Chinese",
    Spanish: "Spanish",
    French: "French",
    Hindi: "Hindi",
    Italian: "Italian",
    "Brazilian Portuguese": "Brazilian Portuguese",
  },
  ja: {
    "American English": "アメリカ英語",
    "British English": "イギリス英語",
    Japanese: "日本語",
    "Mandarin Chinese": "中国語",
    Spanish: "スペイン語",
    French: "フランス語",
    Hindi: "ヒンディー語",
    Italian: "イタリア語",
    "Brazilian Portuguese": "ブラジルポルトガル語",
  },
  zh: {
    "American English": "美式英语",
    "British English": "英式英语",
    Japanese: "日语",
    "Mandarin Chinese": "中文",
    Spanish: "西班牙语",
    French: "法语",
    Hindi: "印地语",
    Italian: "意大利语",
    "Brazilian Portuguese": "巴西葡萄牙语",
  },
  es: {
    "American English": "Inglés estadounidense",
    "British English": "Inglés británico",
    Japanese: "Japonés",
    "Mandarin Chinese": "Chino mandarín",
    Spanish: "Español",
    French: "Francés",
    Hindi: "Hindi",
    Italian: "Italiano",
    "Brazilian Portuguese": "Portugués de Brasil",
  },
  fr: {
    "American English": "Anglais américain",
    "British English": "Anglais britannique",
    Japanese: "Japonais",
    "Mandarin Chinese": "Chinois mandarin",
    Spanish: "Espagnol",
    French: "Français",
    Hindi: "Hindi",
    Italian: "Italien",
    "Brazilian Portuguese": "Portugais du Brésil",
  },
  hi: {
    "American English": "अमेरिकी अंग्रेज़ी",
    "British English": "ब्रिटिश अंग्रेज़ी",
    Japanese: "जापानी",
    "Mandarin Chinese": "चीनी",
    Spanish: "स्पेनिश",
    French: "फ़्रेंच",
    Hindi: "हिन्दी",
    Italian: "इतालवी",
    "Brazilian Portuguese": "ब्राज़ीलियाई पुर्तगाली",
  },
  it: {
    "American English": "Inglese americano",
    "British English": "Inglese britannico",
    Japanese: "Giapponese",
    "Mandarin Chinese": "Cinese mandarino",
    Spanish: "Spagnolo",
    French: "Francese",
    Hindi: "Hindi",
    Italian: "Italiano",
    "Brazilian Portuguese": "Portoghese brasiliano",
  },
  pt: {
    "American English": "Inglês americano",
    "British English": "Inglês britânico",
    Japanese: "Japonês",
    "Mandarin Chinese": "Chinês mandarim",
    Spanish: "Espanhol",
    French: "Francês",
    Hindi: "Hindi",
    Italian: "Italiano",
    "Brazilian Portuguese": "Português do Brasil",
  },
};

const TRANSLATIONS = {
  en: {
    title: "Hangry Labs KokoroTTS Voice Examples",
    dockerHub: "Docker Hub",
    brandSubtitle: "Useful tools, easy to run",
    headline: "KokoroTTS voice examples",
    intro: "Easy-to-run text-to-speech Docker images built for professionals and for people who are not technical. Install Docker, run one command, open the browser, or call the same API from your own application. KokoroTTS creates compact MP3 audio, exposes the full Kokoro voice set, and works out of the box.",
    pillVoices: "54 voices",
    pillLanguages: "9 language prefixes",
    pillApi: "UI + API",
    pillOffline: "Offline-friendly Docker image",
    filterAll: "All",
    voiceFilterLabel: "Filter voice examples by language",
    voiceExamplesLabel: "Voice examples",
    playPrefix: "Play",
    pausePrefix: "Pause",
    seekSample: "Seek sample",
  },
  ja: {
    title: "Hangry Labs KokoroTTS 音声サンプル",
    dockerHub: "Docker Hub",
    brandSubtitle: "便利なツールを、簡単に",
    headline: "KokoroTTS 音声サンプル",
    intro: "専門家にも、技術に詳しくない人にも使いやすい、Docker で動くテキスト読み上げです。Docker を入れて、コマンドを一つ実行し、ブラウザーを開くだけです。内蔵 UI から使うことも、自分のアプリケーションから同じ API を呼び出すこともできます。KokoroTTS はコンパクトな MP3 音声を作成し、すぐに使えます。",
    pillVoices: "54 種類の音声",
    pillLanguages: "9 つの言語プレフィックス",
    pillApi: "UI + API",
    pillOffline: "オフライン向け Docker イメージ",
    filterAll: "すべて",
    voiceFilterLabel: "言語で音声サンプルを絞り込む",
    voiceExamplesLabel: "音声サンプル",
    playPrefix: "再生",
    pausePrefix: "一時停止",
    seekSample: "サンプルをシーク",
  },
  zh: {
    title: "Hangry Labs KokoroTTS 声音示例",
    dockerHub: "Docker Hub",
    brandSubtitle: "实用工具，轻松运行",
    headline: "KokoroTTS 声音示例",
    intro: "易于运行的文本转语音 Docker 镜像，适合专业人员，也适合不太懂技术的用户。安装 Docker，运行一个命令，打开浏览器，或从自己的应用程序调用同一个 API。KokoroTTS 可以生成体积较小的 MP3 音频，提供完整的 Kokoro 声音集，并且开箱即用。",
    pillVoices: "54 个声音",
    pillLanguages: "9 个语言前缀",
    pillApi: "界面 + API",
    pillOffline: "离线友好的 Docker 镜像",
    filterAll: "全部",
    voiceFilterLabel: "按语言筛选声音示例",
    voiceExamplesLabel: "声音示例",
    playPrefix: "播放",
    pausePrefix: "暂停",
    seekSample: "跳转示例音频",
  },
  es: {
    title: "Ejemplos de voz de Hangry Labs KokoroTTS",
    dockerHub: "Docker Hub",
    brandSubtitle: "Herramientas útiles, fáciles de ejecutar",
    headline: "Ejemplos de voz de KokoroTTS",
    intro: "Imágenes Docker de texto a voz fáciles de ejecutar, hechas para profesionales y para personas que no son técnicas. Instala Docker, ejecuta un comando, abre el navegador o llama a la misma API desde tu propia aplicación. KokoroTTS crea audio MP3 compacto, expone todo el conjunto de voces de Kokoro y funciona desde el primer momento.",
    pillVoices: "54 voces",
    pillLanguages: "9 prefijos de idioma",
    pillApi: "UI + API",
    pillOffline: "Imagen Docker apta para uso offline",
    filterAll: "Todo",
    voiceFilterLabel: "Filtrar ejemplos de voz por idioma",
    voiceExamplesLabel: "Ejemplos de voz",
    playPrefix: "Reproducir",
    pausePrefix: "Pausar",
    seekSample: "Buscar en la muestra",
  },
  fr: {
    title: "Exemples de voix Hangry Labs KokoroTTS",
    dockerHub: "Docker Hub",
    brandSubtitle: "Des outils utiles, faciles à lancer",
    headline: "Exemples de voix KokoroTTS",
    intro: "Des images Docker de texte vers parole faciles à lancer, faites pour les professionnels et pour les personnes qui ne sont pas techniques. Installez Docker, lancez une commande, ouvrez le navigateur ou appelez la même API depuis votre application. KokoroTTS crée un audio MP3 compact, expose tout l'ensemble de voix Kokoro et fonctionne immédiatement.",
    pillVoices: "54 voix",
    pillLanguages: "9 préfixes de langue",
    pillApi: "UI + API",
    pillOffline: "Image Docker adaptée au mode hors ligne",
    filterAll: "Tout",
    voiceFilterLabel: "Filtrer les exemples de voix par langue",
    voiceExamplesLabel: "Exemples de voix",
    playPrefix: "Lire",
    pausePrefix: "Mettre en pause",
    seekSample: "Parcourir l'extrait",
  },
  hi: {
    title: "Hangry Labs KokoroTTS आवाज़ उदाहरण",
    dockerHub: "Docker Hub",
    brandSubtitle: "उपयोगी टूल, चलाने में आसान",
    headline: "KokoroTTS आवाज़ उदाहरण",
    intro: "चलाने में आसान टेक्स्ट टू स्पीच Docker इमेज, पेशेवरों और गैर-तकनीकी लोगों दोनों के लिए। Docker इंस्टॉल करें, एक कमांड चलाएँ, ब्राउज़र खोलें, या अपने एप्लिकेशन से वही API कॉल करें। KokoroTTS छोटा MP3 ऑडियो बनाता है, पूरा Kokoro voice set उपलब्ध कराता है, और तुरंत काम करता है।",
    pillVoices: "54 आवाज़ें",
    pillLanguages: "9 भाषा प्रीफ़िक्स",
    pillApi: "UI + API",
    pillOffline: "ऑफ़लाइन-फ्रेंडली Docker इमेज",
    filterAll: "सभी",
    voiceFilterLabel: "भाषा के अनुसार आवाज़ उदाहरण फ़िल्टर करें",
    voiceExamplesLabel: "आवाज़ उदाहरण",
    playPrefix: "चलाएँ",
    pausePrefix: "रोकें",
    seekSample: "नमूना खोजें",
  },
  it: {
    title: "Esempi di voce Hangry Labs KokoroTTS",
    dockerHub: "Docker Hub",
    brandSubtitle: "Strumenti utili, facili da eseguire",
    headline: "Esempi di voce KokoroTTS",
    intro: "Immagini Docker per text to speech facili da eseguire, pensate per professionisti e per persone non tecniche. Installa Docker, esegui un comando, apri il browser oppure chiama la stessa API dalla tua applicazione. KokoroTTS crea audio MP3 compatto, espone l'intero set di voci Kokoro e funziona subito.",
    pillVoices: "54 voci",
    pillLanguages: "9 prefissi lingua",
    pillApi: "UI + API",
    pillOffline: "Immagine Docker adatta all'uso offline",
    filterAll: "Tutto",
    voiceFilterLabel: "Filtra gli esempi di voce per lingua",
    voiceExamplesLabel: "Esempi di voce",
    playPrefix: "Riproduci",
    pausePrefix: "Pausa",
    seekSample: "Scorri il campione",
  },
  pt: {
    title: "Exemplos de voz do Hangry Labs KokoroTTS",
    dockerHub: "Docker Hub",
    brandSubtitle: "Ferramentas úteis, fáceis de executar",
    headline: "Exemplos de voz do KokoroTTS",
    intro: "Imagens Docker de text to speech fáceis de executar, feitas para profissionais e para pessoas que não são técnicas. Instale o Docker, execute um comando, abra o navegador ou chame a mesma API a partir da sua aplicação. O KokoroTTS cria áudio MP3 compacto, expõe todo o conjunto de vozes Kokoro e funciona direto.",
    pillVoices: "54 vozes",
    pillLanguages: "9 prefixos de idioma",
    pillApi: "UI + API",
    pillOffline: "Imagem Docker amigável para uso offline",
    filterAll: "Todos",
    voiceFilterLabel: "Filtrar exemplos de voz por idioma",
    voiceExamplesLabel: "Exemplos de voz",
    playPrefix: "Reproduzir",
    pausePrefix: "Pausar",
    seekSample: "Navegar no exemplo",
  },
};

let currentPageLanguage = "en";

function renderVoiceExamples() {
  const grid = document.querySelector("[data-voice-grid]");
  if (!grid || !Array.isArray(window.VOICE_EXAMPLES)) {
    return;
  }

  grid.innerHTML = window.VOICE_EXAMPLES.map((voice) => `
    <article class="brand-card p-5" data-language="${voice.language}">
      <div class="mb-4 flex items-start justify-between gap-3 border-b border-orange-500/20 pb-3">
        <div>
          <h2 class="text-lg font-bold text-orange-400">${voice.name}</h2>
          <p class="mt-1 text-sm text-[#ffb076]/80" data-card-language>${voice.language}</p>
        </div>
        <span class="rounded-full border border-orange-500/30 bg-orange-500/10 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-gray-300">${voice.voice}</span>
      </div>
      <audio preload="metadata" src="${voice.file}"></audio>
    </article>
  `).join("");
}

renderVoiceExamples();

const players = Array.from(document.querySelectorAll(".brand-card audio"));
const cards = Array.from(document.querySelectorAll(".brand-card"));
const filterButtons = Array.from(document.querySelectorAll("[data-language-value]"));
const volumeButton = document.querySelector(".volume-button");
const volumeSlider = document.querySelector(".volume-slider");
const volumeIconOn = document.querySelector(".volume-icon-on");
const volumeIconMuted = document.querySelector(".volume-icon-muted");
let currentVolume = Number.parseFloat(volumeSlider?.value || "0.85");
let lastVolume = currentVolume > 0 ? currentVolume : 0.85;

function formatTime(value) {
  if (!Number.isFinite(value)) {
    return "0:00";
  }

  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function pauseOthers(currentAudio) {
  players.forEach((audio) => {
    if (audio !== currentAudio) {
      audio.pause();
    }
  });
}

function pauseAll() {
  players.forEach((audio) => {
    audio.pause();
  });
}

function setLanguageFilter(language) {
  pauseAll();
  translatePage(PAGE_LANGUAGE_BY_VOICE_LANGUAGE[language] || "en");

  filterButtons.forEach((button) => {
    const isActive = button.dataset.languageValue === language;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", isActive.toString());
  });

  cards.forEach((card) => {
    const isVisible = language === "all" || card.dataset.language === language;
    card.hidden = !isVisible;
  });
}

function translatePage(languageCode) {
  currentPageLanguage = TRANSLATIONS[languageCode] ? languageCode : "en";
  const translation = TRANSLATIONS[currentPageLanguage];
  document.documentElement.lang = currentPageLanguage;
  document.title = translation.title;

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    if (translation[key]) {
      element.textContent = translation[key];
    }
  });

  document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
    const key = element.dataset.i18nAria;
    if (translation[key]) {
      element.setAttribute("aria-label", translation[key]);
    }
  });

  cards.forEach((card) => {
    const label = card.querySelector("[data-card-language]");
    if (label) {
      label.textContent = LANGUAGE_LABELS[currentPageLanguage][card.dataset.language] || card.dataset.language;
    }
    const heading = card.querySelector("h2")?.textContent || "voice sample";
    const audio = card.querySelector("audio");
    card.setAttribute("aria-label", `${audio?.paused === false ? translation.pausePrefix : translation.playPrefix} ${heading}`);
  });

  document.querySelectorAll(".progress-button").forEach((button) => {
    button.setAttribute("aria-label", translation.seekSample);
  });
}

function updateVolumeControl() {
  const isMuted = currentVolume <= 0.001;

  players.forEach((audio) => {
    audio.volume = currentVolume;
    audio.muted = isMuted;
  });

  if (volumeSlider) {
    volumeSlider.value = currentVolume.toString();
  }

  if (volumeButton) {
    volumeButton.dataset.muted = isMuted.toString();
    volumeButton.setAttribute("aria-label", isMuted ? "Unmute audio" : "Mute audio");
  }

  if (volumeIconOn && volumeIconMuted) {
    volumeIconOn.hidden = isMuted;
    volumeIconMuted.hidden = !isMuted;
    volumeIconOn.style.display = isMuted ? "none" : "block";
    volumeIconMuted.style.display = isMuted ? "block" : "none";
  }
}

if (volumeSlider) {
  volumeSlider.addEventListener("input", () => {
    currentVolume = Number.parseFloat(volumeSlider.value);

    if (currentVolume > 0) {
      lastVolume = currentVolume;
    }

    updateVolumeControl();
  });
}

if (volumeButton) {
  volumeButton.addEventListener("click", () => {
    if (currentVolume > 0) {
      lastVolume = currentVolume;
      currentVolume = 0;
    } else {
      currentVolume = lastVolume || 0.85;
    }

    updateVolumeControl();
  });
}

filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setLanguageFilter(button.dataset.languageValue || "all");
  });
});

players.forEach((audio) => {
  const card = audio.closest(".brand-card");

  audio.volume = currentVolume;
  audio.removeAttribute("controls");
  if (audio.nextElementSibling && audio.nextElementSibling.classList.contains("player")) {
    return;
  }

  const controls = document.createElement("div");
  controls.className = "player";
  controls.innerHTML = `
    <button class="progress-button" type="button" aria-label="${TRANSLATIONS[currentPageLanguage].seekSample}">
      <span class="progress-track" aria-hidden="true">
        <span class="progress-fill"></span>
        <span class="progress-knob"></span>
      </span>
    </button>
    <span class="duration">0:00</span>
  `;

  audio.insertAdjacentElement("afterend", controls);

  const progressButton = controls.querySelector(".progress-button");
  const progressFill = controls.querySelector(".progress-fill");
  const progressKnob = controls.querySelector(".progress-knob");
  const duration = controls.querySelector(".duration");

  function setProgress(value) {
    const progress = Math.max(0, Math.min(100, value));
    progressFill.style.width = `${progress}%`;
    progressKnob.style.left = `${progress}%`;
  }

  function seekToPosition(event) {
    if (Number.isFinite(audio.duration)) {
      const rect = progressButton.getBoundingClientRect();
      const position = (event.clientX - rect.left) / rect.width;
      const progress = Math.max(0, Math.min(1, position));
      audio.currentTime = progress * audio.duration;
      setProgress(progress * 100);
    }
  }

  function togglePlayback() {
    if (audio.paused) {
      pauseOthers(audio);
      audio.play();
    } else {
      audio.pause();
    }
  }

  if (card) {
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");
    card.setAttribute("aria-label", `${TRANSLATIONS[currentPageLanguage].playPrefix} ${card.querySelector("h2")?.textContent || "voice sample"}`);

    card.addEventListener("click", togglePlayback);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        togglePlayback();
      }
    });
  }

  progressButton.addEventListener("click", (event) => {
    event.stopPropagation();
    seekToPosition(event);
  });

  progressButton.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    event.stopPropagation();
    progressButton.setPointerCapture(event.pointerId);
    seekToPosition(event);
  });

  progressButton.addEventListener("pointermove", (event) => {
    if (progressButton.hasPointerCapture(event.pointerId)) {
      event.preventDefault();
      event.stopPropagation();
      seekToPosition(event);
    }
  });

  progressButton.addEventListener("pointerup", (event) => {
    event.preventDefault();
    event.stopPropagation();

    if (progressButton.hasPointerCapture(event.pointerId)) {
      progressButton.releasePointerCapture(event.pointerId);
    }
  });

  progressButton.addEventListener("pointercancel", (event) => {
    if (progressButton.hasPointerCapture(event.pointerId)) {
      progressButton.releasePointerCapture(event.pointerId);
    }
  });

  audio.addEventListener("loadedmetadata", () => {
    duration.textContent = `0:00 / ${formatTime(audio.duration)}`;
  });

  audio.addEventListener("timeupdate", () => {
    if (Number.isFinite(audio.duration) && audio.duration > 0) {
      setProgress((audio.currentTime / audio.duration) * 100);
      duration.textContent = `${formatTime(audio.currentTime)} / ${formatTime(audio.duration)}`;
    }
  });

  audio.addEventListener("play", () => {
    if (card) {
      card.classList.add("is-playing");
      card.setAttribute("aria-label", `${TRANSLATIONS[currentPageLanguage].pausePrefix} ${card.querySelector("h2")?.textContent || "voice sample"}`);
    }
  });

  audio.addEventListener("pause", () => {
    if (card) {
      card.classList.remove("is-playing");
      card.setAttribute("aria-label", `${TRANSLATIONS[currentPageLanguage].playPrefix} ${card.querySelector("h2")?.textContent || "voice sample"}`);
    }
  });

  audio.addEventListener("ended", () => {
    setProgress(0);
    if (card) {
      card.classList.remove("is-playing");
      card.setAttribute("aria-label", `${TRANSLATIONS[currentPageLanguage].playPrefix} ${card.querySelector("h2")?.textContent || "voice sample"}`);
    }
  });
});

updateVolumeControl();
setLanguageFilter("American English");
