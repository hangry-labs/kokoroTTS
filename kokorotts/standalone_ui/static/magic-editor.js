import { t, languageLabel } from './i18n.js'
import { closeDialogOnBackdrop } from './dialog-utils.js?v=pointerdown-v1'
import { parseMagicDocument, renderedSpeechText, serializeMagicDocument } from './magic-document.js'
import { MagicToolbar } from './magic-toolbar.js'

const DEFAULT_BREAK_MS = 300

const DIRECTIONS = [
  ['', 'magic.directionNone', 'Natural'],
  ['Calm and reassuring', 'magic.directionCalm', 'Calm'],
  ['Energetic and upbeat', 'magic.directionEnergetic', 'Energetic'],
  ['Warm and confident', 'magic.directionWarm', 'Warm'],
  ['Authoritative and precise', 'magic.directionAuthoritative', 'Authoritative'],
  ['Urgent and alarmed', 'magic.directionUrgent', 'Urgent'],
  ['__custom__', 'magic.directionCustom', 'Custom...'],
]

const EXPRESSIVE_CUES = [
  ['', 'magic.cuePlaceholder', 'Add cue...'],
  ['[sigh]', 'magic.cueSigh', 'Sigh'],
  ['[laughing]', 'magic.cueLaughing', 'Laughing'],
  ['[Uhm]', 'magic.cueThinking', 'Thinking'],
  ['[Shh]', 'magic.cueHush', 'Hush'],
  ['[Question-en]', 'magic.cueQuestion', 'Question'],
  ['[Surprise-wa]', 'magic.cueSurprise', 'Surprise'],
  ['[Dissatisfaction-hnn]', 'magic.cueDissatisfaction', 'Dissatisfaction'],
]

const SAY_AS_MODES = [
  ['', 'magic.sayAsPlaceholder', 'Say selected text as...'],
  ['characters', 'magic.sayAsCharacters', 'Characters'],
  ['digits', 'magic.sayAsDigits', 'Digits'],
  ['cardinal', 'magic.sayAsCardinal', 'Cardinal number'],
  ['ordinal', 'magic.sayAsOrdinal', 'Ordinal number (English)'],
]

const PROSODY_OPTIONS = {
  rate: [
    ['', 'magic.prosodyDefault', 'Default'], ['x-slow', 'magic.rateXSlow', 'Extra slow'],
    ['slow', 'magic.rateSlow', 'Slow'], ['medium', 'magic.rateMedium', 'Medium'],
    ['fast', 'magic.rateFast', 'Fast'], ['x-fast', 'magic.rateXFast', 'Extra fast'],
  ],
  pitch: [
    ['', 'magic.prosodyDefault', 'Default'], ['x-low', 'magic.pitchXLow', 'Extra low'],
    ['low', 'magic.pitchLow', 'Low'], ['medium', 'magic.pitchMedium', 'Medium'],
    ['high', 'magic.pitchHigh', 'High'], ['x-high', 'magic.pitchXHigh', 'Extra high'],
  ],
  volume: [
    ['', 'magic.prosodyDefault', 'Default'], ['x-soft', 'magic.volumeXSoft', 'Extra soft'],
    ['soft', 'magic.volumeSoft', 'Soft'], ['medium', 'magic.volumeMedium', 'Medium'],
    ['loud', 'magic.volumeLoud', 'Loud'], ['x-loud', 'magic.volumeXLoud', 'Extra loud'],
  ],
}

function button(icon, title, action) {
  const control = document.createElement('button')
  control.type = 'button'
  control.className = 'icon-button magic-block-action'
  control.dataset.magicAction = action
  control.title = title
  control.setAttribute('aria-label', title)
  const glyph = document.createElement('i')
  glyph.className = icon
  control.append(glyph)
  return control
}

function chip(className, text, action, title) {
  const control = document.createElement('button')
  control.type = 'button'
  control.className = `magic-chip ${className}`
  control.dataset.magicAction = action
  control.textContent = text
  control.title = title
  control.setAttribute('aria-label', title)
  return control
}

function removableChip(className, text, editAction, clearAction, editTitle, clearTitle) {
  const group = document.createElement('span')
  group.className = `magic-chip-group ${className}`
  const edit = chip(className, text, editAction, editTitle)
  const remove = document.createElement('button')
  remove.type = 'button'
  remove.className = 'magic-chip-remove'
  remove.dataset.magicAction = clearAction
  remove.title = clearTitle
  remove.setAttribute('aria-label', clearTitle)
  const icon = document.createElement('i')
  icon.className = 'icon-x'
  icon.setAttribute('aria-hidden', 'true')
  remove.append(icon)
  group.append(edit, remove)
  return group
}

function dragHandle(title) {
  const control = document.createElement('button')
  control.type = 'button'
  control.className = 'icon-button magic-block-action magic-drag-handle'
  control.dataset.magicDrag = 'true'
  control.title = title
  control.setAttribute('aria-label', title)
  return control
}

export class MagicEditor {
  constructor(root, {
    onChange,
    onPreview,
    onSaveCharacter,
    onPersistCharacter,
    onError,
    onHistoryChange,
  } = {}) {
    this.root = root
    this.canvas = root.querySelector('#magic-editor')
    this.voiceControl = root.querySelector('#magic-voice-control')
    this.languageControl = root.querySelector('#magic-language-control')
    this.directionControl = root.querySelector('#magic-direction-control')
    this.customDirection = root.querySelector('#magic-custom-direction')
    this.rateControl = root.querySelector('#magic-rate-control')
    this.pitchControl = root.querySelector('#magic-pitch-control')
    this.volumeControl = root.querySelector('#magic-volume-control')
    this.expressionControl = root.querySelector('#magic-expression-control')
    this.sayAsControl = root.querySelector('#magic-say-as-control')
    this.summary = root.querySelector('#magic-summary')
    this.onChange = onChange || (() => {})
    this.onPreview = onPreview || (async () => null)
    this.onSaveCharacter = onSaveCharacter || (async () => {})
    this.onPersistCharacter = onPersistCharacter || (async () => null)
    this.onError = onError || (() => {})
    this.onHistoryChange = onHistoryChange || (() => {})
    this.nextId = 1
    this.voices = []
    this.profileIds = new Set()
    this.languages = []
    this.defaultVoice = null
    this.busy = false
    this.previewBusyId = null
    this.playingId = null
    this.previewAudio = new Audio()
    this.previewAudio.addEventListener('ended', () => {
      this.playingId = null
      this.renderBlocks()
    })
    this.maxBreakMs = 10_000
    this.supportsVoice = true
    this.supportsDirection = true
    this.supportsDefaultDirection = true
    this.supportsLanguage = true
    this.supportsProsody = true
    this.supportsSubstitution = true
    this.supportedSayAs = new Set()
    this.documentMeta = { voiceDefinitions: [], language: '' }
    this.pendingDragId = null
    this.draggingId = null
    this.pendingSubstitution = null
    this.history = []
    this.historyIndex = -1
    this.historyLimit = 100
    this.restoringHistory = false
    this.toolbar = new MagicToolbar(root)
    // Kokoro exposes native voices and effects, not generative voice design.
    this.definitionEditor = { setCapabilities() {}, setDefinitions() {}, getDefinitions: () => [], show() {} }
    this.blocks = [this.createSpeech('')]
    this.activeId = this.blocks[0].id
    this.bind()
    this.render()
    this.resetHistory()
  }

