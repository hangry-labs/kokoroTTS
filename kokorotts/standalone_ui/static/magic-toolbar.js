import { t } from './i18n.js'

function optionButton(name, option) {
  const control = document.createElement('button')
  control.type = 'button'
  control.className = 'magic-menu-option'
  control.dataset.magicChoice = name
  control.dataset.value = option.value
  control.dataset.search = option.label.toLocaleLowerCase()
  if (name === 'voice') {
    const portrait = document.createElement('span')
    portrait.className = 'magic-menu-portrait'
    if (option.portraitUrl) {
      const image = document.createElement('img')
      image.src = option.version
        ? `${option.portraitUrl}?v=${encodeURIComponent(option.version)}`
        : option.portraitUrl
      image.alt = ''
      portrait.append(image)
    } else {
      portrait.textContent = option.value ? option.label.replace(/^\w{2}_/, '').slice(0, 2).toUpperCase() : 'A'
    }
    portrait.setAttribute('aria-hidden', 'true')
    control.append(portrait)
  }
  const label = document.createElement('span')
  label.textContent = option.label
  const check = document.createElement('i')
  check.className = 'icon-check'
  check.setAttribute('aria-hidden', 'true')
  control.append(label, check)
  return control
}

export class MagicToolbar {
  constructor(root) {
    this.root = root
    this.openName = null
    this.closeTimer = null
    this.openTimer = null
    this.hoverQuery = window.matchMedia('(hover: hover) and (pointer: fine)')
    this.menus = new Map([...root.querySelectorAll('[data-magic-menu]')].map((menu) => [menu.dataset.magicMenu, {
      wrapper: menu,
      trigger: menu.querySelector('[data-magic-menu-trigger]'),
      panel: menu.querySelector('[data-magic-menu-panel]'),
      label: menu.querySelector('[data-magic-menu-trigger]')?.title || '',
    }]))
    this.bind()
  }

