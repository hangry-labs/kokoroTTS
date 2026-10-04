import { AudioEditor } from './audio-editor.js'

const $ = (selector, root = document) => root.querySelector(selector)
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)]

const state = {
  activeTab: 'generate',
  headerCollapsed: false,
  defaults: null,
  status: null,
  voices: [],
  deploymentSettings: null,
  streamAbort: null,
  streamPlayback: null,
  gpuHistory: new Map(),
  gpuStats: [],
  gpuWindowMs: 60 * 1000,
  gpuTimer: null,
  gpuRefreshActive: false,
  gpuHovering: false,
  headerAnimation: null,
  inputType: 'text',
  plainTextDraft: '',
  ssmlDraft: '',
}

const GPU_HISTORY_RETENTION_MS = 10 * 60 * 1000
const GPU_POLL_INTERVAL_MS = 1000
const UI_SESSION_KEY = 'kokorotts-ui-state-v1'
const GPU_SESSION_KEY = 'kokorotts-gpu-history-v1'
const GPU_METRICS = [
  { key: 'utilization', label: 'GPU', color: '#ff7a1a' },
  { key: 'memory_utilization', label: 'Memory activity', color: '#c586c0' },
  { key: 'memory_used', label: 'VRAM', color: '#72a7ff' },
  { key: 'temperature', label: 'Temperature', color: '#ef6b73' },
  { key: 'power', label: 'Power', color: '#f2c94c' },
  { key: 'fan_speed', label: 'Fan', color: '#55c58a' },
  { key: 'graphics_clock', label: 'Graphics clock', color: '#9cdcfe' },
  { key: 'memory_clock', label: 'Memory clock', color: '#ce9178' },
]

const generateOutput = new AudioEditor($('#generate-output'), { label: 'Generated audio' })
const streamOutput = new AudioEditor($('#stream-output'), { label: 'Streamed audio' })

function setStatus(message, tone = 'neutral') {
  const status = $('#global-status')
  status.textContent = message
  status.dataset.tone = tone
}

function showToast(message, tone = 'error') {
  const toast = $('#toast')
  toast.textContent = message
  toast.dataset.tone = tone
  toast.hidden = false
  clearTimeout(showToast.timer)
  showToast.timer = setTimeout(() => { toast.hidden = true }, 5000)
}

function errorMessage(error) {
  if (error instanceof Error) return error.message
  return String(error)
}

async function responseError(response) {
  const text = await response.text()
  try {
    const payload = JSON.parse(text)
    return payload.error?.message || payload.detail || text
  } catch {
    return text || `HTTP ${response.status}`
  }
}

async function fetchJson(path, options) {
  const response = await fetch(path, options)
  if (!response.ok) throw new Error(await responseError(response))
  return response.json()
}

function readSessionJson(key) {
  try {
    return JSON.parse(sessionStorage.getItem(key) || 'null')
  } catch {
    return null
  }
}

function persistUiSession() {
  try {
    sessionStorage.setItem(UI_SESSION_KEY, JSON.stringify({
      activeTab: state.activeTab,
      headerCollapsed: state.headerCollapsed,
      gpuWindowMs: state.gpuWindowMs,
    }))
  } catch {
    // Session storage is optional in privacy-restricted browsers.
  }
}

function persistGpuSession() {
  try {
    sessionStorage.setItem(GPU_SESSION_KEY, JSON.stringify({
      savedAt: Date.now(),
      stats: state.gpuStats,
      history: Object.fromEntries(state.gpuHistory),
    }))
  } catch {
    // Monitoring continues in memory if session storage is unavailable.
  }
}

function restoreSessionState() {
  const ui = readSessionJson(UI_SESSION_KEY)
  if (['generate', 'stream', 'api', 'system'].includes(ui?.activeTab)) state.activeTab = ui.activeTab
  if (typeof ui?.headerCollapsed === 'boolean') state.headerCollapsed = ui.headerCollapsed
  if ([60 * 1000, 10 * 60 * 1000].includes(ui?.gpuWindowMs)) state.gpuWindowMs = ui.gpuWindowMs

  const cached = readSessionJson(GPU_SESSION_KEY)
  const now = Date.now()
  const cutoff = now - GPU_HISTORY_RETENTION_MS
  if (!cached || !Number.isFinite(cached.savedAt) || cached.savedAt < cutoff) return
  if (Array.isArray(cached.stats)) state.gpuStats = cached.stats
  if (!cached.history || typeof cached.history !== 'object') return
  Object.entries(cached.history).forEach(([index, samples]) => {
    if (!Array.isArray(samples)) return
    const recent = samples.filter((sample) => Number.isFinite(sample?.timestamp) && sample.timestamp >= cutoff)
    if (recent.length) state.gpuHistory.set(Number(index), recent)
  })
}