  createSpeech(text = '') {
    return {
      id: this.nextId++,
      type: 'speech',
      text,
      annotations: [],
      voice: '',
      direction: '',
      language: '',
      prosody: { rate: '', pitch: '', volume: '' },
      preview: null,
      captureSeed: null,
      locked: false,
    }
  }

  createBreak(milliseconds = DEFAULT_BREAK_MS) {
    return { id: this.nextId++, type: 'break', milliseconds }
  }

  bind() {
    this.root.querySelector('#magic-add-turn').addEventListener('click', () => this.insertAfterActive(this.createSpeech()))
    this.root.querySelector('#magic-add-pause').addEventListener('click', () => this.insertAfterActive(this.createBreak()))
    this.root.querySelector('#magic-edit-definitions').addEventListener('click', () => this.definitionEditor.show())
    this.root.querySelector('#magic-add-substitution').addEventListener('click', () => this.openSubstitutionDialog())
    this.voiceControl.addEventListener('change', () => {
      const block = this.activeSpeech()
      if (!block) return
      this.invalidateBlock(block)
      block.voice = this.voiceControl.value
      this.render()
      this.changed()
    })
    this.languageControl.addEventListener('change', () => {
      const block = this.activeSpeech()
      if (!block) return
      this.invalidateBlock(block)
      block.language = this.languageControl.value
      this.renderBlocks()
      this.syncToolbar()
      this.changed()
    })
    this.directionControl.addEventListener('change', () => {
      const block = this.activeSpeech()
      if (!block) return
      this.invalidateBlock(block)
      const custom = this.directionControl.value === '__custom__'
      block.direction = custom ? this.customDirection.value.trim() : this.directionControl.value
      this.renderBlocks()
      this.syncToolbar()
      this.changed()
      if (custom) this.customDirection.focus()
    })
    this.customDirection.addEventListener('input', () => {
      const block = this.activeSpeech()
      if (!block) return
      this.invalidateBlock(block)
      block.direction = this.customDirection.value.trim()
      this.directionControl.value = '__custom__'
      this.renderBlocks()
      // Keep the live input value intact so a trailing space is not trimmed
      // and written back before the user can type the next word.
      this.toolbar.sync()
      this.changed()
    })
    this.expressionControl.addEventListener('change', () => {
      const cue = this.expressionControl.value
      this.expressionControl.value = ''
      if (cue) this.insertCue(cue)
    })
    for (const [name, control] of [
      ['rate', this.rateControl], ['pitch', this.pitchControl], ['volume', this.volumeControl],
    ]) {
      control.addEventListener('change', () => {
        const block = this.activeSpeech()
        if (!block) return
        this.invalidateBlock(block)
        block.prosody[name] = control.value
        this.renderBlocks()
        this.syncToolbar()
        this.changed()
      })
    }
    this.sayAsControl.addEventListener('change', () => {
      const mode = this.sayAsControl.value
      this.sayAsControl.value = ''
      if (mode) this.applySelectionAnnotation({ type: 'say-as', interpretAs: mode })
    })
    this.canvas.addEventListener('focusin', (event) => {
      const block = event.target.closest('[data-magic-id]')
      if (block) this.activate(Number(block.dataset.magicId))
    })
    this.canvas.addEventListener('click', (event) => {
      const blockElement = event.target.closest('[data-magic-id]')
      if (blockElement) this.activate(Number(blockElement.dataset.magicId))
      const annotationButton = event.target.closest('[data-magic-annotation]')
      if (annotationButton && blockElement) {
        this.removeAnnotation(Number(blockElement.dataset.magicId), Number(annotationButton.dataset.magicAnnotation))
        return
      }
      const actionControl = event.target.closest('[data-magic-action]')
      const action = actionControl?.dataset.magicAction
      if (!action || !blockElement) return
      this.applyBlockAction(Number(blockElement.dataset.magicId), action, actionControl).catch(this.onError)
    })
    this.canvas.addEventListener('input', (event) => {
      const blockElement = event.target.closest('[data-magic-id]')
      const block = this.block(Number(blockElement?.dataset.magicId))
      if (!block) return
      if (event.target.matches('textarea')) {
        const generatedStateChanged = Boolean(block.preview || Number.isInteger(block.captureSeed))
        const previousText = block.text
        const annotationCount = block.annotations.length
        block.text = event.target.value
        block.annotations = this.reconcileAnnotations(previousText, block.text, block.annotations)
        this.invalidateBlock(block)
        if (generatedStateChanged || annotationCount !== block.annotations.length) this.renderBlocks()
      }
      if (event.target.matches('input[type="number"]')) {
        block.milliseconds = Math.min(this.maxBreakMs, Math.max(0, Number(event.target.value) || 0))
      }
      this.updateSummary()
      this.changed()
    })
    this.canvas.addEventListener('pointerdown', (event) => {
      const handle = event.target.closest('[data-magic-drag]')
      const blockElement = handle?.closest('[data-magic-id]')
      if (blockElement) {
        this.pendingDragId = Number(blockElement.dataset.magicId)
        blockElement.draggable = true
      }
    })
    this.canvas.addEventListener('pointerup', () => {
      if (this.draggingId === null) {
        this.pendingDragId = null
        this.canvas.querySelectorAll('[draggable="true"]').forEach((element) => { element.draggable = false })
      }
    })
    this.canvas.addEventListener('dragstart', (event) => this.startDrag(event))
    this.canvas.addEventListener('dragover', (event) => this.dragOver(event))
    this.canvas.addEventListener('drop', (event) => this.dropBlock(event))
    this.canvas.addEventListener('dragend', () => this.finishDrag())

    const substitutionDialog = document.querySelector('#magic-substitution-dialog')
    const closeSubstitution = () => {
      this.pendingSubstitution = null
      substitutionDialog.close()
    }
    document.querySelector('#magic-substitution-form').addEventListener('submit', (event) => {
      event.preventDefault()
      const alias = document.querySelector('#magic-substitution-alias').value.trim()
      if (!alias || !this.pendingSubstitution) return
      const pending = this.pendingSubstitution
      closeSubstitution()
      this.addAnnotation(pending.blockId, {
        start: pending.start,
        end: pending.end,
        type: 'substitution',
        alias,
      })
    })
    document.querySelector('#magic-substitution-close').addEventListener('click', closeSubstitution)
    document.querySelector('#magic-substitution-cancel').addEventListener('click', closeSubstitution)
    closeDialogOnBackdrop(substitutionDialog, closeSubstitution)
    substitutionDialog.addEventListener('cancel', (event) => {
      if (event.target !== substitutionDialog) return
      event.preventDefault()
      closeSubstitution()
    })
  }

