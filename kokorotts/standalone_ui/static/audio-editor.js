import WaveSurfer from './vendor/wavesurfer/wavesurfer.esm.js'
import Regions from './vendor/wavesurfer/plugins/regions.esm.js'
import { fileFromBlob, formatTime, trimAudio } from './audio-utils.js'
import { t } from './i18n.js'

const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2]

function iconButton(icon, title, action) {
  return `<button class="icon-button" type="button" data-action="${action}" title="${title}" aria-label="${title}"><i class="icon-${icon}"></i></button>`
}

export class AudioEditor {
  constructor(container, { label = t('editor.audio'), onChange = () => {} } = {}) {
    this.container = container
    this.label = label
    this.onChange = onChange
    this.file = null
    this.objectUrl = null
    this.trimRegion = null
    this.trimMode = false
    this.dragSelectionCleanup = null
    this.speedIndex = SPEEDS.indexOf(1)
    this.build()
  }

  build() {
    this.container.classList.add('audio-editor')
    this.container.innerHTML = `
      <div class="audio-editor-head">
        <div class="audio-label"><i class="icon-file-audio"></i><span>${this.label}</span><small data-role="filename">${t('editor.noAudio')}</small></div>
        <div class="audio-head-actions">
          ${iconButton('download', t('editor.download'), 'download')}
          ${iconButton('share-2', t('editor.share'), 'share')}
          ${iconButton('x', t('editor.remove'), 'remove')}
        </div>
      </div>
      <div class="wave-stage">
        <div class="wave-empty output-empty" data-role="empty"><i class="icon-audio-lines"></i><strong>${t('editor.audioOutput')}</strong><span>${t('editor.ready')}</span></div>
        <div class="waveform" data-role="waveform"></div>
      </div>
      <div class="trim-strip" data-role="trim-strip" hidden>
        <span data-role="trim-range">0:00 - 0:00</span>
        <div>
          <button class="text-button" type="button" data-action="cancel-trim">${t('editor.cancel')}</button>
          <button class="text-button primary-small" type="button" data-action="apply-trim"><i class="icon-check"></i> ${t('editor.applySelection')}</button>
        </div>
      </div>
      <div class="audio-controls">
        <div class="audio-controls-side">
          ${iconButton('volume-2', t('editor.mute'), 'mute')}
          <input class="volume-slider" data-role="volume" type="range" min="0" max="1" step="0.05" value="1" aria-label="${t('editor.volume')}">
          <button class="speed-button" type="button" data-action="speed" title="${t('editor.playbackSpeed')}">1x</button>
        </div>
        <div class="transport">
          ${iconButton('rewind', t('editor.seekBackward'), 'back')}
          <button class="play-button" type="button" data-action="play" title="${t('editor.play')}" aria-label="${t('editor.play')}"><i class="icon-play"></i></button>
          ${iconButton('fast-forward', t('editor.seekForward'), 'forward')}
        </div>
        <div class="audio-controls-side end">
          <span class="time-readout"><span data-role="current">0:00</span><span>/</span><span data-role="duration">0:00</span></span>
          ${iconButton('rotate-ccw', t('editor.restart'), 'restart')}
          ${iconButton('scissors', t('editor.trim'), 'trim')}
        </div>
      </div>
    `

    this.waveformElement = this.container.querySelector('[data-role="waveform"]')
    this.emptyElement = this.container.querySelector('[data-role="empty"]')
    this.filenameElement = this.container.querySelector('[data-role="filename"]')
    this.currentElement = this.container.querySelector('[data-role="current"]')
    this.durationElement = this.container.querySelector('[data-role="duration"]')
    this.trimStrip = this.container.querySelector('[data-role="trim-strip"]')
    this.trimRange = this.container.querySelector('[data-role="trim-range"]')

    this.regions = Regions.create()
    this.wave = WaveSurfer.create({
      container: this.waveformElement,
      waveColor: '#a8abb3',
      progressColor: '#ff7a1a',
      cursorColor: '#f7f7f8',
      cursorWidth: 1,
      height: 132,
      barWidth: 3,
      barGap: 2,
      barRadius: 2,
      normalize: true,
      dragToSeek: true,
      plugins: [this.regions],
    })

    this.wave.on('ready', () => {
      this.durationElement.textContent = formatTime(this.wave.getDuration())
      this.emptyElement.hidden = true
    })
    this.wave.on('timeupdate', (time) => { this.currentElement.textContent = formatTime(time) })
    this.wave.on('play', () => this.setPlayIcon(true))
    this.wave.on('pause', () => this.setPlayIcon(false))
    this.wave.on('finish', () => this.setPlayIcon(false))
    this.regions.on('region-created', (region) => {
      for (const existing of this.regions.getRegions()) {
        if (existing !== region) existing.remove()
      }
      this.trimRegion = region
      this.updateTrimRange()
    })
    this.regions.on('region-update', () => this.updateTrimRange())
    this.regions.on('region-updated', () => this.updateTrimRange())

    this.container.addEventListener('click', (event) => {
      const button = event.target.closest('[data-action]')
      if (!button) return
      this.handleAction(button.dataset.action).catch((error) => this.showError(error))
    })
    this.container.querySelector('[data-role="volume"]').addEventListener('input', (event) => {
      this.wave.setVolume(Number(event.target.value))
    })
  }