function setHeroCollapsed(collapsed, persist = true, animate = true) {
  const hero = $('#brand-hero')
  const toggle = $('#hero-toggle')
  state.headerAnimation?.cancel()
  const startHeight = hero.getBoundingClientRect().height

  state.headerCollapsed = collapsed
  const action = collapsed ? 'Expand header' : 'Collapse header'
  document.documentElement.dataset.headerCollapsed = String(collapsed)
  hero.dataset.collapsed = String(collapsed)
  toggle.setAttribute('aria-expanded', String(!collapsed))
  toggle.setAttribute('aria-label', action)
  toggle.title = action
  toggle.querySelector('i').className = collapsed ? 'icon-chevron-down' : 'icon-chevron-up'

  const endHeight = hero.getBoundingClientRect().height
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (animate && !reducedMotion && Math.abs(startHeight - endHeight) > 1) {
    hero.classList.add('is-rolling')
    const animation = hero.animate(
      [{ height: `${startHeight}px` }, { height: `${endHeight}px` }],
      { duration: 320, easing: 'cubic-bezier(0.22, 1, 0.36, 1)', fill: 'both' },
    )
    state.headerAnimation = animation
    animation.finished
      .catch(() => {})
      .finally(() => {
        if (state.headerAnimation !== animation) return
        hero.classList.remove('is-rolling')
        state.headerAnimation = null
        animation.cancel()
      })
  }
  if (persist) persistUiSession()
}

$('#hero-toggle').addEventListener('click', () => setHeroCollapsed(!state.headerCollapsed))

function activateTab(name) {
  state.activeTab = name
  persistUiSession()
  $$('.tab-button').forEach((button) => {
    const active = button.dataset.tab === name
    button.classList.toggle('active', active)
    button.setAttribute('aria-selected', String(active))
  })
  $$('.tab-panel').forEach((panel) => { panel.hidden = panel.dataset.panel !== name })
  const synthesisView = name === 'generate' || name === 'stream'
  $('#composer').hidden = !synthesisView
  $('.settings-panel').hidden = !synthesisView
  $('.workspace').dataset.view = name
  if (name === 'api') refreshApiStatus()
  if (name === 'system') {
    loadDeploymentSettings()
    refreshSystem()
    startGpuMonitor()
  } else {
    state.gpuHovering = false
    stopGpuMonitor()
  }
}

$$('.tab-button').forEach((button) => button.addEventListener('click', () => activateTab(button.dataset.tab)))

function clampNumericInput(input) {
  if (!input.value.trim()) return null
  const value = Number(input.value)
  if (!Number.isFinite(value)) return null
  const minimum = Number(input.min)
  const maximum = Number(input.max)
  return Math.min(maximum, Math.max(minimum, value))
}

$$('input[type="range"][data-value-input]').forEach((slider) => {
  const valueInput = $(`#${slider.dataset.valueInput}`)
  slider.addEventListener('input', () => { valueInput.value = slider.value })
})

$$('input[type="number"][data-range-input]').forEach((valueInput) => {
  const slider = $(`#${valueInput.dataset.rangeInput}`)
  valueInput.addEventListener('input', () => {
    const value = clampNumericInput(valueInput)
    if (value !== null) slider.value = String(value)
  })
  valueInput.addEventListener('change', () => {
    const value = clampNumericInput(valueInput)
    if (value === null) {
      valueInput.value = slider.value
      return
    }
    valueInput.value = String(value)
    slider.value = String(value)
  })
})

function setVoiceControlValue(name, value) {
  const valueInput = $(`#${name}`)
  valueInput.value = String(value)
  $(`#${valueInput.dataset.rangeInput}`).value = String(value)
}

function updateNormalizationState() {
  const normalized = $('#normalize').checked
  $('#volume').disabled = normalized
  $('#volume-slider').disabled = normalized
  $('#volume-control').classList.toggle('setting-disabled', normalized)
}

$('#normalize').addEventListener('change', updateNormalizationState)

function resetVoiceControls() {
  const controls = state.defaults?.audio_controls
  if (!controls) return
  setVoiceControlValue('speed', state.defaults.speed)
  setVoiceControlValue('pitch', controls.pitch_semitones)
  setVoiceControlValue('tempo', controls.tempo)
  setVoiceControlValue('volume', controls.volume)
  $('#normalize').checked = controls.normalize
  updateNormalizationState()
  setStatus('Voice controls reset', 'success')
}

$('#reset-voice-controls').addEventListener('click', resetVoiceControls)

function escapeXml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;')
}

function ssmlTemplate(value) {
  return `<speak>\n  ${escapeXml(value.trim())}\n</speak>`
}

function setComposerText(value) {
  state.plainTextDraft = value
  if (state.inputType === 'ssml') {
    state.ssmlDraft = ssmlTemplate(value)
    $('#text-input').value = state.ssmlDraft
  } else {
    $('#text-input').value = value
  }
  updateTextMetrics()
}

function setInputType(inputType) {
  const input = $('#text-input')
  if (state.inputType === 'ssml') state.ssmlDraft = input.value
  else state.plainTextDraft = input.value

  state.inputType = inputType
  if (inputType === 'ssml') {
    if (!state.ssmlDraft) state.ssmlDraft = ssmlTemplate(state.plainTextDraft)
    input.value = state.ssmlDraft
  } else {
    input.value = state.plainTextDraft
  }

  const active = inputType === 'ssml'
  const button = $('#ssml-mode-button')
  button.classList.toggle('active', active)
  button.setAttribute('aria-pressed', String(active))
  button.title = active ? 'Disable experimental SSML input' : 'Enable experimental SSML input'
  $('#composer').dataset.inputType = inputType
  $('#input-mode-label').textContent = active ? 'SSML' : 'Text'
  input.spellcheck = !active
  input.setAttribute('aria-label', active ? 'Experimental SSML to synthesize' : 'Text to synthesize')
  updateTextMetrics()
  setStatus(active ? 'Experimental SSML input enabled' : 'Plain text input enabled', active ? 'warning' : 'success')
}

