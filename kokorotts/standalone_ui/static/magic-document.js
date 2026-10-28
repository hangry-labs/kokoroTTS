import { msg } from './i18n.js'
const SSML_NAMESPACE = 'http://www.w3.org/2001/10/synthesis'
const SSML_H_NAMESPACE = 'https://hangrylabs.app/ns/ssml-h/1.0'
const XML_NAMESPACE = 'http://www.w3.org/XML/1998/namespace'

const DEFINITION_ATTRIBUTES = [
  'name', 'gender', 'age', 'pitch', 'style', 'languages', 'accent', 'dialect', 'scope', 'replace', 'seed',
]

function escapeXml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;')
}

function xmlAttribute(name, value) {
  if (value === null || value === undefined || value === '') return ''
  return ` ${name}="${escapeXml(value)}"`
}

function normalizedAnnotations(block) {
  const text = String(block.text || '')
  const annotations = Array.isArray(block.annotations) ? block.annotations : []
  return annotations
    .map((annotation) => ({ ...annotation, start: Number(annotation.start), end: Number(annotation.end) }))
    .filter((annotation) => (
      Number.isInteger(annotation.start)
      && Number.isInteger(annotation.end)
      && annotation.start >= 0
      && annotation.end > annotation.start
      && annotation.end <= text.length
      && (annotation.type === 'substitution' || annotation.type === 'say-as')
    ))
    .sort((left, right) => left.start - right.start || left.end - right.end)
}

function serializeRichText(block) {
  const text = String(block.text || '')
  const annotations = normalizedAnnotations(block)
  let cursor = 0
  let output = ''
  for (const annotation of annotations) {
    if (annotation.start < cursor) throw new Error(msg('Magic inline controls cannot overlap.'))
    output += escapeXml(text.slice(cursor, annotation.start))
    const source = escapeXml(text.slice(annotation.start, annotation.end))
    if (annotation.type === 'substitution') {
      if (!String(annotation.alias || '').trim()) throw new Error(msg('Pronunciation substitutions require spoken text.'))
      output += `<sub alias="${escapeXml(String(annotation.alias).trim())}">${source}</sub>`
    } else {
      if (!String(annotation.interpretAs || '').trim()) throw new Error(msg('Say-as ranges require an interpretation.'))
      output += `<say-as interpret-as="${escapeXml(String(annotation.interpretAs).trim())}">${source}</say-as>`
    }
    cursor = annotation.end
  }
  return output + escapeXml(text.slice(cursor))
}

function serializeVoiceDefinitions(definitions) {
  if (!definitions?.length) return ''
  const lines = ['<metadata>', '  <h:extensions version="1.0">']
  for (const definition of definitions) {
    const attributes = DEFINITION_ATTRIBUTES
      .map((name) => xmlAttribute(name, definition[name]))
      .join('')
    const children = []
    if (String(definition.description || '').trim()) {
      children.push(`      <h:description>${escapeXml(String(definition.description).trim())}</h:description>`)
    }
    if (String(definition.sample || '').trim()) {
      children.push(
        `      <h:sample${xmlAttribute('xml:lang', String(definition.sampleLanguage || '').trim())}>${escapeXml(String(definition.sample).trim())}</h:sample>`,
      )
    }
    if (children.length) {
      lines.push(`    <h:voice-definition${attributes}>`, ...children, '    </h:voice-definition>')
    } else {
      lines.push(`    <h:voice-definition${attributes}/>`)
    }
  }
  lines.push('  </h:extensions>', '</metadata>')
  return lines.join('\n')
}

function serializeSpeech(block) {
  let content = serializeRichText(block)
  const prosody = block.prosody || {}
  const prosodyAttributes = ['rate', 'pitch', 'volume']
    .map((name) => xmlAttribute(name, prosody[name]))
    .join('')
  if (prosodyAttributes) content = `<prosody${prosodyAttributes}>${content}</prosody>`
  if (block.language) content = `<lang xml:lang="${escapeXml(block.language)}">${content}</lang>`
  if (block.voice) {
    const direction = block.direction ? ` h:direction="${escapeXml(block.direction)}"` : ''
    return `<voice name="${escapeXml(block.voice)}"${direction}>${content}</voice>`
  }
  const direction = block.direction ? ` h:direction="${escapeXml(block.direction)}"` : ''
  return `<s${direction}>${content}</s>`
}