  bind() {
    for (const [name, menu] of this.menus) {
      menu.trigger.addEventListener('click', () => {
        if (this.openName === name) this.close()
        else this.open(name)
      })
      menu.wrapper.addEventListener('pointerenter', () => {
        clearTimeout(this.closeTimer)
        if (!this.hoverQuery.matches || menu.trigger.disabled
          || (this.openName === name && menu.anchor && menu.anchor !== menu.trigger)) return
        clearTimeout(this.openTimer)
        this.openTimer = setTimeout(() => this.open(name), 160)
      })
      menu.wrapper.addEventListener('pointerleave', () => {
        clearTimeout(this.openTimer)
        if (!this.hoverQuery.matches || this.openName !== name || menu.anchor !== menu.trigger) return
        this.closeTimer = setTimeout(() => this.close(), 320)
      })
    }
    this.root.addEventListener('click', (event) => {
      const choice = event.target.closest('[data-magic-choice]')
      if (choice) {
        const name = choice.dataset.magicChoice
        const select = this.root.querySelector(`#magic-${name}-control`)
        select.value = choice.dataset.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
        this.close()
        return
      }
      const mode = event.target.closest('[data-magic-direction-mode]')?.dataset.magicDirectionMode
      if (mode) {
        this.showDirectionDetail(mode)
        const menu = this.menus.get('direction')
        if (this.openName === 'direction' && menu?.anchor) this.anchor(menu.panel, menu.anchor)
      }
    })
    this.root.querySelectorAll('[data-magic-filter]').forEach((input) => {
      input.addEventListener('input', () => this.filter(input.dataset.magicFilter, input.value))
    })
    document.addEventListener('pointerdown', (event) => {
      const menu = this.menus.get(this.openName)
      if (menu && !menu.wrapper.contains(event.target)) this.close()
    })
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && this.openName) {
        const trigger = this.menus.get(this.openName)?.trigger
        this.close()
        trigger?.focus()
      }
    })
    window.addEventListener('resize', () => this.close())
    this.root.querySelector('#magic-editor')?.addEventListener('scroll', () => this.close())
  }

  refreshOptions(name, options) {
    const list = this.root.querySelector(`[data-magic-options="${name}"]`)
    if (!list) return
    list.replaceChildren(...options.map((option) => optionButton(name, option)))
    this.filter(name, this.root.querySelector(`[data-magic-filter="${name}"]`)?.value || '')
    this.sync()
  }

  filter(name, value) {
    const query = value.trim().toLocaleLowerCase()
    this.root.querySelectorAll(`[data-magic-choice="${name}"]`).forEach((option) => {
      option.hidden = Boolean(query) && !option.dataset.search.includes(query)
    })
  }

  open(name, anchor = null, { directionMode = null } = {}) {
    const menu = this.menus.get(name)
    if (!menu || menu.trigger.disabled) return
    clearTimeout(this.closeTimer)
    clearTimeout(this.openTimer)
    this.close({ except: name })
    this.openName = name
    menu.panel.hidden = false
    menu.trigger.classList.add('open')
    menu.trigger.setAttribute('aria-expanded', 'true')
    if (name === 'direction') {
      const currentMode = this.root.querySelector('#magic-direction-control')?.value === '__custom__'
        ? 'custom'
        : 'predefined'
      this.showDirectionDetail(directionMode || currentMode)
    }
    menu.anchor = anchor || menu.trigger
    this.anchor(menu.panel, menu.anchor)
    const filter = menu.panel.querySelector('[data-magic-filter]')
    if (filter) {
      filter.value = ''
      this.filter(filter.dataset.magicFilter, '')
      requestAnimationFrame(() => filter.focus())
    }
  }

  close({ except = null } = {}) {
    for (const [name, menu] of this.menus) {
      if (name === except) continue
      menu.panel.hidden = true
      menu.trigger.classList.remove('open')
      menu.trigger.setAttribute('aria-expanded', 'false')
      this.resetAnchor(menu.panel)
      menu.anchor = null
    }
    if (!except || this.openName !== except) this.openName = except
  }

  anchor(panel, anchor) {
    const rect = anchor.getBoundingClientRect()
    panel.classList.add('card-anchored')
    panel.style.left = '8px'
    panel.style.top = '8px'
    const width = panel.offsetWidth
    const height = panel.offsetHeight
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8))
    const top = rect.bottom + 6 + height <= window.innerHeight
      ? rect.bottom + 6
      : Math.max(8, rect.top - height - 6)
    panel.style.left = `${left}px`
    panel.style.top = `${top}px`
    panel.dataset.flyoutSide = left + width + 250 > window.innerWidth ? 'left' : 'right'
  }

  resetAnchor(panel) {
    panel.classList.remove('card-anchored')
    panel.style.removeProperty('left')
    panel.style.removeProperty('top')
    delete panel.dataset.flyoutSide
  }

  showDirectionDetail(mode) {
    this.root.querySelectorAll('[data-magic-direction-mode]').forEach((button) => {
      button.classList.toggle('active', button.dataset.magicDirectionMode === mode)
    })
    this.root.querySelectorAll('[data-magic-direction-detail]').forEach((detail) => {
      detail.hidden = detail.dataset.magicDirectionDetail !== mode
    })
    if (mode === 'custom') requestAnimationFrame(() => this.root.querySelector('#magic-custom-direction')?.focus())
  }

  setDisabled(name, disabled, reason = '') {
    const menu = this.menus.get(name)
    if (!menu) return
    menu.trigger.disabled = disabled
    menu.wrapper.title = disabled ? reason : ''
    menu.trigger.title = disabled ? reason : menu.label
    menu.trigger.setAttribute('aria-label', disabled && reason ? reason : menu.label)
    if (disabled && this.openName === name) this.close()
  }

  sync() {
    const directionControl = this.root.querySelector('#magic-direction-control')
    const customDirection = this.root.querySelector('#magic-custom-direction')?.value.trim() || ''
    const active = {
      voice: this.root.querySelector('#magic-voice-control')?.value || '',
      language: this.root.querySelector('#magic-language-control')?.value || '',
      direction: directionControl?.value === '__custom__' ? customDirection : directionControl?.value || '',
      transformations: ['rate', 'pitch', 'volume'].some((name) => this.root.querySelector(`#magic-${name}-control`)?.value),
    }
    for (const [name, menu] of this.menus) {
      menu.trigger.classList.toggle('selected', Boolean(active[name]))
      const current = menu.panel.querySelector(`[data-magic-current="${name}"]`)
      if (current) {
        if (name === 'transformations') current.textContent = active.transformations ? t('common.done', {}, 'Done') : ''
        else if (name === 'direction' && directionControl?.value === '__custom__') current.textContent = active.direction
        else {
          const select = this.root.querySelector(`#magic-${name}-control`)
          current.textContent = select?.selectedOptions[0]?.textContent || active[name] || ''
        }
      }
      menu.panel.querySelectorAll(`[data-magic-choice="${name}"]`).forEach((choice) => {
        const selected = choice.dataset.value === (this.root.querySelector(`#magic-${name}-control`)?.value || '')
        choice.classList.toggle('selected', selected)
        choice.setAttribute('aria-pressed', String(selected))
      })
    }
  }
}