function updateTextMetrics() {
  const text = $('#text-input').value
  const words = text.trim() ? text.trim().split(/\s+/u).length : 0
  const label = state.inputType === 'ssml' ? 'SSML characters' : 'characters'
  $('#text-metrics').textContent = `${text.length} ${label} / ${words} words`
}

$('#text-input').addEventListener('input', () => {
  if (state.inputType === 'ssml') state.ssmlDraft = $('#text-input').value
  else state.plainTextDraft = $('#text-input').value
  updateTextMetrics()
})

$('#ssml-mode-button').addEventListener('click', () => {
  setInputType(state.inputType === 'ssml' ? 'text' : 'ssml')
})

const ssmlDialog = $('#ssml-help-dialog')
$('#ssml-help-button').addEventListener('click', () => ssmlDialog.showModal())
$('#ssml-help-close').addEventListener('click', () => ssmlDialog.close())
ssmlDialog.addEventListener('click', (event) => {
  if (event.target === ssmlDialog) ssmlDialog.close()
})

function setSelectOptions(select, entries, selectedValue) {
  select.replaceChildren()
  entries.forEach(({ value, label }) => {
    const option = document.createElement('option')
    option.value = value
    option.textContent = label
    select.append(option)
  })
  if (entries.some((entry) => entry.value === selectedValue)) select.value = selectedValue
}

function voicesForLanguage(language) {
  return state.voices.filter((voice) => voice.language === language)
}

function voiceDisplayName(voice) {
  const name = voice.id
    .split('_')
    .slice(1)
    .join(' ')
    .replace(/\b\w/gu, (letter) => letter.toUpperCase())
  return `${name} (${voice.id})`
}

function refreshVoiceOptions(preferredVoice) {
  const voices = voicesForLanguage($('#language').value)
  setSelectOptions(
    $('#voice'),
    voices.map((voice) => ({ value: voice.id, label: voiceDisplayName(voice) })),
    preferredVoice,
  )
}

function updateModelSettingsSummary() {
  const checkboxes = $$('#model-settings-groups input[type="checkbox"]')
  const selected = checkboxes.filter((checkbox) => checkbox.checked).length
  $('#model-settings-summary').textContent = `${selected} of ${checkboxes.length} model packs selected`
}

function renderDeploymentSettings(payload) {
  state.deploymentSettings = payload
  const selected = new Set(payload.served_model_families || [])
  const container = $('#model-settings-groups')
  container.replaceChildren()
  ;(payload.supported_model_families || []).forEach((modelPack) => {
    const section = document.createElement('section')
    section.className = 'model-setting'
    const label = document.createElement('label')
    label.className = 'model-setting-choice'
    const checkbox = document.createElement('input')
    checkbox.type = 'checkbox'
    checkbox.value = modelPack.id
    checkbox.checked = selected.has(modelPack.id)
    checkbox.addEventListener('change', updateModelSettingsSummary)
    const copy = document.createElement('span')
    copy.className = 'model-setting-copy'
    const name = document.createElement('strong')
    name.textContent = modelPack.name
    const languages = (modelPack.languages || []).map((language) => language.name).join(', ')
    const metadata = document.createElement('span')
    metadata.textContent = `${modelPack.voice_count} ${modelPack.voice_count === 1 ? 'voice' : 'voices'} - ${languages}`
    const id = document.createElement('code')
    id.textContent = modelPack.id
    copy.append(name, metadata, id)
    label.append(checkbox, copy)
    const details = document.createElement('details')
    details.className = 'model-voices'
    const summary = document.createElement('summary')
    summary.textContent = 'Included voices'
    const voices = document.createElement('div')
    voices.textContent = (modelPack.voices || []).join(', ')
    details.append(summary, voices)
    section.append(label, details)
    container.append(section)
  })
  updateModelSettingsSummary()
}

async function loadDeploymentSettings() {
  try {
    renderDeploymentSettings(await fetchJson('/system/settings'))
  } catch (error) {
    showToast(errorMessage(error))
  }
}

function setAllModelSettings(checked) {
  $$('#model-settings-groups input[type="checkbox"]').forEach((checkbox) => { checkbox.checked = checked })
  updateModelSettingsSummary()
}

$('#models-select-all').addEventListener('click', () => setAllModelSettings(true))
$('#models-select-none').addEventListener('click', () => setAllModelSettings(false))

$('#save-model-settings').addEventListener('click', async () => {
  const button = $('#save-model-settings')
  const modelFamilies = $$('#model-settings-groups input[type="checkbox"]:checked').map((checkbox) => checkbox.value)
  button.disabled = true
  try {
    const settings = await fetchJson('/system/settings/model-families', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_families: modelFamilies }),
    })
    renderDeploymentSettings(settings)
    const [defaults, languages, inventory] = await Promise.all([
      fetchJson('/tts/defaults'),
      fetchJson('/tts/languages'),
      fetchJson('/tts/voices'),
    ])
    const previousLanguage = $('#language').value
    const previousVoice = $('#voice').value
    state.defaults = defaults
    state.voices = inventory.voices
    setSelectOptions(
      $('#language'),
      Object.entries(languages.languages).map(([value, label]) => ({ value, label })),
      languages.languages[previousLanguage] ? previousLanguage : state.voices[0]?.language,
    )
    refreshVoiceOptions(state.voices.some((voice) => voice.id === previousVoice) ? previousVoice : defaults.voice)
    setStatus('Deployment model packs saved', 'success')
    showToast('Model packs saved', 'success')
  } catch (error) {
    showToast(errorMessage(error))
  } finally {
    button.disabled = false
  }
})

