import { msg } from './i18n.js'
const BUNDLE_MEDIA_TYPE = 'application/vnd.hangrylabs.magic-takes'

function speechBlocks(blocks) {
  return blocks.filter((block) => block.type === 'speech' && block.text.trim())
}

function takeFile(block) {
  return new File(
    [block.preview.blob],
    `kokorotts-turn-${block.id}.wav`,
    { type: block.preview.blob.type || 'audio/wav' },
  )
}

async function unpackBundle(response) {
  const buffer = await response.arrayBuffer()
  if (buffer.byteLength < 4) throw new Error(msg('Magic take response is incomplete.'))
  const view = new DataView(buffer)
  const manifestLength = view.getUint32(0, true)
  const manifestEnd = 4 + manifestLength
  if (manifestEnd > buffer.byteLength) throw new Error(msg('Magic take manifest is incomplete.'))
  const manifest = JSON.parse(new TextDecoder().decode(buffer.slice(4, manifestEnd)))
  if (manifest.version !== 1 || !Array.isArray(manifest.takes) || !manifest.output) {
    throw new Error(msg('Magic take response uses an unsupported format.'))
  }
  const payload = buffer.slice(manifestEnd)
  const extract = (item) => {
    const start = Number(item.offset)
    const end = start + Number(item.length)
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end < start || end > payload.byteLength) {
      throw new Error(msg('Magic take response contains an invalid audio range.'))
    }
    return new Blob([payload.slice(start, end)], { type: item.media_type || 'application/octet-stream' })
  }
  return {
    requestSeed: Number(manifest.request_seed),
    metrics: manifest.metrics || {},
    sampleRate: Number(manifest.sample_rate),
    committedProfiles: manifest.committed_profiles && typeof manifest.committed_profiles === 'object'
      ? manifest.committed_profiles
      : {},
    takes: new Map(manifest.takes.map((item) => [String(item.id), {
      blob: extract(item),
      extension: item.extension || 'wav',
      seed: Number(item.seed),
    }])),
    output: {
      blob: extract(manifest.output),
      extension: manifest.output.extension || 'wav',
    },
  }
}

export class MagicTakeStudio {
  constructor({ responseError }) {
    this.responseError = responseError
  }

  async render(payload, blocks, { signal, requestId } = {}) {
    const speech = speechBlocks(blocks)
    if (!speech.length) throw new Error(msg('Add at least one speech turn before generating.'))
    const retained = speech.filter((block) => block.locked && block.preview)
    const form = new FormData()
    form.append('payload', JSON.stringify(payload))
    form.append('speech_ids', JSON.stringify(speech.map((block) => String(block.id))))
    form.append('retained', JSON.stringify(retained.map((block) => ({
      id: String(block.id),
      seed: Number(block.captureSeed) || 0,
    }))))
    retained.forEach((block) => form.append('takes', takeFile(block)))
    const response = await fetch('/tts/magic/render', {
      method: 'POST',
      headers: requestId ? { 'X-KokoroTTS-Request-ID': requestId } : {},
      body: form,
      signal,
    })
    if (!response.ok) throw new Error(await this.responseError(response))
    if (!response.headers.get('Content-Type')?.startsWith(BUNDLE_MEDIA_TYPE)) {
      throw new Error(msg('Magic render returned an unexpected response type.'))
    }
    return unpackBundle(response)
  }

  async take(payload, speechIndex, { signal, requestId } = {}) {
    const response = await fetch('/tts/magic/take', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(requestId ? { 'X-KokoroTTS-Request-ID': requestId } : {}),
      },
      body: JSON.stringify({ payload, speech_index: speechIndex }),
      signal,
    })
    if (!response.ok) throw new Error(await this.responseError(response))
    return {
      blob: await response.blob(),
      extension: response.headers.get('X-KokoroTTS-Format') || 'wav',
      seed: Number(response.headers.get('X-KokoroTTS-Seed')),
    }
  }

  async assemble(blocks, { outputFormat = 'wav', normalizeLoudness = false, signal } = {}) {
    const speech = speechBlocks(blocks)
    if (!speech.length || speech.some((block) => !block.preview)) {
      throw new Error(msg('Generate every speech turn before assembling the dialogue.'))
    }
    const timeline = blocks.flatMap((block) => {
      if (block.type === 'break') return [{ type: 'break', milliseconds: block.milliseconds }]
      return block.text.trim()
        ? [{ type: 'speech', id: String(block.id) }]
        : []
    })
    const form = new FormData()
    form.append('options', JSON.stringify({
      items: timeline,
      output_format: outputFormat,
      normalize_loudness: normalizeLoudness,
    }))
    form.append('take_metadata', JSON.stringify(speech.map((block) => ({
      id: String(block.id),
      seed: Number(block.captureSeed) || 0,
    }))))
    speech.forEach((block) => form.append('takes', takeFile(block)))
    const response = await fetch('/tts/magic/assemble-upload', { method: 'POST', body: form, signal })
    if (!response.ok) throw new Error(await this.responseError(response))
    return {
      blob: await response.blob(),
      extension: response.headers.get('X-KokoroTTS-Format') || outputFormat,
    }
  }
}
