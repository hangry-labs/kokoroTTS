import { AudioEditor } from './audio-editor.js'

const $ = (selector, root = document) => root.querySelector(selector)
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)]

const state = {
  activeTab: 'generate',
  defaults: null,
  status: null,
  voices: [],
  streamAbort: null,
  streamPlayback: null,
}

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

function activateTab(name) {
  state.activeTab = name
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
  if (name === 'system') refreshSystem()
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

function updateTextMetrics() {
  const text = $('#text-input').value
  const words = text.trim() ? text.trim().split(/\s+/u).length : 0
  $('#text-metrics').textContent = `${text.length} characters / ${words} words`
}

$('#text-input').addEventListener('input', updateTextMetrics)

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

async function loadSample(random = false) {
  const language = $('#language').value
  const payload = await fetchJson(`/tts/samples?language=${encodeURIComponent(language)}&random=${random}`)
  $('#text-input').value = payload.text
  updateTextMetrics()
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
      body: JSON.stringify({ text: $('#text-input').value, voice: $('#voice').value }),
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
  const paths = ['/tts/ping', '/tts/defaults', '/tts/formats', '/tts/stream-formats', '/tts/languages']
  const values = await Promise.all(paths.map(async (path) => {
    try { return [path, await fetchJson(path)] } catch (error) { return [path, { error: errorMessage(error) }] }
  }))
  renderJsonTree($('#api-output'), Object.fromEntries(values))
}

async function refreshSystem() {
  try {
    $('#gpu-output').innerHTML = '<div class="gpu-monitor"><div class="gpu-monitor-title">GPU Monitor</div><div class="gpu-monitor-muted">Loading...</div></div>'
    const [status, voices, gpu] = await Promise.all([
      fetchJson('/tts/status'),
      fetchJson('/tts/voices'),
      fetch('/system/gpu').then(async (response) => {
        if (!response.ok) throw new Error(await responseError(response))
        return response.text()
      }),
    ])
    renderJsonTree($('#runtime-output'), status, 1)
    renderJsonTree($('#voices-output'), voices, 1)
    $('#gpu-output').innerHTML = gpu
  } catch (error) {
    showToast(errorMessage(error))
  }
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
$('#system-refresh').addEventListener('click', refreshSystem)

function updateRuntime(status) {
  const badge = $('#runtime-badge')
  state.status = status
  badge.dataset.state = 'ready'
  badge.querySelector('strong').textContent = 'Inference ready'
  $('#runtime-model').textContent = `${status.repo_id} / ${status.runtime}`
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
    Object.entries(formats.formats).map(([value, config]) => ({ value, label: config.label })),
    formats.formats.mp3 ? 'mp3' : formats.default,
  )

  $('#text-input').value = defaults.text
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
  }
  setTimeout(pollReadiness, 15000)
}

document.addEventListener('audio-error', (event) => showToast(errorMessage(event.detail)))
window.addEventListener('beforeunload', () => {
  state.streamAbort?.abort()
  state.streamPlayback?.stop()
})

loadWorkspace().catch((error) => {
  setStatus('Connection failed', 'error')
  showToast(errorMessage(error))
})
pollReadiness()