async function loadSample(random = false) {
  const language = $('#language').value
  const payload = await fetchJson(`/tts/samples?language=${encodeURIComponent(language)}&random=${random}`)
  setComposerText(payload.text)
}

$('#language').addEventListener('change', async () => {
  refreshVoiceOptions()
  try {
    await loadSample(false)
    setStatus('Language ready', 'success')
  } catch (error) {
    showToast(errorMessage(error))
  }
})

$('#sample-button').addEventListener('click', async () => {
  try {
    await loadSample(true)
    setStatus('Sample ready', 'success')
  } catch (error) {
    showToast(errorMessage(error))
  }
})

function requestPayload(outputFormat = $('#output-format').value) {
  const normalize = $('#normalize').checked
  return {
    text: $('#text-input').value,
    input_type: state.inputType,
    voice: $('#voice').value,
    speed: Number($('#speed').value),
    device: $('#device').value,
    pitch_semitones: Number($('#pitch').value),
    tempo: Number($('#tempo').value),
    volume: normalize ? 1 : Number($('#volume').value),
    normalize,
    output_format: outputFormat,
  }
}

function responseFilename(response, fallback) {
  const disposition = response.headers.get('content-disposition') || ''
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (encoded) return decodeURIComponent(encoded[1])
  const plain = disposition.match(/filename="?([^";]+)"?/i)
  return plain?.[1] || fallback
}

$('#generate-button').addEventListener('click', async () => {
  const button = $('#generate-button')
  const payload = requestPayload()
  if (!payload.text.trim()) {
    showToast('Enter text before generating audio.')
    return
  }
  button.disabled = true
  $('#output-format').disabled = true
  generateOutput.clear()
  setStatus('Generating audio')
  const started = performance.now()
  try {
    const response = await fetch('/tts/generate', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) throw new Error(await responseError(response))
    const blob = await response.blob()
    const extension = payload.output_format
    await generateOutput.load(blob, responseFilename(response, `kokorotts_${payload.voice}.${extension}`))
    await generateOutput.play().catch(() => {})
    setStatus(`Generated in ${((performance.now() - started) / 1000).toFixed(2)}s`, 'success')
  } catch (error) {
    setStatus('Generation failed', 'error')
    showToast(errorMessage(error))
  } finally {
    button.disabled = false
    $('#output-format').disabled = false
  }
})

$('#output-format').addEventListener('change', () => {
  if (!generateOutput.currentFile()) return
  generateOutput.clear()
  setStatus('Output format changed; generate audio again')
})

$('#tokenize-button').addEventListener('click', async () => {
  const button = $('#tokenize-button')
  button.disabled = true
  try {
    const payload = await fetchJson('/tts/tokenize', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ text: $('#text-input').value, voice: $('#voice').value, input_type: state.inputType }),
    })
    $('#token-output').textContent = JSON.stringify(payload, null, 2)
    $('#token-details').open = true
  } catch (error) {
    showToast(errorMessage(error))
  } finally {
    button.disabled = false
  }
})

class IncrementalAudioPlayback {
  static async create() {
    if (!window.MediaSource || !MediaSource.isTypeSupported('audio/mpeg')) return null
    const mediaSource = new MediaSource()
    const objectUrl = URL.createObjectURL(mediaSource)
    const audio = new Audio(objectUrl)
    await new Promise((resolve, reject) => {
      mediaSource.addEventListener('sourceopen', resolve, { once: true })
      mediaSource.addEventListener('error', reject, { once: true })
    })
    try {
      return new IncrementalAudioPlayback(mediaSource, audio, objectUrl)
    } catch {
      URL.revokeObjectURL(objectUrl)
      return null
    }
  }

  constructor(mediaSource, audio, objectUrl) {
    this.mediaSource = mediaSource
    this.audio = audio
    this.objectUrl = objectUrl
    this.sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg')
    this.queue = Promise.resolve()
    this.started = false
  }

  append(chunk) {
    const bytes = chunk.buffer.slice(chunk.byteOffset, chunk.byteOffset + chunk.byteLength)
    this.queue = this.queue.then(() => new Promise((resolve, reject) => {
      const done = () => {
        this.sourceBuffer.removeEventListener('error', failed)
        resolve()
      }
      const failed = () => {
        this.sourceBuffer.removeEventListener('updateend', done)
        reject(new Error('Browser could not buffer streamed MP3 audio.'))
      }
      this.sourceBuffer.addEventListener('updateend', done, { once: true })
      this.sourceBuffer.addEventListener('error', failed, { once: true })
      this.sourceBuffer.appendBuffer(bytes)
    })).then(() => {
      if (!this.started) {
        this.started = true
        this.audio.play().catch(() => {})
      }
    })
    return this.queue
  }

  async finish() {
    await this.queue
    if (this.mediaSource.readyState === 'open') this.mediaSource.endOfStream()
  }

  currentTime() {
    return this.audio.currentTime || 0
  }