  setVoices(profiles) {
    this.profileIds = new Set(profiles.map((profile) => String(profile.id).toLowerCase()))
    this.voices = profiles.map((profile) => ({
      id: profile.id,
      label: profile.name || profile.id,
      portraitUrl: profile.portrait_url || '',
      version: profile.created_at || 'current',
    }))
    const known = new Set([
      ...this.voices.map((voice) => voice.id),
      ...this.documentMeta.voiceDefinitions.map((definition) => definition.name),
    ])
    for (const block of this.blocks) {
      if (block.type === 'speech' && block.voice && !known.has(block.voice)) {
        this.voices.push({ id: block.voice, label: block.voice, portraitUrl: '', version: 'current' })
        known.add(block.voice)
      }
    }
    this.renderVoiceOptions()
    this.renderBlocks()
    this.syncToolbar()
  }

  setLanguages(languages) {
    this.languages = (languages || []).map((language) => (
      typeof language === 'string' ? { value: language, label: language } : language
    ))
    this.renderLanguageOptions()
    this.syncToolbar()
  }

  setDefaultVoice(profile) {
    const next = profile ? {
      id: profile.id,
      label: profile.name || profile.id,
      portraitUrl: profile.portrait_url || '',
      version: profile.created_at || 'current',
    } : null
    if (next?.id === this.defaultVoice?.id
      && next?.portraitUrl === this.defaultVoice?.portraitUrl
      && next?.version === this.defaultVoice?.version) return
    this.defaultVoice = next
    this.blocks.filter((block) => block.type === 'speech' && !block.voice).forEach((block) => this.invalidateBlock(block))
    this.renderBlocks()
  }

  setCapabilities(capabilities) {
    const elements = new Set(capabilities?.ssml?.elements || [])
    this.supportsVoice = elements.has('voice')
    const directionCapability = capabilities?.ssml_h?.turn_direction
    const directionElements = new Set(directionCapability?.elements || [directionCapability?.element].filter(Boolean))
    this.supportsDirection = Boolean(directionCapability?.supported)
    this.supportsDefaultDirection = this.supportsDirection && directionElements.has('s')
    this.supportsLanguage = elements.has('lang')
    this.supportsProsody = elements.has('prosody')
    this.supportsSubstitution = elements.has('sub')
    this.supportedSayAs = new Set((capabilities?.ssml?.say_as || []).map((mode) => String(mode).split(' ', 1)[0]))
    this.sayAsControl.replaceChildren()
    this.root.querySelector('#magic-add-pause').disabled = !elements.has('break')
    this.maxBreakMs = Number(capabilities?.limits?.break_ms) || this.maxBreakMs
    this.definitionEditor.setCapabilities(capabilities)
    this.root.querySelector('#magic-edit-definitions').hidden = !capabilities?.ssml_h?.voice_definitions_supported
    this.root.querySelector('[data-magic-menu="direction"]').hidden = !this.supportsDirection
    this.expressionControl.closest('label').hidden = true
    this.renderSayAsOptions()
    this.renderBlocks()
    this.syncToolbar()
  }

  loadSample(text) {
    this.blocks.forEach((block) => this.clearPreview(block))
    this.documentMeta = { voiceDefinitions: [], language: '' }
    this.definitionEditor.setDefinitions([])
    this.blocks = [this.createSpeech(text)]
    this.activeId = this.blocks[0].id
    this.render()
    this.resetHistory()
    this.changed({ skipHistory: true })
  }

  newDocument() {
    this.blocks.forEach((block) => this.clearPreview(block))
    this.documentMeta = { voiceDefinitions: [], language: '' }
    this.definitionEditor.setDefinitions([])
    this.blocks = [this.createSpeech('')]
    this.activeId = this.blocks[0].id
    this.render()
    this.resetHistory()
    this.changed({ skipHistory: true })
  }

  loadSSMLH(source, { resetHistory = true, notify = true } = {}) {
    const parsed = parseMagicDocument(source)
    if (parsed.voiceDefinitions.length || parsed.blocks.some((block) => block.direction)) {
      throw new Error(t('magic.unsupportedDesign', {}, 'Kokoro uses pretrained voices. Remove voice definitions and delivery directions, then select a native voice.'))
    }
    this.blocks.forEach((block) => this.clearPreview(block))
    this.documentMeta = { voiceDefinitions: parsed.voiceDefinitions, language: parsed.language }
    this.definitionEditor.setDefinitions(parsed.voiceDefinitions)
    this.blocks = parsed.blocks.map((block) => (
      block.type === 'break'
        ? this.createBreak(block.milliseconds)
        : {
          ...this.createSpeech(block.text),
          annotations: block.annotations,
          voice: block.voice,
          direction: block.direction,
          language: block.language,
          prosody: block.prosody,
        }
    ))
    const known = new Set([
      ...this.voices.map((voice) => voice.id),
      ...parsed.voiceDefinitions.map((definition) => definition.name),
    ])
    for (const block of this.blocks) {
      if (block.type === 'speech' && block.voice && !known.has(block.voice)) {
        this.voices.push({ id: block.voice, label: block.voice, portraitUrl: '', version: 'current' })
        known.add(block.voice)
      }
    }
    this.activeId = this.blocks[0].id
    this.render()
    if (resetHistory) this.resetHistory()
    if (notify) this.changed({ skipHistory: true })
  }

  updateVoiceDefinitions(definitions, detail = {}) {
    this.documentMeta.voiceDefinitions = definitions
    const committed = new Map(Object.entries(detail.committed || {}).map(
      ([sourceName, profileId]) => [sourceName.toLowerCase(), String(profileId)],
    ))
    if (committed.size) {
      for (const block of this.blocks) {
        if (block.type !== 'speech') continue
        const profileId = committed.get(block.voice.toLowerCase())
        if (profileId) block.voice = profileId
      }
    }
    if (detail.removed && !this.voices.some((voice) => voice.id === detail.removed)) {
      for (const block of this.blocks) {
        if (block.type === 'speech' && block.voice === detail.removed) {
          block.voice = ''
          this.invalidateBlock(block)
        }
      }
    }
    this.render()
    this.changed()
  }

  async persistVoiceDefinition(definition, previous, metadata = {}) {
    const sourceName = String(previous?.name || '').toLowerCase()
    const block = this.blocks.find((item) => (
      item.type === 'speech'
      && item.voice.toLowerCase() === sourceName
      && item.preview
    ))
    if (!block) {
      throw new Error(t(
        'magic.definitionGenerateFirst',
        {},
        'Keep this character in the script and generate one of its turns before saving it as a voice.',
      ))
    }
    return this.onPersistCharacter({
      definition: { ...definition },
      previous: { ...previous },
      metadata,
      block,
    })
  }

  selectedRange() {
    const block = this.activeSpeech()
    if (!block) return null
    const textarea = this.canvas.querySelector(`[data-magic-id="${block.id}"] textarea`)
    const start = textarea?.selectionStart
    const end = textarea?.selectionEnd
    if (!Number.isInteger(start) || !Number.isInteger(end) || start === end) {
      this.onError(new Error(t('magic.selectText', {}, 'Select text inside a speech turn first.')))
      return null
    }
    if (!block.text.slice(start, end).trim()) {
      this.onError(new Error(t('magic.selectWords', {}, 'Select one or more visible characters.')))
      return null
    }
    return { block, start, end }
  }