export function serializeMagicDocument(blocks, options = {}) {
  const body = blocks.map((block) => {
    if (block.type === 'break') return `  <break time="${Math.round(block.milliseconds)}ms"/>`
    if (!String(block.text || '').trim()) return ''
    return `  ${serializeSpeech(block)}`
  }).filter(Boolean)
  const metadata = serializeVoiceDefinitions(options.voiceDefinitions || [])
  if (metadata) body.unshift(...metadata.split('\n').map((line) => `  ${line}`))
  const language = options.language ? ` xml:lang="${escapeXml(options.language)}"` : ''
  return `<speak version="1.1" xmlns="${SSML_NAMESPACE}" xmlns:h="${SSML_H_NAMESPACE}"${language}>\n${body.join('\n')}\n</speak>`
}

function parseBreakTime(value) {
  const match = String(value || '').trim().match(/^(\d+(?:\.\d+)?)(ms|s)$/i)
  if (!match) throw new Error(msg('Magic supports break times written in milliseconds or seconds.'))
  const milliseconds = Number(match[1]) * (match[2].toLowerCase() === 's' ? 1000 : 1)
  if (!Number.isFinite(milliseconds) || milliseconds < 0 || milliseconds > 10_000) {
    throw new Error(msg('Magic supports pauses between 0 and 10000 milliseconds.'))
  }
  return Math.round(milliseconds)
}

function meaningfulNodes(element) {
  return [...element.childNodes].filter((node) => (
    node.nodeType === Node.ELEMENT_NODE
    || (node.nodeType === Node.TEXT_NODE && node.textContent.trim())
  ))
}

function normalizedText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim()
}

function joinText(left, right) {
  if (!left) return right
  if (!right) return left
  const separator = !/\s$/.test(left) && !/^\s/.test(right) && !/^[.,;:!?\)\]\}]/.test(right) ? ' ' : ''
  return `${left}${separator}${right}`
}

function parseInline(element) {
  let text = ''
  const annotations = []
  const append = (value, annotation = null) => {
    const normalized = normalizedText(value)
    if (!normalized) return
    const joined = joinText(text, normalized)
    const start = joined.length - normalized.length
    text = joined
    if (annotation) annotations.push({ ...annotation, start, end: text.length })
  }
  for (const node of element.childNodes) {
    if (node.nodeType === Node.TEXT_NODE) {
      append(node.textContent)
      continue
    }
    if (node.nodeType !== Node.ELEMENT_NODE || node.namespaceURI !== SSML_NAMESPACE) {
      throw new Error(msg('Magic supports only substitution and say-as ranges inside a speech turn.'))
    }
    if ([...node.children].length) throw new Error(msg`Magic does not support nested content inside <${node.localName}>.`)
    if (node.localName === 'sub') {
      const alias = node.getAttribute('alias')?.trim()
      if (!alias) throw new Error(msg('Magic substitutions require a non-empty alias.'))
      append(node.textContent, { type: 'substitution', alias })
      continue
    }
    if (node.localName === 'say-as') {
      const interpretAs = node.getAttribute('interpret-as')?.trim()
      if (!interpretAs) throw new Error(msg('Magic say-as ranges require an interpretation.'))
      append(node.textContent, { type: 'say-as', interpretAs })
      continue
    }
    throw new Error(msg`Magic cannot edit <${node.localName}> inside a speech turn.`)
  }
  return { text, annotations }
}