  stop() {
    this.audio.pause()
    if (this.mediaSource.readyState === 'open') {
      try { this.mediaSource.endOfStream() } catch {}
    }
    URL.revokeObjectURL(this.objectUrl)
  }
}

function setStreaming(active) {
  $('#stream-start').disabled = active
  $('#stream-stop').disabled = !active
  $('#stream-progress').hidden = !active
}

async function loadStreamResult(chunks, voice, autoplay) {
  if (!chunks.length) return
  const blob = new Blob(chunks, { type: 'audio/mpeg' })
  await streamOutput.load(blob, `kokorotts_${voice}_stream.mp3`)
  if (autoplay) await streamOutput.play().catch(() => {})
}

$('#stream-start').addEventListener('click', async () => {
  const payload = { ...requestPayload('mp3'), stream_format: 'mp3' }
  if (!payload.text.trim()) {
    showToast('Enter text before streaming audio.')
    return
  }
  const controller = new AbortController()
  const chunks = []
  state.streamAbort = controller
  streamOutput.clear()
  setStreaming(true)
  setStatus('Starting stream')
  const started = performance.now()
  let playback = null
  try {
    playback = await IncrementalAudioPlayback.create()
    state.streamPlayback = playback
    const response = await fetch('/tts/stream', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
    if (!response.ok) throw new Error(await responseError(response))
    if (!response.body) throw new Error('Streaming response body is unavailable in this browser.')
    const reader = response.body.getReader()
    let totalBytes = 0
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      chunks.push(value)
      totalBytes += value.byteLength
      if (playback) playback.append(value).catch((error) => showToast(errorMessage(error)))
      setStatus(`Streaming ${(totalBytes / 1024).toFixed(0)} KiB`)
    }
    let resumeAt = 0
    if (playback) {
      await playback.finish()
      resumeAt = playback.currentTime()
      playback.stop()
      playback = null
      state.streamPlayback = null
    }
    await loadStreamResult(chunks, payload.voice, !resumeAt)
    if (resumeAt) await streamOutput.playFrom(resumeAt).catch(() => {})
    setStatus(`Stream complete in ${((performance.now() - started) / 1000).toFixed(2)}s`, 'success')
  } catch (error) {
    if (error.name === 'AbortError') {
      await loadStreamResult(chunks, payload.voice, false)
      setStatus('Stream stopped', 'success')
    } else {
      setStatus('Stream failed', 'error')
      showToast(errorMessage(error))
    }
  } finally {
    playback?.stop()
    state.streamAbort = null
    state.streamPlayback = null
    setStreaming(false)
  }
})

$('#stream-stop').addEventListener('click', () => {
  setStatus('Stopping stream')
  state.streamAbort?.abort()
  state.streamPlayback?.stop()
})

async function refreshApiStatus() {
  $('#api-output').textContent = 'Loading...'
  const groups = {
    'OpenAI-compatible API': ['/health/ready', '/v1/models'],
    'KokoroTTS native API': ['/tts/ping', '/tts/defaults', '/tts/formats', '/tts/stream-formats', '/tts/languages'],
  }
  const output = {}
  for (const [group, paths] of Object.entries(groups)) {
    const values = await Promise.all(paths.map(async (path) => {
      try { return [path, await fetchJson(path)] } catch (error) { return [path, { error: errorMessage(error) }] }
    }))
    output[group] = Object.fromEntries(values)
  }
  renderJsonTree($('#api-output'), output)
}

async function refreshSystem() {
  try {
    const [status, voices] = await Promise.all([
      fetchJson('/tts/status'),
      fetchJson('/tts/voices'),
    ])
    renderJsonTree($('#runtime-output'), status, 1)
    renderJsonTree($('#voices-output'), voices, 1)
  } catch (error) {
    showToast(errorMessage(error))
  }
}