  openSubstitutionDialog() {
    if (!this.supportsSubstitution) return
    const selection = this.selectedRange()
    if (!selection) return
    this.pendingSubstitution = { blockId: selection.block.id, start: selection.start, end: selection.end }
    document.querySelector('#magic-substitution-source').textContent = selection.block.text.slice(selection.start, selection.end)
    const alias = document.querySelector('#magic-substitution-alias')
    alias.value = ''
    document.querySelector('#magic-substitution-dialog').showModal()
    alias.focus()
  }

  applySelectionAnnotation(annotation) {
    const selection = this.selectedRange()
    if (!selection) return
    this.addAnnotation(selection.block.id, { ...annotation, start: selection.start, end: selection.end })
  }

  addAnnotation(blockId, annotation) {
    const block = this.block(blockId)
    if (!block || block.type !== 'speech') return
    const overlaps = block.annotations.some((current) => (
      annotation.start < current.end && annotation.end > current.start
    ))
    if (overlaps) {
      this.onError(new Error(t('magic.overlappingRange', {}, 'Inline pronunciation ranges cannot overlap. Remove the existing range first.')))
      return
    }
    block.annotations.push(annotation)
    block.annotations.sort((left, right) => left.start - right.start)
    this.invalidateBlock(block)
    this.renderBlocks()
    this.changed()
  }

  removeAnnotation(blockId, index) {
    const block = this.block(blockId)
    if (!block || block.type !== 'speech' || !block.annotations[index]) return
    block.annotations.splice(index, 1)
    this.invalidateBlock(block)
    this.renderBlocks()
    this.changed()
  }

  reconcileAnnotations(previousText, nextText, annotations) {
    if (previousText === nextText || !annotations.length) return annotations
    let prefix = 0
    while (prefix < previousText.length && prefix < nextText.length && previousText[prefix] === nextText[prefix]) prefix += 1
    let suffix = 0
    while (
      suffix < previousText.length - prefix
      && suffix < nextText.length - prefix
      && previousText[previousText.length - 1 - suffix] === nextText[nextText.length - 1 - suffix]
    ) suffix += 1
    const previousEnd = previousText.length - suffix
    const delta = nextText.length - previousText.length
    return annotations.flatMap((annotation) => {
      if (annotation.end <= prefix) return [annotation]
      if (annotation.start >= previousEnd) return [{ ...annotation, start: annotation.start + delta, end: annotation.end + delta }]
      return []
    })
  }