function peelTurnControls(element) {
  let container = element
  let language = ''
  const prosody = { rate: '', pitch: '', volume: '' }
  if (element.localName === 'lang' || (element.localName === 's' && element.hasAttributeNS(XML_NAMESPACE, 'lang'))) {
    language = element.getAttributeNS(XML_NAMESPACE, 'lang') || ''
    if (!language.trim()) throw new Error(msg('Magic turn language cannot be empty.'))
  }
  if (element.localName === 'prosody') {
    for (const key of ['rate', 'pitch', 'volume']) prosody[key] = element.getAttribute(key) || ''
  }
  while (true) {
    const nodes = meaningfulNodes(container)
    if (nodes.length !== 1 || nodes[0].nodeType !== Node.ELEMENT_NODE) break
    const child = nodes[0]
    if (child.namespaceURI !== SSML_NAMESPACE) break
    if (child.localName === 'lang') {
      if (language) throw new Error(msg('Magic supports one language control per turn.'))
      language = child.getAttributeNS(XML_NAMESPACE, 'lang') || child.getAttribute('xml:lang') || ''
      if (!language.trim()) throw new Error(msg('Magic turn language cannot be empty.'))
      container = child
      continue
    }
    if (child.localName === 'prosody') {
      if (prosody.rate || prosody.pitch || prosody.volume) {
        throw new Error(msg('Magic supports one prosody control per turn.'))
      }
      prosody.rate = child.getAttribute('rate') || ''
      prosody.pitch = child.getAttribute('pitch') || ''
      prosody.volume = child.getAttribute('volume') || ''
      container = child
      continue
    }
    break
  }
  return { container, language: language.trim(), prosody }
}

function speechBlock(element, { voice = '', direction = '' } = {}) {
  const { container, language, prosody } = peelTurnControls(element)
  const inline = parseInline(container)
  return {
    type: 'speech',
    ...inline,
    voice,
    direction,
    language,
    prosody,
  }
}

function parseVoiceDefinitions(metadata) {
  if (!metadata) return []
  const definitions = []
  for (const extensions of metadata.children) {
    if (extensions.namespaceURI !== SSML_H_NAMESPACE || extensions.localName !== 'extensions') {
      throw new Error(msg`Magic cannot edit the <${extensions.localName}> metadata element.`)
    }
    for (const element of extensions.children) {
      if (element.namespaceURI !== SSML_H_NAMESPACE || element.localName !== 'voice-definition') {
        throw new Error(msg`Magic cannot edit the <${element.localName}> SSML-H extension.`)
      }
      const definition = {}
      for (const name of DEFINITION_ATTRIBUTES) {
        const value = element.getAttribute(name)
        if (value !== null && value !== '') definition[name] = value
      }
      for (const child of element.children) {
        if (child.namespaceURI !== SSML_H_NAMESPACE) {
          throw new Error(msg`Magic cannot edit the <${child.localName}> voice-definition element.`)
        }
        if (child.localName === 'description') definition.description = normalizedText(child.textContent)
        else if (child.localName === 'sample') {
          definition.sample = normalizedText(child.textContent)
          definition.sampleLanguage = child.getAttributeNS(XML_NAMESPACE, 'lang') || child.getAttribute('xml:lang') || ''
        } else throw new Error(msg`Magic cannot edit the <${child.localName}> voice-definition element.`)
      }
      definitions.push(definition)
    }
  }
  return definitions
}