function element(tag, className, text) {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

function gpuHistoryPoints(samples, now, windowMs, metricKey, maximum, width = 300, height = 70) {
  const windowStart = now - windowMs
  return samples.filter((sample) => Number.isFinite(sample[metricKey])).map((sample) => {
    const x = Math.min(width, Math.max(0, (sample.timestamp - windowStart) / windowMs * width))
    const y = height - (Math.min(maximum, Math.max(0, sample[metricKey])) / maximum * height)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

function addGpuChartGrid(svg, width, height) {
  for (let column = 0; column <= 10; column += 1) {
    const x = column * width / 10
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
    line.setAttribute('class', 'gpu-grid-line')
    line.setAttribute('x1', String(x))
    line.setAttribute('x2', String(x))
    line.setAttribute('y1', '0')
    line.setAttribute('y2', String(height))
    svg.append(line)
  }
  for (let row = 0; row <= 4; row += 1) {
    const y = row * height / 4
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
    line.setAttribute('class', 'gpu-grid-line')
    line.setAttribute('x1', '0')
    line.setAttribute('x2', String(width))
    line.setAttribute('y1', String(y))
    line.setAttribute('y2', String(y))
    svg.append(line)
  }
}

function mergeGpuHistory(historyPayload) {
  const cutoff = Date.now() - GPU_HISTORY_RETENTION_MS
  Object.entries(historyPayload || {}).forEach(([index, incoming]) => {
    if (!Array.isArray(incoming)) return
    const samplesByTimestamp = new Map()
    const combinedSamples = [...(state.gpuHistory.get(Number(index)) || []), ...incoming]
    combinedSamples.forEach((sample) => {
      if (Number.isFinite(sample?.timestamp) && sample.timestamp >= cutoff) {
        samplesByTimestamp.set(sample.timestamp, sample)
      }
    })
    const merged = [...samplesByTimestamp.values()].sort((left, right) => left.timestamp - right.timestamp)
    if (merged.length) state.gpuHistory.set(Number(index), merged)
  })
  state.gpuHistory.forEach((samples, index) => {
    const recent = samples.filter((sample) => sample.timestamp >= cutoff)
    if (recent.length) state.gpuHistory.set(index, recent)
    else state.gpuHistory.delete(index)
  })
  persistGpuSession()
}

function gpuMetricMaximum(metric, gpu, history) {
  const observedMaximum = Math.max(1, ...history.map((sample) => sample[metric.key] || 0))
  if (['utilization', 'memory_utilization', 'temperature', 'fan_speed'].includes(metric.key)) return 100
  if (metric.key === 'memory_used' && Number.isFinite(gpu.memory_total)) return Math.max(1, gpu.memory_total)
  if (metric.key === 'power' && Number.isFinite(gpu.power_limit)) return Math.max(1, gpu.power_limit)
  if (metric.key === 'graphics_clock' && Number.isFinite(gpu.graphics_clock_max)) {
    return Math.max(1, gpu.graphics_clock_max)
  }
  if (metric.key === 'memory_clock' && Number.isFinite(gpu.memory_clock_max)) {
    return Math.max(1, gpu.memory_clock_max)
  }
  return Math.ceil(observedMaximum * 1.1)
}

function formatGpuMetric(metric, value) {
  if (!Number.isFinite(value)) return 'N/A'
  if (['utilization', 'memory_utilization', 'fan_speed'].includes(metric.key)) return `${Math.round(value)}%`
  if (metric.key === 'memory_used') return `${(value / 1024).toFixed(1)} GB`
  if (metric.key === 'temperature') return `${Math.round(value)} C`
  if (metric.key === 'power') return `${Math.round(value)} W`
  return `${Math.round(value)} MHz`
}

function attachGpuChartHover(plot, samples, metric, now) {
  const line = element('div', 'gpu-hover-line')
  const tooltip = element('div', 'gpu-hover-tooltip')
  line.hidden = true
  tooltip.hidden = true
  plot.append(line, tooltip)

  plot.addEventListener('pointermove', (event) => {
    state.gpuHovering = true
    const bounds = plot.getBoundingClientRect()
    const offset = Math.min(bounds.width, Math.max(0, event.clientX - bounds.left))
    const ratio = bounds.width ? offset / bounds.width : 0
    const targetTime = now - state.gpuWindowMs + (ratio * state.gpuWindowMs)
    const nearest = samples.reduce((best, sample) => {
      if (!best) return sample
      return Math.abs(sample.timestamp - targetTime) < Math.abs(best.timestamp - targetTime) ? sample : best
    }, null)
    const tolerance = Math.max(1500, state.gpuWindowMs * 10 / Math.max(1, bounds.width))
    const hasSample = nearest && Math.abs(nearest.timestamp - targetTime) <= tolerance
    const shownTime = new Date(hasSample ? nearest.timestamp : targetTime).toLocaleTimeString()
    tooltip.textContent = hasSample
      ? `${formatGpuMetric(metric, nearest[metric.key])} / ${shownTime}`
      : `No sample / ${shownTime}`
    const percent = ratio * 100
    line.style.left = `${percent}%`
    tooltip.style.left = `${percent}%`
    tooltip.classList.toggle('align-start', percent < 18)
    tooltip.classList.toggle('align-end', percent > 82)
    line.hidden = false
    tooltip.hidden = false
  })
  plot.addEventListener('pointerleave', () => {
    state.gpuHovering = false
    line.hidden = true
    tooltip.hidden = true
    renderGpuMonitor(state.gpuStats)
  })
}

function createGpuMetricChart(metric, gpu, history, now) {
  const current = gpu[metric.key]
  if (!Number.isFinite(current)) return null
  const samples = history.filter((sample) => Number.isFinite(sample[metric.key]))
  const maximum = gpuMetricMaximum(metric, gpu, samples)
  const average = samples.length
    ? samples.reduce((total, sample) => total + sample[metric.key], 0) / samples.length
    : current
  const peak = samples.length ? Math.max(...samples.map((sample) => sample[metric.key])) : current
  const chart = element('div', 'gpu-metric-chart')
  chart.style.setProperty('--chart-color', metric.color)
  const chartScale = element('div', 'gpu-chart-scale')
  chartScale.append(element('span', '', metric.label), element('strong', '', formatGpuMetric(metric, current)))
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  svg.setAttribute('class', 'gpu-sparkline')
  svg.setAttribute('viewBox', '0 0 300 70')
  svg.setAttribute('preserveAspectRatio', 'none')
  svg.setAttribute(
    'aria-label',
    `${metric.label} history, average ${formatGpuMetric(metric, average)}, peak ${formatGpuMetric(metric, peak)}`,
  )
  svg.setAttribute('role', 'img')
  addGpuChartGrid(svg, 300, 70)
  const points = gpuHistoryPoints(samples, now, state.gpuWindowMs, metric.key, maximum)
  if (samples.length > 1) {
    const pointList = points.split(' ')
    const firstX = pointList[0].split(',')[0]
    const lastX = pointList.at(-1).split(',')[0]
    const area = document.createElementNS('http://www.w3.org/2000/svg', 'polygon')
    area.setAttribute('class', 'gpu-chart-area')
    area.setAttribute('points', `${firstX},70 ${points} ${lastX},70`)
    svg.append(area)
  }
  const line = document.createElementNS('http://www.w3.org/2000/svg', 'polyline')
  line.setAttribute('class', 'gpu-chart-line')
  line.setAttribute('points', points)
  svg.append(line)
  if (samples.length) {
    const latestPoint = points.split(' ').at(-1).split(',')
    const marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle')
    marker.setAttribute('class', 'gpu-chart-marker')
    marker.setAttribute('cx', latestPoint[0])
    marker.setAttribute('cy', latestPoint[1])
    marker.setAttribute('r', '2.5')
    svg.append(marker)
  }
  const plot = element('div', 'gpu-chart-plot')
  plot.append(svg)
  attachGpuChartHover(plot, samples, metric, now)
  const chartAxis = element('div', 'gpu-chart-axis')
  chartAxis.append(
    element('span', '', state.gpuWindowMs === 60 * 1000 ? '1 min' : '10 min'),
    element('span', '', `Avg ${formatGpuMetric(metric, average)} / Peak ${formatGpuMetric(metric, peak)}`),
  )
  chart.append(chartScale, plot, chartAxis)
  return chart
}

function renderGpuMonitor(gpus) {
  const output = $('#gpu-output')
  const monitor = element('div', 'gpu-monitor')
  const heading = element('div', 'gpu-monitor-heading')
  const windowControl = element('div', 'gpu-window-control')
  windowControl.setAttribute('role', 'group')
  windowControl.setAttribute('aria-label', 'GPU history window')
  const historyWindows = [[60 * 1000, '1 min'], [10 * 60 * 1000, '10 min']]
  historyWindows.forEach(([windowMs, label]) => {
    const button = element('button', windowMs === state.gpuWindowMs ? 'active' : '', label)
    button.type = 'button'
    button.setAttribute('aria-pressed', String(windowMs === state.gpuWindowMs))
    button.addEventListener('click', () => {
      state.gpuWindowMs = windowMs
      persistUiSession()
      renderGpuMonitor(state.gpuStats)
    })
    windowControl.append(button)
  })
  heading.append(element('div', 'gpu-monitor-title', 'GPU Monitor'), windowControl)
  monitor.append(heading)

  if (!gpus.length) {
    monitor.append(element('div', 'gpu-monitor-muted', 'nvidia-smi unavailable'))
    output.replaceChildren(monitor)
    return
  }

  const grid = element('div', 'gpu-card-grid')
  gpus.forEach((gpu) => {
    const now = Date.now()
    const history = (state.gpuHistory.get(gpu.index) || [])
      .filter((sample) => sample.timestamp >= now - state.gpuWindowMs)
    const card = element('div', 'gpu-card')
    const cardHead = element('div', 'gpu-card-head')
    cardHead.append(element('strong', '', `GPU ${gpu.index}`), element('span', '', gpu.name))
    const metrics = element('div', 'gpu-metrics-grid')
    GPU_METRICS.forEach((metric) => {
      const chart = createGpuMetricChart(metric, gpu, history, now)
      if (chart) metrics.append(chart)
    })
    const details = element('div', 'gpu-live-details')
    if (gpu.performance_state) details.append(element('span', '', `State ${gpu.performance_state}`))
    if (Number.isFinite(gpu.pcie_generation) && Number.isFinite(gpu.pcie_width)) {
      details.append(element('span', '', `PCIe Gen ${gpu.pcie_generation} x${gpu.pcie_width}`))
    }
    if (Number.isFinite(gpu.power_limit)) {
      details.append(element('span', '', `Power limit ${Math.round(gpu.power_limit)} W`))
    }
    card.append(cardHead, metrics, details)
    grid.append(card)
  })
  monitor.append(grid)
  output.replaceChildren(monitor)
}

async function refreshGpuMonitor() {
  if (state.gpuRefreshActive) return
  state.gpuRefreshActive = true
  try {
    const payload = await fetchJson('/system/gpu')
    state.gpuStats = Array.isArray(payload.gpus) ? payload.gpus : []
    mergeGpuHistory(payload.history)
    if (!state.gpuHovering) renderGpuMonitor(state.gpuStats)
  } catch {
    if (!state.gpuHovering) renderGpuMonitor(state.gpuStats)
  } finally {
    state.gpuRefreshActive = false
  }
}

function startGpuMonitor() {
  if (state.gpuTimer || document.hidden) return
  if (state.gpuStats.length) renderGpuMonitor(state.gpuStats)
  refreshGpuMonitor()
  state.gpuTimer = setInterval(refreshGpuMonitor, GPU_POLL_INTERVAL_MS)
}

function stopGpuMonitor() {
  clearInterval(state.gpuTimer)
  state.gpuTimer = null
}

function jsonPrimitive(value) {
  const span = document.createElement('span')
  if (value === null) {
    span.className = 'json-null'
    span.textContent = 'null'
  } else if (typeof value === 'string') {
    span.className = 'json-string'
    span.textContent = JSON.stringify(value)
  } else if (typeof value === 'number') {
    span.className = 'json-number'
    span.textContent = String(value)
  } else {
    span.className = 'json-boolean'
    span.textContent = String(value)
  }
  return span
}

function jsonKey(key) {
  const span = document.createElement('span')
  span.className = 'json-key'
  span.textContent = `${typeof key === 'number' ? key : JSON.stringify(String(key))}: `
  return span
}

function createJsonNode(value, key, depth, expandDepth) {
  const composite = value !== null && typeof value === 'object'
  if (!composite) {
    const row = document.createElement('div')
    row.className = 'json-row'
    if (key !== null) row.append(jsonKey(key))
    row.append(jsonPrimitive(value))
    return row
  }

  const array = Array.isArray(value)
  const entries = Object.entries(value)
  const details = document.createElement('details')
  details.className = 'json-branch'
  details.open = depth < expandDepth

  const summary = document.createElement('summary')
  if (key !== null) summary.append(jsonKey(key))
  const opening = document.createElement('span')
  opening.className = 'json-bracket'
  opening.textContent = array ? '[' : '{'
  const count = document.createElement('span')
  count.className = 'json-count'
  count.textContent = `${entries.length} ${entries.length === 1 ? 'item' : 'items'}`
  const closing = document.createElement('span')
  closing.className = 'json-bracket json-collapsed-close'
  closing.textContent = array ? ']' : '}'
  summary.append(opening, count, closing)

  const children = document.createElement('div')
  children.className = 'json-children'
  entries.forEach(([entryKey, entryValue]) => {
    children.append(createJsonNode(entryValue, array ? Number(entryKey) : entryKey, depth + 1, expandDepth))
  })
  const closeRow = document.createElement('div')
  closeRow.className = 'json-close'
  closeRow.textContent = array ? ']' : '}'
  details.append(summary, children, closeRow)
  return details
}

function renderJsonTree(container, value, expandDepth = 1) {
  container.replaceChildren(createJsonNode(value, null, 0, expandDepth))
}

$('#api-refresh').addEventListener('click', refreshApiStatus)

function updateRuntime(status) {
  const badge = $('#runtime-badge')
  state.status = status
  badge.dataset.state = 'ready'
  badge.querySelector('strong').textContent = 'Inference ready'
  $('#runtime-model').textContent = `${status.repo_id} / ${status.runtime}`
  badge.title = `${status.repo_id} / ${status.runtime}`
  const devices = status.hardware || [
    { value: 'auto', label: 'Auto' },
    { value: 'cpu', label: 'CPU' },
  ]
  const selectedDevice = $('#device').value || state.defaults?.device || 'auto'
  setSelectOptions($('#device'), devices, selectedDevice)
}

async function loadWorkspace() {
  const [defaults, status, languages, voices, formats] = await Promise.all([
    fetchJson('/tts/defaults'),
    fetchJson('/tts/status'),
    fetchJson('/tts/languages'),
    fetchJson('/tts/voices'),
    fetchJson('/tts/formats'),
  ])
  state.defaults = defaults
  state.voices = voices.voices

  setSelectOptions(
    $('#language'),
    Object.entries(languages.languages).map(([value, label]) => ({ value, label })),
    state.voices.find((voice) => voice.id === defaults.voice)?.language || 'a',
  )
  refreshVoiceOptions(defaults.voice)
  setSelectOptions(
    $('#output-format'),
    Object.entries(formats.formats)
      .filter(([, config]) => config.browser_playback !== false)
      .map(([value, config]) => ({ value, label: config.label })),
    formats.formats.mp3 ? 'mp3' : formats.default,
  )

  state.inputType = 'text'
  state.plainTextDraft = defaults.text
  state.ssmlDraft = ''
  $('#text-input').value = defaults.text
  setInputType(defaults.input_type || 'text')
  setVoiceControlValue('speed', defaults.speed)
  setVoiceControlValue('pitch', defaults.audio_controls.pitch_semitones)
  setVoiceControlValue('tempo', defaults.audio_controls.tempo)
  setVoiceControlValue('volume', defaults.audio_controls.volume)
  $('#normalize').checked = defaults.audio_controls.normalize
  updateNormalizationState()
  $('#reset-voice-controls').disabled = false
  updateTextMetrics()
  updateRuntime(status)
  setStatus('Ready', 'success')
}

async function pollReadiness() {
  try {
    updateRuntime(await fetchJson('/tts/status'))
  } catch {
    const badge = $('#runtime-badge')
    badge.dataset.state = 'starting'
    badge.querySelector('strong').textContent = 'Inference starting'
    $('#runtime-model').textContent = 'Waiting for inference service'
    badge.title = 'Waiting for inference service'
  }
  setTimeout(pollReadiness, 15000)
}

document.addEventListener('audio-error', (event) => showToast(errorMessage(event.detail)))
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    stopGpuMonitor()
  } else if (state.activeTab === 'system') {
    startGpuMonitor()
  }
})
window.addEventListener('beforeunload', () => {
  state.streamAbort?.abort()
  state.streamPlayback?.stop()
  stopGpuMonitor()
})

restoreSessionState()
setHeroCollapsed(state.headerCollapsed, false, false)
loadWorkspace()
  .then(() => activateTab(state.activeTab))
  .catch((error) => {
    setStatus('Connection failed', 'error')
    showToast(errorMessage(error))
  })
pollReadiness()