  setPlayIcon(playing) {
    const button = this.container.querySelector('[data-action="play"]')
    button.innerHTML = `<i class="icon-${playing ? 'pause' : 'play'}"></i>`
    button.title = playing ? t('editor.pause') : t('editor.play')
    button.setAttribute('aria-label', button.title)
  }

  async handleAction(action) {
    if (action === 'download') this.download()
    if (action === 'share') await this.share()
    if (action === 'remove') this.clear()
    if (action === 'mute') this.wave.setMuted(!this.wave.getMuted())
    if (action === 'speed') this.cycleSpeed()
    if (action === 'play' && this.file) await this.wave.playPause()
    if (action === 'back') this.wave.skip(-5)
    if (action === 'forward') this.wave.skip(5)
    if (action === 'restart') this.wave.setTime(0)
    if (action === 'trim') this.enableTrim()
    if (action === 'cancel-trim') this.disableTrim()
    if (action === 'apply-trim') await this.applyTrim()
  }

  async load(value, name = null) {
    const file = value instanceof File ? value : fileFromBlob(value, name || 'audio.wav')
    this.disableTrim()
    if (this.objectUrl) URL.revokeObjectURL(this.objectUrl)
    this.file = file
    this.objectUrl = URL.createObjectURL(file)
    this.filenameElement.textContent = file.name
    this.container.classList.add('has-audio')
    await this.wave.load(this.objectUrl)
    this.onChange(file)
  }

  clear() {
    this.disableTrim()
    this.wave.empty()
    if (this.objectUrl) URL.revokeObjectURL(this.objectUrl)
    this.objectUrl = null
    this.file = null
    this.filenameElement.textContent = t('editor.noAudio')
    this.currentElement.textContent = '0:00'
    this.durationElement.textContent = '0:00'
    this.emptyElement.hidden = false
    this.container.classList.remove('has-audio')
    this.onChange(null)
  }

  currentFile() {
    return this.file
  }

  async play() {
    if (this.file) await this.wave.play()
  }

  async playFrom(time = 0) {
    if (!this.file) return
    this.wave.setTime(Math.max(0, Math.min(time, this.wave.getDuration())))
    await this.wave.play()
  }

  cycleSpeed() {
    this.speedIndex = (this.speedIndex + 1) % SPEEDS.length
    const speed = SPEEDS[this.speedIndex]
    this.wave.setPlaybackRate(speed, true)
    this.container.querySelector('[data-action="speed"]').textContent = `${speed}x`
  }

  download() {
    if (!this.file || !this.objectUrl) return
    const anchor = document.createElement('a')
    anchor.href = this.objectUrl
    anchor.download = this.file.name
    anchor.click()
  }

  async share() {
    if (!this.file || !navigator.share) return
    const data = { files: [this.file], title: this.file.name }
    if (!navigator.canShare || navigator.canShare(data)) await navigator.share(data)
  }

  enableTrim() {
    if (!this.file || this.trimMode) return
    this.trimMode = true
    this.container.classList.add('trim-mode')
    this.trimStrip.hidden = false
    const duration = this.wave.getDuration()
    this.trimRegion = this.regions.addRegion({
      start: duration * 0.1,
      end: duration * 0.9,
      color: 'rgba(255, 122, 26, 0.22)',
      drag: true,
      resize: true,
      minLength: Math.min(0.1, duration),
    })
    this.dragSelectionCleanup = this.regions.enableDragSelection({
      color: 'rgba(255, 122, 26, 0.22)',
      drag: true,
      resize: true,
      minLength: Math.min(0.1, duration),
    })
    this.updateTrimRange()
  }

  disableTrim() {
    this.trimMode = false
    this.container.classList.remove('trim-mode')
    if (this.dragSelectionCleanup) this.dragSelectionCleanup()
    this.dragSelectionCleanup = null
    this.regions?.clearRegions()
    this.trimRegion = null
    if (this.trimStrip) this.trimStrip.hidden = true
  }

  updateTrimRange() {
    if (!this.trimRegion) return
    this.trimRange.textContent = `${formatTime(this.trimRegion.start)} - ${formatTime(this.trimRegion.end)}`
  }

  async applyTrim() {
    if (!this.file || !this.trimRegion) return
    const { start, end } = this.trimRegion
    const blob = await trimAudio(this.file, start, end)
    const stem = this.file.name.replace(/\.[^.]+$/, '')
    await this.load(blob, `${stem}-trimmed.wav`)
  }

  showError(error) {
    this.container.dispatchEvent(new CustomEvent('audio-error', { bubbles: true, detail: error }))
  }
}