export function parseMagicDocument(source) {
  if (String(source).length > 50_000 || /<!DOCTYPE|<!ENTITY/i.test(String(source))) {
    throw new Error(msg('Use safe SSML-H up to 50000 characters, without DTDs or entities.'))
  }
  const parser = new DOMParser()
  const document = parser.parseFromString(String(source || ''), 'application/xml')
  const parseError = document.querySelector('parsererror')
  if (parseError) throw new Error(msg`Invalid SSML-H: ${parseError.textContent.trim()}`)
  const root = document.documentElement
  if (root.localName !== 'speak' || root.namespaceURI !== SSML_NAMESPACE) {
    throw new Error(msg('SSML-H must use a namespaced <speak> root element.'))
  }
  const allowed = { speak: ['version', 'xml:lang'], voice: ['name', 'required', 'h:direction'],
    s: ['xml:lang', 'h:direction'], lang: ['xml:lang'], prosody: ['rate', 'pitch', 'volume'],
    break: ['time'], sub: ['alias'], 'say-as': ['interpret-as'] }
  for (const element of [root, ...root.querySelectorAll('*')]) {
    if (element.namespaceURI === SSML_NAMESPACE && allowed[element.localName]) {
      for (const attribute of element.attributes) {
        if (attribute.namespaceURI === 'http://www.w3.org/2000/xmlns/') continue
        if (!allowed[element.localName].includes(attribute.name)) throw new Error(msg`Magic cannot preserve attribute ${attribute.name}. Keep this document in the raw SSML-H editor.`)
      }
    }
  }

  const blocks = []
  let metadata = null
  for (const node of root.childNodes) {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = normalizedText(node.textContent)
      if (text) blocks.push({ type: 'speech', text, annotations: [], voice: '', direction: '', language: '', prosody: { rate: '', pitch: '', volume: '' } })
      continue
    }
    if (node.nodeType !== Node.ELEMENT_NODE) continue
    if (node.namespaceURI !== SSML_NAMESPACE) {
      throw new Error(msg`Magic cannot edit the <${node.localName}> element at the document level.`)
    }
    if (node.localName === 'metadata') {
      if (metadata) throw new Error(msg('Magic supports one metadata section.'))
      metadata = node
      continue
    }
    if (node.localName === 'voice') {
      blocks.push(speechBlock(node, {
        voice: node.getAttribute('name') || '',
        direction: node.getAttributeNS(SSML_H_NAMESPACE, 'direction') || node.getAttribute('h:direction') || '',
      }))
      continue
    }
    if (node.localName === 's' || node.localName === 'lang' || node.localName === 'prosody') {
      blocks.push(speechBlock(node, {
        direction: node.localName === 's'
          ? node.getAttributeNS(SSML_H_NAMESPACE, 'direction') || node.getAttribute('h:direction') || ''
          : '',
      }))
      continue
    }
    if (node.localName === 'break') {
      blocks.push({ type: 'break', milliseconds: parseBreakTime(node.getAttribute('time')) })
      continue
    }
    throw new Error(msg`Magic cannot edit <${node.localName}> blocks. Keep this document in the SSML-H editor.`)
  }
  if (!blocks.length) {
    blocks.push({ type: 'speech', text: '', annotations: [], voice: '', direction: '', language: '', prosody: { rate: '', pitch: '', volume: '' } })
  }
  return {
    blocks,
    voiceDefinitions: parseVoiceDefinitions(metadata),
    language: root.getAttributeNS(XML_NAMESPACE, 'lang') || root.getAttribute('xml:lang') || '',
  }
}

export function renderedSpeechText(block) {
  const text = String(block.text || '')
  const annotations = normalizedAnnotations(block)
  let cursor = 0
  let output = ''
  for (const annotation of annotations) {
    output += text.slice(cursor, annotation.start)
    const source = text.slice(annotation.start, annotation.end)
    if (annotation.type === 'substitution') output += String(annotation.alias || '').trim()
    else if (annotation.interpretAs === 'characters' || annotation.interpretAs === 'digits') output += [...source].join(' ')
    else if (annotation.interpretAs === 'ordinal' && /^[-+]?\d+$/.test(source)) {
      const number = BigInt(source)
      const absolute = number < 0n ? -number : number
      const lastTwo = Number(absolute % 100n)
      const suffix = lastTwo >= 10 && lastTwo <= 20
        ? 'th'
        : ({ 1: 'st', 2: 'nd', 3: 'rd' }[Number(absolute % 10n)] || 'th')
      output += `${number}${suffix}`
    } else output += source
    cursor = annotation.end
  }
  return output + text.slice(cursor)
}

export { SSML_H_NAMESPACE, SSML_NAMESPACE }
