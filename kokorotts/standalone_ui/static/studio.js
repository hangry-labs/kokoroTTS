import { MagicEditor } from './magic-editor.js'
import { MagicTakeStudio } from './magic-takes.js'
import { DialogueScriptLibrary } from './dialogue-script-library.js'
import { t, languageLabel } from './i18n.js'

const $ = (selector) => document.querySelector(selector)

export async function createStudio({ state, requestPayload, fetchJson, responseError,
  showToast, errorMessage, setInputType, updateTextMetrics, output }) {
  const takes = new MagicTakeStudio({ responseError })
  let library = null
  let abort = null
  let generation = 0
  let outputValid = false
  const disabledBefore = new Map()
  function lockControls(locked) {
    if (locked) {
      for (const control of document.querySelectorAll('.settings-panel input, .settings-panel select, .settings-panel button, .script-toolbar input, .script-toolbar button, .script-library button, [data-input-type], #sample-button, #generate-button, #stream-start, #tokenize-button')) {
        disabledBefore.set(control, control.disabled)
        control.disabled = true
      }
    } else {
      for (const [control, disabled] of disabledBefore) control.disabled = disabled
      disabledBefore.clear()
    }
    $('#magic-editor-shell').inert = locked
    $('#text-input').readOnly = locked
    $('#magic-editor-shell').setAttribute('aria-busy', String(locked))
  }
  const editor = new MagicEditor($('#magic-editor-shell'), {
    onError: (error) => showToast(errorMessage(error)),
    onChange: (_editor, detail = {}) => {
      if (!detail.takesOnly) outputValid = false
      library?.markDirty(); updateTextMetrics(); syncActions()
    },
    onHistoryChange: ({ canUndo, canRedo }) => {
      $('#dialogue-undo').disabled = !canUndo
      $('#dialogue-redo').disabled = !canRedo
    },
    onPreview: async (block) => {
      const revision = generation
      abort = new AbortController()
      $('#generate-stop').hidden = false
      $('#generate-stop').disabled = false
      lockControls(true)
      try {
        const payload = { ...requestPayload('wav'), text: editor.toSSMLH([block], { preview: true }), input_type: 'ssml-h', normalize: false }
        const result = await takes.take(payload, 0, { signal: abort.signal })
        return revision === generation ? result : null
      } finally {
        abort = null
        $('#generate-stop').hidden = true
        $('#generate-stop').disabled = true
        lockControls(false)
      }
    },
  })
  function syncActions() {
    $('#magic-assemble').disabled = !editor.hasCompleteTakes() || editor.busy
    $('#magic-assemble').hidden = state.inputType !== 'magic'
  }
  function syncVoices() {
    if (editor.defaultVoice?.id !== $('#voice').value && editor.blocks.some((block) => block.type === 'speech' && !block.voice)) outputValid = false
    editor.setVoices(state.voices.map((voice) => ({ id: voice.id, name: voice.label || voice.id })))
    editor.setDefaultVoice({ id: $('#voice').value, name: $('#voice').selectedOptions[0]?.textContent })
    editor.setLanguages([...$('#language').options].map((option) => ({ value: option.value, label: languageLabel(option.textContent) })))
  }
  const capabilities = await fetchJson('/tts/ssml/capabilities')
  editor.setCapabilities(capabilities)
  editor.loadSample($('#text-input').value)
  syncVoices()
  $('#voice').addEventListener('change', syncVoices)
  $('#language').addEventListener('change', () => queueMicrotask(syncVoices))
  // Request-wide controls change every take's sound. Never retain an old locked
  // take under new controls, even when the document text itself is unchanged.
  for (const id of ['speed', 'pitch', 'tempo', 'volume', 'normalize', 'device']) {
    const invalidate = () => {
      outputValid = false
      editor.blocks.forEach((block) => editor.invalidateBlock(block))
      editor.renderBlocks()
      library?.markDirty()
      syncActions()
    }
    $(`#${id}`).addEventListener('change', invalidate)
    $(`#${id}-slider`)?.addEventListener('input', invalidate)
    if ($(`#${id}`).type === 'number') $(`#${id}`).addEventListener('input', invalidate)
  }
  $('#reset-voice-controls').addEventListener('click', () => {
    editor.blocks.forEach((block) => editor.invalidateBlock(block)); editor.renderBlocks(); syncActions()
  })
  $('#dialogue-undo').addEventListener('click', () => editor.undoDialogue())
  $('#dialogue-redo').addEventListener('click', () => editor.redoDialogue())
  library = new DialogueScriptLibrary({ magicEditor: editor, fetchJson, showToast, errorMessage,
    getInputType: () => state.inputType,
    setInputType,
    onDocumentChange: () => updateTextMetrics(),
    clearWorkspace: () => { generation++; abort?.abort(); output.clear() },
    captureWorkspace: () => ({ settings: requestPayload(), takes: editor.workspaceTakes(),
      output: outputValid && output.currentFile() ? { blob: output.currentFile(), extension: $('#output-format').value } : null }),
    restoreWorkspace: async (workspace) => {
      const settings = workspace.settings || {}
      for (const [key, id] of Object.entries({ speed: 'speed', pitch_semitones: 'pitch', tempo: 'tempo', volume: 'volume' })) {
        const control = $(`#${id}`)
        if (Number.isFinite(settings[key]) && settings[key] >= Number(control.min) && settings[key] <= Number(control.max)) {
          control.value = settings[key]
          control.dispatchEvent(new Event('input', { bubbles: true }))
        }
      }
      if (state.voices.some((v) => v.id === settings.voice)) {
        $('#language').value = state.voices.find((v) => v.id === settings.voice).language
        // Loading a workspace must not replace the script with a sample.
        const option = document.createElement('option'); option.value = settings.voice; option.textContent = settings.voice
        if (![...$('#voice').options].some((o) => o.value === settings.voice)) $('#voice').append(option)
        $('#voice').value = settings.voice
      }
      $('#normalize').checked = Boolean(settings.normalize)
      $('#normalize').dispatchEvent(new Event('change'))
      syncVoices()
      editor.restoreWorkspaceTakes(workspace.takes || [], { notify: false })
      if (workspace.output?.blob) await output.load(workspace.output.blob, 'kokorotts-dialogue.wav')
      outputValid = Boolean(workspace.output?.blob)
      syncActions()
    },
  })
  const saved = await fetchJson('/tts/dialogue-scripts')
  library.initialize(saved.data, saved.folders)
  syncActions()
  return {
    editor, library, syncVoices,
    markOutput: () => { outputValid = true },
    invalidateOutput: () => { outputValid = false },
    setExternalBusy(busy) { editor.setBusy(busy); lockControls(busy) },
    stop: () => { generation++; abort?.abort() },
    setMode(mode, previous, options = {}) {
      if (editor.busy || editor.previewBusyId !== null) throw new Error(t('magic.waitForGeneration', {}, 'Stop generation before changing the input format.'))
      if (mode === 'magic' && options.syncSsmlH !== false) {
        if (previous === 'ssml-h') editor.loadSSMLH($('#text-input').value)
        else if (previous === 'text') editor.loadSample($('#text-input').value)
        else if (previous === 'ssml') throw new Error(t('magic.legacyImport', {}, 'Legacy SSML has a different prosody format. Use Text or SSML-H before opening Magic; your SSML draft is unchanged.'))
      }
      $('#magic-editor-shell').hidden = mode !== 'magic'
      $('#text-input').hidden = mode === 'magic'
      syncActions()
      $('#magic-assemble').hidden = mode !== 'magic'
    },
    document: () => editor.toSSMLH(),
    async render(payload) {
      abort = new AbortController()
      editor.setBusy(true)
      lockControls(true)
      try {
        const result = await takes.render({ ...payload, input_type: 'ssml-h', text: editor.toSSMLH() }, editor.blocks, { signal: abort.signal })
        editor.applyTakes(result.takes, { notify: true })
        outputValid = true
        return result.output.blob
      } finally { editor.setBusy(false); abort = null; lockControls(false); syncActions() }
    },
    async assemble(payload) {
      abort = new AbortController()
      editor.setBusy(true)
      lockControls(true)
      try {
        const result = await takes.assemble(editor.blocks, { outputFormat: payload.output_format,
          normalizeLoudness: payload.normalize, signal: abort.signal })
        outputValid = true
        return result.blob
      } finally { editor.setBusy(false); abort = null; lockControls(false); syncActions() }
    },
  }
}
