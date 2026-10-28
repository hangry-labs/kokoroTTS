import { msg } from './i18n.js'
import { t } from './i18n.js'
import { closeDialogOnBackdrop } from './dialog-utils.js?v=pointerdown-v1'
import { serializeMagicDocument } from './magic-document.js'

const $ = (selector, root = document) => root.querySelector(selector)
const COLLAPSED_FOLDERS_KEY = 'kokorotts.script-folders.collapsed'

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function normalizedName(value) {
  return value.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^[-_]+|[-_]+$/g, '').slice(0, 80)
}

function tags(value) {
  return [...new Set(value.split(',').map((tag) => tag.trim().toLowerCase()).filter(Boolean))]
}

function downloadDocument(documentText, filename) {
  const url = URL.createObjectURL(new Blob([documentText], { type: 'application/ssml+xml;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

function readCollapsedFolders() {
  try {
    const values = JSON.parse(localStorage.getItem(COLLAPSED_FOLDERS_KEY) || '[]')
    return new Set(Array.isArray(values) ? values.map(String) : [])
  } catch {
    return new Set()
  }
}

export class DialogueScriptLibrary {
  constructor({
    magicEditor, fetchJson, showToast, errorMessage, getInputType, setInputType,
    onDocumentChange, captureWorkspace, restoreWorkspace, clearWorkspace,
  }) {
    this.magicEditor = magicEditor
    this.fetchJson = fetchJson
    this.showToast = showToast
    this.errorMessage = errorMessage
    this.getInputType = getInputType
    this.setInputType = setInputType
    this.onDocumentChange = onDocumentChange
    this.captureWorkspace = captureWorkspace || (() => ({}))
    this.restoreWorkspace = restoreWorkspace || (async () => {})
    this.clearWorkspace = clearWorkspace || (() => {})
    this.scripts = []
    this.folders = []
    this.active = null
    this.dirty = false
    this.pendingDelete = null
    this.editingDetails = null
    this.suppressDirty = false
    this.draggingScriptId = null
    this.collapsedFolders = readCollapsedFolders()
    this.bindEvents()
  }

  initialize(scripts, folders = []) {
    this.scripts = scripts
    this.folders = folders
    this.render()
  }

  markDirty() {
    if (this.suppressDirty || !this.active) return
    this.dirty = true
    this.render()
  }

  runWithoutDirty(callback) {
    this.suppressDirty = true
    try { return callback() } finally { this.suppressDirty = false }
  }

  renderSaveState() {
    $('#script-save').hidden = !normalizedName($('#script-name').value)
    $('span', $('#script-save')).textContent = t('scripts.saveShort', {}, 'Save')
  }

  card(script) {
    const active = script.id === this.active?.id
    return `
      <article class="script-card${active ? ' active' : ''}" data-script-id="${escapeHtml(script.id)}" draggable="true">
        <div class="script-card-copy">
          <strong>${escapeHtml(script.name)}${active && this.dirty ? `<span class="script-dirty-badge">${escapeHtml(t('scripts.unsaved', {}, 'Unsaved changes'))}</span>` : ''}</strong>
          <span>${escapeHtml(script.description || t('scripts.storedDialogue', {}, 'Stored SSML-H dialogue'))}</span>
          <div class="script-card-metadata">
            <span>${escapeHtml(t('scripts.turnCount', { count: script.turns }, `${script.turns} turns`))}</span>
            <span>${escapeHtml(t('scripts.wordCount', { count: script.words }, `${script.words} words`))}</span>
            ${script.generated_takes ? `<span>${escapeHtml(t('scripts.savedTakes', { count: script.generated_takes }, `${script.generated_takes} saved takes`))}</span>` : ''}
            ${(script.tags || []).map((tag) => `<span>#${escapeHtml(tag)}</span>`).join('')}
          </div>
        </div>
        <div class="script-card-actions">
          <button class="secondary-button" type="button" data-script-action="use" ${active ? 'disabled' : ''}>${active ? `<i class="icon-check"></i><span>${escapeHtml(t('scripts.loadedShort', {}, 'Loaded'))}</span>` : `<i class="icon-book-open"></i><span>${escapeHtml(t('scripts.load', {}, 'Load script'))}</span>`}</button>
          <button class="icon-button bordered" type="button" data-script-action="edit" title="${escapeHtml(t('scripts.editNamed', { name: script.name }, `Edit ${script.name}`))}" aria-label="${escapeHtml(t('scripts.editNamed', { name: script.name }, `Edit ${script.name}`))}"><i class="icon-sliders-horizontal"></i></button>
          <button class="icon-button bordered danger-icon" type="button" data-script-action="delete" title="${escapeHtml(t('common.delete', {}, 'Delete'))}" aria-label="${escapeHtml(t('scripts.deleteNamed', { name: script.name }, `Delete ${script.name}`))}"><i class="icon-x"></i></button>
        </div>
      </article>`
  }

  folder(folder, scripts, query) {
    const folderId = folder?.id || ''
    const collapsed = !query && this.collapsedFolders.has(folderId || '__ungrouped__')
    const title = folder?.name || t('scripts.ungrouped', {}, 'Ungrouped')
    return `
      <section class="script-folder${collapsed ? ' collapsed' : ''}" data-script-folder="${escapeHtml(folderId)}">
        <header class="script-folder-heading">
          <button type="button" data-folder-action="toggle" aria-expanded="${String(!collapsed)}"><span class="script-folder-chevron" aria-hidden="true">›</span><strong>${escapeHtml(title)}</strong><span>${scripts.length}</span></button>
          ${folder ? `<button class="icon-button" type="button" data-folder-action="delete" title="${escapeHtml(t('scripts.deleteFolder', {}, 'Delete folder'))}" aria-label="${escapeHtml(t('scripts.deleteFolderNamed', { name: folder.name }, `Delete folder ${folder.name}`))}"><i class="icon-x"></i></button>` : ''}
        </header>
        <div class="script-folder-items"${collapsed ? ' hidden' : ''}>${scripts.length ? scripts.map((script) => this.card(script)).join('') : `<div class="script-folder-empty">${escapeHtml(t('scripts.dropHere', {}, 'Drop scripts here'))}</div>`}</div>
      </section>`
  }

  render() {
    const query = $('#script-filter').value.trim().toLowerCase()
    const matches = (script, folderName = '') => !query || [script.name, script.description || '', folderName, ...(script.tags || [])].join(' ').toLowerCase().includes(query)
    const folders = this.folders.map((folder) => ({
      ...folder,
      scripts: this.scripts.filter((script) => script.folder === folder.id && matches(script, folder.name)),
    }))
    const knownFolders = new Set(this.folders.map((folder) => folder.id))
    const ungrouped = this.scripts.filter((script) => (!script.folder || !knownFolders.has(script.folder)) && matches(script))
    const activeFolder = this.active?.folder || ''
    for (const group of [...folders, { scripts: ungrouped }]) {
      group.scripts.sort((left, right) => left.id === this.active?.id ? -1 : right.id === this.active?.id ? 1 : left.name.localeCompare(right.name))
    }
    folders.sort((left, right) => left.id === activeFolder ? -1 : right.id === activeFolder ? 1 : left.name.localeCompare(right.name))
    const visibleFolders = query ? folders.filter((folder) => folder.scripts.length) : folders
    const groups = visibleFolders.map((folder) => this.folder(folder, folder.scripts, query))
    if (ungrouped.length || (!query && !folders.length)) groups.push(this.folder(null, ungrouped, query))
    $('#script-count').textContent = String(this.scripts.length)
    $('#script-list').innerHTML = groups.length
      ? groups.join('')
      : `<div class="script-empty">${escapeHtml(t(query ? 'scripts.noMatches' : 'scripts.empty', {}, query ? 'No matching scripts.' : 'No saved scripts yet.'))}</div>`
    this.renderSaveState()
  }

  async refresh(selectedId = this.active?.id) {
    const payload = await this.fetchJson('/tts/dialogue-scripts')
    this.scripts = payload.data || []
    this.folders = payload.folders || []
    if (selectedId) this.active = this.scripts.find((script) => script.id === selectedId) || null
    this.render()
  }

  currentDocument() {
    const mode = this.getInputType()
    if (mode === 'text') return serializeMagicDocument([{ type: 'speech', text: $('#text-input').value, prosody: {} }])
    if (mode === 'ssml' || mode === 'ssml-h') {
      const parsed = new DOMParser().parseFromString($('#text-input').value, 'application/xml')
      if (parsed.querySelector('parsererror') || parsed.documentElement.localName !== 'speak') throw new Error(msg('Enter a valid speak document before saving.'))
      if (mode === 'ssml') parsed.documentElement.setAttribute('version', '1.1')
      return new XMLSerializer().serializeToString(parsed)
    }
    return this.magicEditor.toSSMLH()
  }

  download() {
    try {
      const name = this.active?.id || normalizedName($('#script-name').value) || 'kokoro-dialogue'
      downloadDocument(this.getInputType() === 'ssml' ? $('#text-input').value : this.currentDocument(), `${name}.ssml`)
      $('.script-transfer-menu').open = false
    } catch (error) {
      this.showToast(this.errorMessage(error))
    }
  }

  startNew() {
    this.active = null
    this.dirty = false
    $('#script-name').value = ''
    this.clearWorkspace()
    this.setInputType('magic', { syncSsmlH: false })
    this.runWithoutDirty(() => this.magicEditor.newDocument())
    this.onDocumentChange(this.magicEditor.toSSMLH())
    this.render()
    this.magicEditor.canvas.querySelector('textarea')?.focus()
  }

  async fetchAsset(asset) {
    if (!asset?.url) return null
    const response = await fetch(asset.url, { cache: 'no-store' })
    if (!response.ok) throw new Error(msg`Unable to load saved workspace audio (${response.status}).`)
    return { ...asset, blob: await response.blob() }
  }

  async hydrateWorkspace(workspace) {
    if (!workspace) return null
    const takes = await Promise.all((workspace.takes || []).map(async (take) => ({ ...take, blob: (await this.fetchAsset(take))?.blob })))
    return {
      ...workspace,
      takes,
      output: await this.fetchAsset(workspace.output),
      processed: await this.fetchAsset(workspace.processed),
    }
  }

  async load(scriptId) {
    const record = await this.fetchJson(`/tts/dialogue-scripts/${encodeURIComponent(scriptId)}`)
    this.clearWorkspace()
    this.setInputType('magic', { syncSsmlH: false })
    try { this.runWithoutDirty(() => this.magicEditor.loadSSMLH(record.document)) }
    catch {
      this.setInputType('ssml-h', { syncSsmlH: false })
      $('#text-input').value = record.document
    }
    this.active = record
    this.dirty = false
    $('#script-name').value = record.name
    const workspace = await this.hydrateWorkspace(record.workspace)
    if (workspace) await this.restoreWorkspace(workspace)
    this.onDocumentChange(this.magicEditor.toSSMLH())
    this.render()
    this.showToast(t('scripts.loadedNamed', { name: record.name }, `Loaded ${record.name}.`), 'success')
  }

  async persist() {
    if (this.getInputType() === 'ssml') throw new Error(msg('Legacy SSML uses different controls. Export it as SSML, or switch to SSML-H before saving a studio workspace.'))
    const name = $('#script-name').value.trim()
    const scriptId = normalizedName(name)
    if (!scriptId) throw new Error(t('scripts.nameRequired', {}, 'Enter a script name before saving.'))
    const overwrite = scriptId === this.active?.id
    const snapshot = await this.captureWorkspace()
    const workspace = {
      settings: snapshot.settings || {},
      finishing: snapshot.finishing || {},
      takes: (snapshot.takes || []).map((take) => ({ speech_index: take.speechIndex, seed: take.seed, locked: take.locked, extension: take.extension || 'wav' })),
      output: snapshot.output ? { extension: snapshot.output.extension || 'wav' } : null,
      processed: snapshot.processed ? { extension: snapshot.processed.extension || 'wav' } : null,
    }
    const form = new FormData()
    form.append('metadata', JSON.stringify({ name, document: this.currentDocument(), description: this.active?.description || '', tags: this.active?.tags || [], folder: this.active?.folder || '', workspace }))
    ;(snapshot.takes || []).forEach((take, index) => form.append('takes', take.blob, `take-${index}.${take.extension || 'wav'}`))
    if (snapshot.output) form.append('output', snapshot.output.blob, `output.${snapshot.output.extension || 'wav'}`)
    if (snapshot.processed) form.append('processed', snapshot.processed.blob, `processed.${snapshot.processed.extension || 'wav'}`)
    const saved = await this.fetchJson(overwrite ? `/tts/dialogue-workspaces/${encodeURIComponent(this.active.id)}` : '/tts/dialogue-workspaces', { method: overwrite ? 'PUT' : 'POST', body: form })
    this.active = saved
    this.dirty = false
    $('#script-name').value = saved.name
    await this.refresh(saved.id)
    this.showToast(t('scripts.savedWorkspace', { name: saved.name }, `Saved ${saved.name} workspace.`), 'success')
  }

  renderFolderOptions(selected = '') {
    const options = [`<option value="">${escapeHtml(t('scripts.ungrouped', {}, 'Ungrouped'))}</option>`]
    options.push(...this.folders.map((folder) => `<option value="${escapeHtml(folder.id)}"${folder.id === selected ? ' selected' : ''}>${escapeHtml(folder.name)}</option>`))
    $('#edit-script-folder').innerHTML = options.join('')
    $('#edit-script-folder').value = selected || ''
  }

  async openEdit(script) {
    const record = await this.fetchJson(`/tts/dialogue-scripts/${encodeURIComponent(script.id)}`)
    this.editingDetails = record
    $('#edit-script-name').textContent = record.name
    $('#edit-script-tags').value = (record.tags || []).join(', ')
    $('#edit-script-description').value = record.description || ''
    this.renderFolderOptions(record.folder)
    $('#edit-script-dialog').showModal()
  }

  closeEdit() {
    $('#edit-script-dialog').close()
    this.editingDetails = null
  }

  async updateDetails() {
    if (!this.editingDetails) return
    const record = this.editingDetails
    const saved = await this.fetchJson(`/tts/dialogue-scripts/${encodeURIComponent(record.id)}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: record.name, document: record.document, description: $('#edit-script-description').value.trim(), tags: tags($('#edit-script-tags').value), folder: $('#edit-script-folder').value }),
    })
    if (this.active?.id === saved.id) this.active = saved
    this.closeEdit()
    await this.refresh(this.active?.id)
    this.showToast(t('scripts.detailsUpdatedNamed', { name: saved.name }, `Updated ${saved.name} details.`), 'success')
  }

  async import(file) {
    if (!file) return
    if (file.size > 1_000_000) throw new Error(t('scripts.importSize', {}, 'SSML-H scripts must be 1 MB or smaller.'))
    const source = await file.text()
    this.active = null
    this.dirty = false
    this.clearWorkspace()
    this.setInputType('magic', { syncSsmlH: false })
    try { this.runWithoutDirty(() => this.magicEditor.loadSSMLH(source)) }
    catch {
      this.setInputType('ssml-h', { syncSsmlH: false })
      $('#text-input').value = source
    }
    $('#script-name').value = file.name.replace(/\.(ssml|xml)$/i, '').slice(0, 80)
    this.onDocumentChange(this.magicEditor.toSSMLH())
    this.render()
    $('.script-transfer-menu').open = false
    this.showToast(t('scripts.imported', { name: file.name }, `Imported ${file.name}.`), 'success')
  }

  persistCollapsedFolders() {
    try { localStorage.setItem(COLLAPSED_FOLDERS_KEY, JSON.stringify([...this.collapsedFolders])) } catch { /* Optional UI preference. */ }
  }

  toggleFolder(folderId) {
    const key = folderId || '__ungrouped__'
    if (this.collapsedFolders.has(key)) this.collapsedFolders.delete(key)
    else this.collapsedFolders.add(key)
    this.persistCollapsedFolders()
    this.render()
  }

  async createFolder() {
    const name = $('#script-folder-name').value.trim()
    if (!name) return
    await this.fetchJson('/tts/dialogue-script-folders', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })
    $('#script-folder-dialog').close()
    $('#script-folder-name').value = ''
    await this.refresh()
    this.showToast(t('scripts.folderCreated', { name }, `Created folder ${name}.`), 'success')
  }

  async deleteFolder(folderId) {
    const folder = this.folders.find((item) => item.id === folderId)
    if (!folder) return
    await this.fetchJson(`/tts/dialogue-script-folders/${encodeURIComponent(folderId)}`, { method: 'DELETE' })
    this.collapsedFolders.delete(folderId)
    this.persistCollapsedFolders()
    await this.refresh(this.active?.id)
    this.showToast(t('scripts.folderDeleted', { name: folder.name }, `Removed folder ${folder.name}. Scripts moved to Ungrouped.`), 'success')
  }

  async assignFolder(scriptId, folderId) {
    const saved = await this.fetchJson(`/tts/dialogue-scripts/${encodeURIComponent(scriptId)}/folder`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ folder: folderId }) })
    if (this.active?.id === saved.id) this.active = { ...this.active, folder: saved.folder }
    await this.refresh(this.active?.id)
  }

  bindEvents() {
    $('#script-import').addEventListener('click', () => $('#script-import-input').click())
    $('#script-import-input').addEventListener('change', async (event) => {
      const file = event.target.files[0]
      event.target.value = ''
      try { await this.import(file) } catch (error) { this.showToast(this.errorMessage(error)) }
    })
    $('#script-download').addEventListener('click', () => this.download())
    $('#script-new').addEventListener('click', () => this.startNew())
    $('#script-name').addEventListener('input', () => this.renderSaveState())
    $('#script-filter').addEventListener('input', () => this.render())
    $('#script-save').addEventListener('click', (event) => {
      const button = event.currentTarget
      button.disabled = true
      this.persist().catch((error) => this.showToast(this.errorMessage(error))).finally(() => { button.disabled = false })
    })
    $('#script-folder-add').addEventListener('click', () => {
      $('#script-folder-name').value = ''
      $('#script-folder-dialog').showModal()
      $('#script-folder-name').focus()
    })
    $('#script-folder-close').addEventListener('click', () => $('#script-folder-dialog').close())
    $('#script-folder-cancel').addEventListener('click', () => $('#script-folder-dialog').close())
    $('#script-folder-form').addEventListener('submit', (event) => {
      event.preventDefault()
      this.createFolder().catch((error) => this.showToast(this.errorMessage(error)))
    })
    $('#script-list').addEventListener('click', (event) => {
      const folderElement = event.target.closest('[data-script-folder]')
      const folderAction = event.target.closest('[data-folder-action]')?.dataset.folderAction
      if (folderAction === 'toggle') return this.toggleFolder(folderElement?.dataset.scriptFolder || '')
      if (folderAction === 'delete') return this.deleteFolder(folderElement?.dataset.scriptFolder || '').catch((error) => this.showToast(this.errorMessage(error)))
      const action = event.target.closest('[data-script-action]')?.dataset.scriptAction
      const scriptId = event.target.closest('[data-script-id]')?.dataset.scriptId
      const script = this.scripts.find((item) => item.id === scriptId)
      if (!action || !script) return
      if (action === 'use') this.load(scriptId).catch((error) => this.showToast(this.errorMessage(error)))
      if (action === 'edit') this.openEdit(script).catch((error) => this.showToast(this.errorMessage(error)))
      if (action === 'delete') {
        this.pendingDelete = script
        $('#delete-script-name').textContent = script.name
        $('#delete-script-dialog').showModal()
      }
    })
    $('#script-list').addEventListener('dragstart', (event) => {
      const card = event.target.closest('[data-script-id]')
      if (!card) return
      this.draggingScriptId = card.dataset.scriptId
      card.classList.add('dragging')
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/plain', this.draggingScriptId)
    })
    $('#script-list').addEventListener('dragover', (event) => {
      const folder = event.target.closest('[data-script-folder]')
      if (!folder || !this.draggingScriptId) return
      event.preventDefault()
      folder.classList.add('drag-target')
    })
    $('#script-list').addEventListener('dragleave', (event) => event.target.closest('[data-script-folder]')?.classList.remove('drag-target'))
    $('#script-list').addEventListener('drop', (event) => {
      const folder = event.target.closest('[data-script-folder]')
      if (!folder || !this.draggingScriptId) return
      event.preventDefault()
      const scriptId = this.draggingScriptId
      this.draggingScriptId = null
      this.assignFolder(scriptId, folder.dataset.scriptFolder || '').catch((error) => this.showToast(this.errorMessage(error)))
    })
    $('#script-list').addEventListener('dragend', () => {
      this.draggingScriptId = null
      $('#script-list').querySelectorAll('.dragging, .drag-target').forEach((element) => element.classList.remove('dragging', 'drag-target'))
    })
    $('#edit-script-close').addEventListener('click', () => this.closeEdit())
    $('#edit-script-cancel').addEventListener('click', () => this.closeEdit())
    closeDialogOnBackdrop($('#edit-script-dialog'), () => this.closeEdit())
    $('#edit-script-form').addEventListener('submit', (event) => {
      event.preventDefault()
      this.updateDetails().catch((error) => this.showToast(this.errorMessage(error)))
    })
    $('#delete-script-close').addEventListener('click', () => $('#delete-script-dialog').close())
    $('#delete-script-cancel').addEventListener('click', () => $('#delete-script-dialog').close())
    $('#delete-script-confirm').addEventListener('click', async (event) => {
      if (!this.pendingDelete) return
      const script = this.pendingDelete
      const button = event.currentTarget
      button.disabled = true
      try {
        await this.fetchJson(`/tts/dialogue-scripts/${encodeURIComponent(script.id)}`, { method: 'DELETE' })
        $('#delete-script-dialog').close()
        this.pendingDelete = null
        if (this.active?.id === script.id) this.startNew()
        await this.refresh()
        this.showToast(t('scripts.deletedNamed', { name: script.name }, `Deleted ${script.name}.`), 'success')
      } catch (error) {
        this.showToast(this.errorMessage(error))
      } finally {
        button.disabled = false
      }
    })
  }
}