  startDrag(event) {
    const element = event.target.closest('[data-magic-id]')
    const id = Number(element?.dataset.magicId)
    if (!element || !Number.isInteger(id) || id !== this.pendingDragId) {
      event.preventDefault()
      return
    }
    this.draggingId = id
    this.pendingDragId = null
    element.classList.add('dragging')
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(this.draggingId))
  }

  dragOver(event) {
    if (this.draggingId === null) return
    const target = event.target.closest('[data-magic-id]')
    if (!target || Number(target.dataset.magicId) === this.draggingId) return
    event.preventDefault()
    this.canvas.querySelectorAll('.drop-before, .drop-after').forEach((element) => element.classList.remove('drop-before', 'drop-after'))
    const after = event.clientY > target.getBoundingClientRect().top + target.getBoundingClientRect().height / 2
    target.classList.add(after ? 'drop-after' : 'drop-before')
  }

  dropBlock(event) {
    if (this.draggingId === null) return
    const target = event.target.closest('[data-magic-id]')
    if (!target) return this.finishDrag()
    event.preventDefault()
    const sourceIndex = this.blocks.findIndex((block) => block.id === this.draggingId)
    let targetIndex = this.blocks.findIndex((block) => block.id === Number(target.dataset.magicId))
    if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return this.finishDrag()
    const after = event.clientY > target.getBoundingClientRect().top + target.getBoundingClientRect().height / 2
    const [moved] = this.blocks.splice(sourceIndex, 1)
    if (sourceIndex < targetIndex) targetIndex -= 1
    this.blocks.splice(targetIndex + (after ? 1 : 0), 0, moved)
    this.activeId = moved.id
    this.finishDrag()
    this.render()
    this.changed()
  }

  finishDrag() {
    this.pendingDragId = null
    this.draggingId = null
    this.canvas.querySelectorAll('[data-magic-id]').forEach((element) => {
      element.draggable = false
      element.classList.remove('dragging', 'drop-before', 'drop-after')
    })
  }

  insertAfterActive(block) {
    const index = Math.max(0, this.blocks.findIndex((item) => item.id === this.activeId))
    this.blocks.splice(index + 1, 0, block)
    this.activeId = block.id
    this.render()
    this.changed()
    this.canvas.querySelector(`[data-magic-id="${block.id}"] textarea`)?.focus()
  }

  async applyBlockAction(id, action, anchor = null) {
    const index = this.blocks.findIndex((item) => item.id === id)
    if (index < 0) return
    const block = this.blocks[index]
    if (action.startsWith('clear-')) {
      if (action === 'clear-voice') {
        block.voice = ''
      } else if (action === 'clear-direction') {
        block.direction = ''
      } else if (action === 'clear-language') {
        block.language = ''
      } else if (['clear-rate', 'clear-pitch', 'clear-volume'].includes(action)) {
        block.prosody[action.slice('clear-'.length)] = ''
      } else {
        return
      }
      this.invalidateBlock(block)
      this.toolbar.close()
      this.render()
      this.changed()
      return
    }
    if (action === 'edit-voice') {
      this.toolbar.open('voice', anchor)
      return
    }
    if (action === 'edit-language') {
      this.toolbar.open('language', anchor)
      return
    }
    if (action === 'edit-direction') {
      const direction = this.blocks[index].direction
      const predefined = DIRECTIONS.some(([value]) => value !== '__custom__' && value === direction)
      this.toolbar.open('direction', anchor, { directionMode: predefined ? 'predefined' : 'custom' })
      return
    }
    if (action === 'edit-transformations') {
      this.toolbar.open('transformations', anchor)
      return
    }
    if (action === 'preview') {
      await this.togglePreview(id)
      return
    }
    if (action === 'regenerate') {
      await this.ensurePreview(id, { play: true, force: true })
      return
    }
    if (action === 'lock') {
      if (!block.preview) return
      block.locked = !block.locked
      this.renderBlocks()
      this.changed({ takesOnly: true })
      return
    }
    if (action === 'download') {
      await this.downloadTake(this.blocks[index], index)
      return
    }
    if (action === 'save-character') {
      await this.onSaveCharacter({ ...this.blocks[index] })
      return
    }
    if (action === 'up' && index > 0) [this.blocks[index - 1], this.blocks[index]] = [this.blocks[index], this.blocks[index - 1]]
    if (action === 'down' && index < this.blocks.length - 1) [this.blocks[index + 1], this.blocks[index]] = [this.blocks[index], this.blocks[index + 1]]
    if (action === 'remove') {
      this.clearPreview(this.blocks[index])
      if (this.blocks.length === 1) {
        this.blocks = [this.createSpeech()]
      } else {
        this.blocks.splice(index, 1)
      }
      this.activeId = this.blocks[Math.min(index, this.blocks.length - 1)].id
    }
    this.render()
    this.changed()
  }

  insertCue(cue) {
    const block = this.activeSpeech()
    if (!block) return
    const textarea = this.canvas.querySelector(`[data-magic-id="${block.id}"] textarea`)
    const start = Number.isInteger(textarea?.selectionStart) ? textarea.selectionStart : block.text.length
    const end = Number.isInteger(textarea?.selectionEnd) ? textarea.selectionEnd : start
    const before = block.text.slice(0, start)
    const after = block.text.slice(end)
    const prefix = before && !/\s$/.test(before) ? ' ' : ''
    const suffix = after && !/^\s/.test(after) ? ' ' : ''
    block.text = `${before}${prefix}${cue}${suffix}${after}`
    this.invalidateBlock(block)
    this.renderBlocks()
    const updated = this.canvas.querySelector(`[data-magic-id="${block.id}"] textarea`)
    const cursor = before.length + prefix.length + cue.length + suffix.length
    updated?.focus()
    updated?.setSelectionRange(cursor, cursor)
    this.updateSummary()
    this.changed()
  }

  clearPreview(block, { unlock = true } = {}) {
    if (!block) return
    if (block.preview && this.playingId === block.id) {
      this.previewAudio.pause()
      this.playingId = null
    }
    if (block.preview?.url) URL.revokeObjectURL(block.preview.url)
    block.preview = null
    if (unlock) block.locked = false
  }

  invalidateBlock(block) {
    this.clearPreview(block)
    block.captureSeed = null
  }

  async ensurePreview(id, { play = false, force = false } = {}) {
    const block = this.block(id)
    if (!block || block.type !== 'speech' || !block.text.trim()) return null
    if (force && block.locked) return block.preview
    if (!block.preview || force) {
      if (this.previewBusyId !== null || this.busy) return null
      this.previewBusyId = id
      this.renderBlocks()
      try {
        const result = await this.onPreview({ ...block })
        if (!result?.blob) return null
        this.clearPreview(block)
        block.preview = { ...result, url: URL.createObjectURL(result.blob) }
        block.captureSeed = Number.isInteger(result.seed) ? result.seed : null
        this.changed({ takesOnly: true, takesChanged: true })
      } finally {
        this.previewBusyId = null
        this.renderBlocks()
      }
    }
    if (play && block.preview) await this.playPreview(block)
    return block.preview
  }

  async downloadTake(block, index) {
    if (!block?.preview) return
    const link = document.createElement('a')
    link.href = block.preview.url
    link.download = `kokorotts-turn-${index + 1}.${block.preview.extension || 'wav'}`
    link.click()
  }

  async togglePreview(id) {
    if (this.playingId === id) {
      this.previewAudio.pause()
      this.playingId = null
      this.renderBlocks()
      return
    }
    const preview = await this.ensurePreview(id)
    const block = this.block(id)
    if (preview && block) await this.playPreview(block)
  }

  async playPreview(block) {
    if (!block.preview) return
    this.previewAudio.pause()
    this.previewAudio.src = block.preview.url
    this.playingId = block.id
    this.renderBlocks()
    try {
      await this.previewAudio.play()
    } catch (error) {
      this.playingId = null
      this.renderBlocks()
      if (error?.name !== 'AbortError') this.onError(error)
    }
  }

  assignVoice(id, voice) {
    const block = this.block(id)
    if (!block || block.type !== 'speech') return
    block.voice = voice
    block.captureSeed = null
    if (block.preview) block.locked = true
    this.activeId = id
    this.render()
    this.changed()
  }

  characterNameExists(name) {
    const normalized = String(name || '').toLowerCase()
    return this.voices.some((voice) => voice.id.toLowerCase() === normalized)
      || this.documentMeta.voiceDefinitions.some((definition) => definition.name.toLowerCase() === normalized)
  }

  profileNameExists(name) {
    return this.profileIds.has(String(name || '').toLowerCase())
  }

  scriptCharacter(name) {
    const normalized = String(name || '').toLowerCase()
    if (!normalized) return null
    return this.documentMeta.voiceDefinitions.find(
      (definition) => definition.name.toLowerCase() === normalized,
    ) || null
  }

  promoteScriptCharacter(sourceName, profileId) {
    if (!sourceName || !profileId) return
    this.adoptCommittedProfiles({ [sourceName]: profileId })
  }

  adoptCommittedProfiles(profiles) {
    const committed = new Map(Object.entries(profiles || {}).map(
      ([sourceName, profileId]) => [sourceName.toLowerCase(), String(profileId)],
    ))
    if (!committed.size) return
    this.documentMeta.voiceDefinitions = this.documentMeta.voiceDefinitions.filter(
      (definition) => !committed.has(definition.name.toLowerCase()),
    )
    this.definitionEditor.setDefinitions(this.documentMeta.voiceDefinitions)
    for (const block of this.blocks) {
      const profileId = block.type === 'speech' ? committed.get(block.voice.toLowerCase()) : null
      if (profileId) block.voice = profileId
    }
    this.render()
    this.changed()
  }

  addScriptCharacter(id, definition) {
    const block = this.block(id)
    if (!block || block.type !== 'speech') return
    if (this.characterNameExists(definition.name)) {
      throw new Error(t('magic.characterExists', { name: definition.name }, `Character ${definition.name} already exists.`))
    }
    this.documentMeta.voiceDefinitions.push({ ...definition, scope: 'request', replace: false })
    this.definitionEditor.setDefinitions(this.documentMeta.voiceDefinitions)
    block.voice = definition.name
    block.captureSeed = null
    if (block.preview) block.locked = true
    this.activeId = id
    this.render()
    this.changed()
  }

  markFullGeneration(seed) {
    if (!Number.isInteger(seed)) return
    let speechIndex = 0
    for (const block of this.blocks) {
      if (block.type !== 'speech' || !block.text.trim()) {
        continue
      }
      if (!block.preview) block.captureSeed = (seed + speechIndex) % (2 ** 32)
      speechIndex += 1
    }
    this.renderBlocks()
  }

  setBusy(busy) {
    if (this.busy === busy) return
    this.busy = busy
    this.renderBlocks()
  }

  speechBlocks() {
    return this.blocks.filter((block) => block.type === 'speech' && block.text.trim())
  }

  hasCompleteTakes() {
    const speech = this.speechBlocks()
    return speech.length > 0 && speech.every((block) => block.preview)
  }

  applyTakes(takes, { notify = false } = {}) {
    for (const block of this.speechBlocks()) {
      const take = takes.get(String(block.id))
      if (!take?.blob) continue
      const locked = block.locked
      this.clearPreview(block)
      block.locked = locked
      block.preview = { ...take, url: URL.createObjectURL(take.blob) }
      block.captureSeed = Number.isInteger(take.seed) ? take.seed : null
    }
    this.renderBlocks()
    if (notify) this.changed({ takesOnly: true, takesChanged: true })
  }

  workspaceTakes() {
    return this.speechBlocks().flatMap((block, speechIndex) => (
      block.preview?.blob
        ? [{
            speechIndex,
            blob: block.preview.blob,
            extension: block.preview.extension || 'wav',
            seed: Number.isInteger(block.captureSeed) ? block.captureSeed : 0,
            locked: Boolean(block.locked),
          }]
        : []
    ))
  }

  restoreWorkspaceTakes(takes = [], { notify = true } = {}) {
    const speech = this.speechBlocks()
    for (const item of takes) {
      const block = speech[Number(item.speechIndex ?? item.speech_index)]
      if (!block || !item.blob) continue
      this.clearPreview(block)
      block.preview = {
        blob: item.blob,
        extension: item.extension || 'wav',
        seed: Number(item.seed) || 0,
        url: URL.createObjectURL(item.blob),
      }
      block.captureSeed = Number.isInteger(item.seed) ? item.seed : Number(item.seed) || 0
      block.locked = Boolean(item.locked)
    }
    this.renderBlocks()
    if (notify) this.changed({ takesOnly: true, takesChanged: true })
  }

  activate(id) {
    if (this.activeId === id) return
    this.toolbar.close()
    this.activeId = id
    this.canvas.querySelectorAll('[data-magic-id]').forEach((element) => {
      element.classList.toggle('active', Number(element.dataset.magicId) === id)
    })
    this.syncToolbar()
  }

  block(id) {
    return this.blocks.find((item) => item.id === id)
  }

  activeSpeech() {
    const block = this.block(this.activeId)
    return block?.type === 'speech' ? block : null
  }

  render() {
    this.renderVoiceOptions()
    this.renderLanguageOptions()
    this.renderDirectionOptions()
    this.renderProsodyOptions()
    this.renderExpressionOptions()
    this.renderSayAsOptions()
    this.renderBlocks()
    this.syncToolbar()
    this.updateSummary()
    this.root.querySelector('#magic-definition-count').textContent = String(this.documentMeta.voiceDefinitions.length)
  }

  relocalize() {
    this.toolbar.close()
    for (const control of [this.directionControl, this.rateControl, this.pitchControl,
      this.volumeControl, this.expressionControl, this.sayAsControl]) control.replaceChildren()
    this.render()
    this.definitionEditor.renderList()
  }

  renderVoiceOptions() {
    const selected = this.voiceControl.value
    const dynamic = this.documentMeta.voiceDefinitions.map((definition) => ({
      id: definition.name,
      label: t('magic.scriptCharacter', { name: definition.name }, `${definition.name} (script)`),
    }))
    const known = new Set(dynamic.map((voice) => voice.id))
    const options = [
      { id: '', label: t('magic.defaultVoice', {}, 'Default voice') },
      ...dynamic,
      ...this.voices.filter((voice) => !known.has(voice.id)),
    ]
    this.voiceControl.replaceChildren(...options.map((voice) => {
      const option = document.createElement('option')
      option.value = voice.id
      option.textContent = voice.label
      return option
    }))
    if (options.some((voice) => voice.id === selected)) this.voiceControl.value = selected
    this.toolbar.refreshOptions('voice', options.map((voice) => ({
      value: voice.id,
      label: voice.label,
      portraitUrl: voice.portraitUrl || '',
      version: voice.version || '',
    })))
  }

  renderLanguageOptions() {
    const selected = this.languageControl.value
    const options = [
      { value: '', label: t('magic.languageInherit', {}, 'Document language') },
      ...this.languages.map(item => ({ ...item, label: languageLabel(item.value) })),
    ]
    this.languageControl.replaceChildren(...options.map((language) => {
      const option = document.createElement('option')
      option.value = language.value
      option.textContent = language.label
      return option
    }))
    if (options.some((language) => language.value === selected)) this.languageControl.value = selected
    this.toolbar.refreshOptions('language', options)
  }

  renderDirectionOptions() {
    if (this.directionControl.options.length) return
    this.directionControl.replaceChildren(...DIRECTIONS.map(([value, key, fallback]) => {
      const option = document.createElement('option')
      option.value = value
      option.textContent = t(key, {}, fallback)
      return option
    }))
    this.toolbar.refreshOptions('direction', DIRECTIONS
      .filter(([value]) => value !== '__custom__')
      .map(([value, key, fallback]) => ({ value, label: t(key, {}, fallback) })))
  }

  renderProsodyOptions() {
    for (const [name, control] of [
      ['rate', this.rateControl], ['pitch', this.pitchControl], ['volume', this.volumeControl],
    ]) {
      if (control.options.length) continue
      control.replaceChildren(...PROSODY_OPTIONS[name].map(([value, key, fallback]) => {
        const option = document.createElement('option')
        option.value = value
        option.textContent = t(key, {}, fallback)
        return option
      }))
    }
  }

  renderExpressionOptions() {
    if (this.expressionControl.options.length) return
    this.expressionControl.replaceChildren(...EXPRESSIVE_CUES.map(([value, key, fallback]) => {
      const option = document.createElement('option')
      option.value = value
      option.textContent = t(key, {}, fallback)
      return option
    }))
  }

  renderSayAsOptions() {
    if (this.sayAsControl.options.length) return
    this.sayAsControl.replaceChildren(...SAY_AS_MODES.map(([value, key, fallback]) => {
      const option = document.createElement('option')
      option.value = value
      option.textContent = t(key, {}, fallback)
      if (value) option.disabled = !this.supportedSayAs.has(value)
      return option
    }))
  }

  renderBlocks() {
    const activeElement = document.activeElement
    const activeId = Number(activeElement?.closest?.('[data-magic-id]')?.dataset.magicId)
    const selectionStart = activeElement?.selectionStart
    const selectionEnd = activeElement?.selectionEnd
    this.canvas.replaceChildren(...this.blocks.map((block, index) => (
      block.type === 'break' ? this.renderBreak(block, index) : this.renderSpeech(block, index)
    )))
    if (activeId) {
      const restored = this.canvas.querySelector(`[data-magic-id="${activeId}"] textarea`)
      if (restored) {
        restored.focus()
        if (Number.isInteger(selectionStart)) restored.setSelectionRange(selectionStart, selectionEnd)
      }
    }
  }

  renderSpeech(block, index) {
    const article = document.createElement('article')
    article.className = `magic-turn${block.id === this.activeId ? ' active' : ''}${block.locked ? ' locked' : ''}`
    article.dataset.magicId = String(block.id)

    const heading = document.createElement('div')
    heading.className = 'magic-block-heading'
    const metadata = document.createElement('div')
    metadata.className = 'magic-turn-metadata'
    const voice = block.voice
      ? removableChip(
        'voice',
        block.voice,
        'edit-voice',
        'clear-voice',
        t('magic.editVoice', {}, 'Change voice'),
        t('magic.removeVoice', {}, 'Remove voice'),
      )
      : chip(
        'voice',
        t('magic.defaultVoice', {}, 'Default voice'),
        'edit-voice',
        t('magic.editVoice', {}, 'Change voice'),
      )
    voice.querySelector?.('.magic-chip')?.toggleAttribute('disabled', !this.supportsVoice)
    if (voice.matches('button')) voice.disabled = !this.supportsVoice
    metadata.append(voice)
    if (block.locked) {
      const locked = document.createElement('span')
      locked.className = 'magic-chip locked'
      const lockedIcon = document.createElement('i')
      lockedIcon.className = 'icon-lock'
      locked.append(lockedIcon, t('magic.takeLocked', {}, 'Locked take'))
      metadata.append(locked)
    }
    if (block.direction) {
      const direction = removableChip(
        'direction',
        block.direction,
        'edit-direction',
        'clear-direction',
        t('magic.editDirection', {}, 'Change direction'),
        t('magic.removeDirection', {}, 'Remove direction'),
      )
      direction.querySelector('.magic-chip').disabled = !this.supportsDirection
      metadata.append(direction)
    } else if (this.supportsDirection && (block.voice || this.supportsDefaultDirection)) {
      const direction = chip(
        'direction add',
        '+',
        'edit-direction',
        t('magic.addDirection', {}, 'Add direction'),
      )
      metadata.append(direction)
    }
    if (block.language) {
      const language = removableChip(
        'language',
        block.language,
        'edit-language',
        'clear-language',
        t('magic.editLanguage', {}, 'Change language'),
        t('magic.removeLanguage', {}, 'Remove language'),
      )
      language.querySelector('.magic-chip').disabled = !this.supportsLanguage
      metadata.append(language)
    }
    const prosodyValues = Object.entries(block.prosody || {}).filter(([, value]) => value)
    for (const [name, value] of prosodyValues) {
      const prosody = removableChip(
        'prosody',
        `${t(`magic.${name}`, {}, name)}: ${value}`,
        'edit-transformations',
        `clear-${name}`,
        t('magic.editTransformations', {}, 'Change transformations'),
        t('magic.removeTransformation', { name: t(`magic.${name}`, {}, name) }, `Remove ${name}`),
      )
      prosody.querySelector('.magic-chip').disabled = !this.supportsProsody
      metadata.append(prosody)
    }
    const actions = document.createElement('div')
    actions.className = 'magic-block-actions'
    const previewing = this.previewBusyId === block.id
    const playing = this.playingId === block.id
    const preview = button(
      previewing ? 'icon-refresh-cw' : playing ? 'icon-pause' : 'icon-play',
      previewing
        ? t('magic.previewGenerating', {}, 'Generating turn preview')
        : playing
          ? t('magic.previewPause', {}, 'Pause turn preview')
          : block.preview
            ? t('magic.previewPlay', {}, 'Play turn preview')
            : t('magic.previewGenerate', {}, 'Generate this turn'),
      'preview',
    )
    preview.classList.add('magic-preview-action')
    preview.classList.toggle('ready', Boolean(block.preview))
    preview.classList.toggle('loading', previewing)
    preview.disabled = this.busy || !block.text.trim() || (this.previewBusyId !== null && !previewing)
    const regenerate = button('icon-refresh-cw', t('magic.regenerateTake', {}, 'Regenerate this turn'), 'regenerate')
    regenerate.disabled = this.busy || previewing || !block.preview || block.locked
    const lock = button(
      block.locked ? 'icon-lock' : 'icon-lock-open',
      block.locked
        ? t('magic.unlockTake', {}, 'Unlock this take')
        : t('magic.lockTake', {}, 'Lock this take'),
      'lock',
    )
    lock.classList.toggle('active', block.locked)
    lock.disabled = this.busy || previewing || !block.preview
    lock.setAttribute('aria-pressed', String(block.locked))
    const download = button('icon-download', t('magic.downloadTake', {}, 'Download this take'), 'download')
    download.disabled = !block.preview
    const moveUp = button('icon-chevron-up', t('magic.moveUp', {}, 'Move turn up'), 'up')
    const moveDown = button('icon-chevron-down', t('magic.moveDown', {}, 'Move turn down'), 'down')
    moveUp.disabled = this.busy || index === 0
    moveDown.disabled = this.busy || index === this.blocks.length - 1
    const remove = button('icon-x', t('magic.remove', {}, 'Remove block'), 'remove')
    remove.disabled = this.busy
    actions.append(
      dragHandle(t('magic.drag', {}, 'Drag to reorder')),
      preview,
      regenerate,
      lock,
      download,
      moveUp,
      moveDown,
      remove,
    )
    actions.firstElementChild.disabled = this.busy
    heading.append(metadata, actions)

    const textarea = document.createElement('textarea')
    textarea.rows = 2
    textarea.value = block.text
    textarea.placeholder = t('magic.turnPlaceholder', {}, 'Write this turn...')
    textarea.setAttribute('aria-label', t('magic.turnLabel', { number: index + 1 }, `Speech turn ${index + 1}`))
    const content = document.createElement('div')
    content.className = 'magic-turn-content'
    const editor = document.createElement('div')
    editor.className = 'magic-turn-editor'
    editor.append(textarea)
    if (block.annotations.length) editor.append(this.renderAnnotations(block))
    content.append(this.renderPortrait(block), editor)
    article.append(heading, content)
    return article
  }

  renderAnnotations(block) {
    const list = document.createElement('div')
    list.className = 'magic-inline-ranges'
    block.annotations.forEach((annotation, index) => {
      const chip = document.createElement('span')
      chip.className = `magic-inline-chip ${annotation.type}`
      const source = block.text.slice(annotation.start, annotation.end)
      const label = document.createElement('span')
      label.textContent = annotation.type === 'substitution'
        ? `${source} -> ${annotation.alias}`
        : `${source} · ${annotation.interpretAs}`
      const remove = document.createElement('button')
      remove.type = 'button'
      remove.dataset.magicAnnotation = String(index)
      remove.title = t('magic.removeInline', {}, 'Remove inline control')
      remove.setAttribute('aria-label', remove.title)
      const icon = document.createElement('i')
      icon.className = 'icon-x'
      remove.append(icon)
      chip.append(label, remove)
      list.append(chip)
    })
    return list
  }

  renderPortrait(block) {
    const voice = block.voice
      ? this.voices.find((item) => item.id === block.voice)
      : this.defaultVoice
    const portrait = document.createElement(voice ? 'div' : 'button')
    portrait.className = 'magic-turn-portrait'
    if (voice) {
      portrait.title = voice.label
      if (voice.portraitUrl) {
        const image = document.createElement('img')
        image.src = `${voice.portraitUrl}?v=${encodeURIComponent(voice.version)}`
        image.alt = t('profiles.portraitAlt', { name: voice.label }, `${voice.label} portrait`)
        image.loading = 'lazy'
        portrait.append(image)
      } else {
        const placeholder = document.createElement('span')
        placeholder.textContent = (voice.label || voice.id).replace(/^\w{2}_/, '').slice(0, 2).toUpperCase()
        placeholder.setAttribute('aria-hidden', 'true')
        portrait.append(placeholder)
      }
      return portrait
    }

    portrait.type = 'button'
    portrait.dataset.magicAction = 'save-character'
    const canSave = Boolean(block.preview || Number.isInteger(block.captureSeed))
    portrait.disabled = !canSave || this.previewBusyId !== null
    portrait.classList.toggle('ready', canSave)
    portrait.title = canSave
      ? t('magic.saveCharacter', {}, 'Save this generated voice as a character')
      : t('magic.previewToSave', {}, 'Generate this turn before saving its voice')
    portrait.setAttribute('aria-label', portrait.title)
    const plus = document.createElement('span')
    plus.textContent = '+'
    plus.setAttribute('aria-hidden', 'true')
    portrait.append(plus)
    return portrait
  }

  renderBreak(block, index) {
    const element = document.createElement('div')
    element.className = `magic-pause${block.id === this.activeId ? ' active' : ''}`
    element.dataset.magicId = String(block.id)
    const line = document.createElement('span')
    line.className = 'magic-pause-line'
    const label = document.createElement('label')
    label.append(document.createTextNode(t('magic.pause', {}, 'Pause')))
    const input = document.createElement('input')
    input.type = 'number'
    input.min = '0'
    input.max = String(this.maxBreakMs)
    input.step = '50'
    input.value = String(block.milliseconds)
    input.setAttribute('aria-label', t('magic.pauseDuration', {}, 'Pause duration in milliseconds'))
    const unit = document.createElement('span')
    unit.textContent = 'ms'
    const actions = document.createElement('div')
    actions.className = 'magic-block-actions'
    actions.append(
      dragHandle(t('magic.drag', {}, 'Drag to reorder')),
      button('icon-chevron-up', t('magic.moveUp', {}, 'Move turn up'), 'up'),
      button('icon-chevron-down', t('magic.moveDown', {}, 'Move turn down'), 'down'),
      button('icon-x', t('magic.remove', {}, 'Remove block'), 'remove'),
    )
    actions.children[1].disabled = index === 0
    actions.children[2].disabled = index === this.blocks.length - 1
    element.append(line, label, input, unit, actions)
    return element
  }

  syncToolbar() {
    const block = this.activeSpeech()
    this.voiceControl.disabled = !block || !this.supportsVoice
    this.languageControl.disabled = !block || !this.supportsLanguage
    this.directionControl.disabled = !block
      || !this.supportsDirection
      || (!block.voice && !this.supportsDefaultDirection)
    this.expressionControl.disabled = !block
    this.rateControl.disabled = !block || !this.supportsProsody
    this.pitchControl.disabled = !block || !this.supportsProsody
    this.volumeControl.disabled = !block || !this.supportsProsody
    this.sayAsControl.disabled = !block || !this.supportedSayAs.size
    this.root.querySelector('#magic-add-substitution').disabled = !block || !this.supportsSubstitution
    const turnReason = !block
      ? t('magic.controlNeedsTurn', {}, 'Select a dialogue turn to use this control')
      : ''
    this.toolbar.setDisabled(
      'voice',
      !block || !this.supportsVoice,
      turnReason || t('magic.voiceUnavailable', {}, 'Voice selection is unavailable for this backend'),
    )
    this.toolbar.setDisabled(
      'language',
      !block || !this.supportsLanguage,
      turnReason || t('magic.languageUnavailable', {}, 'Language control is unavailable for this backend'),
    )
    const directionReason = !block
      ? t('magic.directionNeedsTurn', {}, 'Select a dialogue turn before adding direction')
      : !this.supportsDirection
        ? t('magic.directionUnavailable', {}, 'Direction controls are unavailable for this backend')
        : !block.voice && !this.supportsDefaultDirection
          ? t('magic.directionNeedsVoice', {}, 'This backend requires a named character before adding direction')
          : ''
    this.toolbar.setDisabled('direction', Boolean(directionReason), directionReason)
    this.toolbar.setDisabled(
      'transformations',
      !block || !this.supportsProsody,
      turnReason || t('magic.prosodyUnavailable', {}, 'Prosody controls are unavailable for this backend'),
    )
    this.toolbar.setDisabled('expression', !block, turnReason)
    if (!block) {
      this.toolbar.sync()
      return
    }
    this.voiceControl.value = block.voice
    this.languageControl.value = block.language
    this.rateControl.value = block.prosody.rate
    this.pitchControl.value = block.prosody.pitch
    this.volumeControl.value = block.prosody.volume
    const predefined = DIRECTIONS.some(([value]) => value === block.direction)
    this.directionControl.value = predefined ? block.direction : '__custom__'
    this.customDirection.value = predefined ? '' : block.direction
    this.toolbar.sync()
  }

  plainText() {
    return this.blocks
      .filter((block) => block.type === 'speech')
      .map((block) => block.text.trim())
      .filter(Boolean)
      .join('\n')
  }

  stats() {
    const text = this.plainText()
    return {
      characters: text.length,
      words: text ? text.split(/\s+/).length : 0,
      turns: this.blocks.filter((block) => block.type === 'speech' && block.text.trim()).length,
    }
  }

  updateSummary() {
    const stats = this.stats()
    this.summary.textContent = t('magic.summary', { turns: stats.turns }, `${stats.turns} turns`)
  }

  changed(detail = {}) {
    if (!detail.takesOnly && !detail.skipHistory && !this.restoringHistory) this.recordHistory()
    this.onChange(this, detail)
  }

  resetHistory() {
    this.history = [this.toSSMLH()]
    this.historyIndex = 0
    this.onHistoryChange({ canUndo: false, canRedo: false })
  }

  recordHistory() {
    const snapshot = this.toSSMLH()
    if (snapshot === this.history[this.historyIndex]) return
    this.history.splice(this.historyIndex + 1)
    this.history.push(snapshot)
    if (this.history.length > this.historyLimit) this.history.shift()
    this.historyIndex = this.history.length - 1
    this.onHistoryChange({ canUndo: this.historyIndex > 0, canRedo: false })
  }

  restoreHistory(index) {
    if (index < 0 || index >= this.history.length || index === this.historyIndex) return
    this.restoringHistory = true
    try {
      this.loadSSMLH(this.history[index], { resetHistory: false, notify: false })
      this.historyIndex = index
    } finally {
      this.restoringHistory = false
    }
    this.onHistoryChange({ canUndo: this.historyIndex > 0, canRedo: this.historyIndex < this.history.length - 1 })
    this.changed({ skipHistory: true, historyOnly: true })
  }

  undoDialogue() {
    this.restoreHistory(this.historyIndex - 1)
  }

  redoDialogue() {
    this.restoreHistory(this.historyIndex + 1)
  }

  toSSMLH(blocks = this.blocks, { preview = false } = {}) {
    if (!preview) return serializeMagicDocument(blocks, this.documentMeta)
    const usedVoices = new Set(blocks.filter((block) => block.type === 'speech').map((block) => block.voice).filter(Boolean))
    const voiceDefinitions = this.documentMeta.voiceDefinitions
      .filter((definition) => usedVoices.has(definition.name))
      .map((definition) => ({ ...definition, scope: 'request', replace: false }))
    return serializeMagicDocument(blocks, { ...this.documentMeta, voiceDefinitions })
  }

  spokenText(block) {
    return renderedSpeechText(block)
  }
}
