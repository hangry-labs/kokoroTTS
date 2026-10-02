export function formatTime(value) {
  const seconds = Number.isFinite(value) ? Math.max(0, value) : 0
  const minutes = Math.floor(seconds / 60)
  const remainder = Math.floor(seconds % 60)
  return `${minutes}:${String(remainder).padStart(2, '0')}`
}

export function fileFromBlob(blob, name = 'audio.wav') {
  return new File([blob], name, { type: blob.type || 'audio/wav', lastModified: Date.now() })
}

function writeAscii(view, offset, value) {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index))
  }
}

export function encodeWav(channels, sampleRate) {
  const channelCount = channels.length
  const frameCount = channels[0]?.length || 0
  const bytesPerSample = 2
  const dataSize = frameCount * channelCount * bytesPerSample
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  writeAscii(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeAscii(view, 8, 'WAVE')
  writeAscii(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, channelCount, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * channelCount * bytesPerSample, true)
  view.setUint16(32, channelCount * bytesPerSample, true)
  view.setUint16(34, 16, true)
  writeAscii(view, 36, 'data')
  view.setUint32(40, dataSize, true)

  let offset = 44
  for (let frame = 0; frame < frameCount; frame += 1) {
    for (let channel = 0; channel < channelCount; channel += 1) {
      const sample = Math.max(-1, Math.min(1, channels[channel][frame]))
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
      offset += bytesPerSample
    }
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

export async function trimAudio(blob, startSeconds, endSeconds) {
  const context = new AudioContext()
  try {
    const decoded = await context.decodeAudioData(await blob.arrayBuffer())
    const startFrame = Math.max(0, Math.floor(startSeconds * decoded.sampleRate))
    const endFrame = Math.min(decoded.length, Math.ceil(endSeconds * decoded.sampleRate))
    if (endFrame <= startFrame) throw new Error('The selected audio range is empty.')
    const channels = []
    for (let index = 0; index < decoded.numberOfChannels; index += 1) {
      channels.push(decoded.getChannelData(index).slice(startFrame, endFrame))
    }
    return encodeWav(channels, decoded.sampleRate)
  } finally {
    await context.close()
  }
}

