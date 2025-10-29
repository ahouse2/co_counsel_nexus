export function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  /* ChunkID */ writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  /* Format */ writeString(view, 8, 'WAVE');
  /* Subchunk1ID */ writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // PCM header length
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  /* Subchunk2ID */ writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);
  floatTo16Bit(view, samples, 44);
  return buffer;
}

export function audioBufferToWav(buffer: AudioBuffer): Blob {
  const sampleRate = buffer.sampleRate;
  const channelCount = buffer.numberOfChannels;
  const length = buffer.length;
  const tmp = new Float32Array(length);
  if (channelCount === 1) {
    buffer.copyFromChannel(tmp, 0);
  } else {
    const channelData = Array.from({ length: channelCount }, (_, index) => {
      const channel = new Float32Array(length);
      buffer.copyFromChannel(channel, index);
      return channel;
    });
    for (let i = 0; i < length; i += 1) {
      let sum = 0;
      for (let channelIndex = 0; channelIndex < channelCount; channelIndex += 1) {
        sum += channelData[channelIndex][i];
      }
      tmp[i] = sum / channelCount;
    }
  }
  const wav = encodeWav(tmp, sampleRate);
  return new Blob([wav], { type: 'audio/wav' });
}

function writeString(view: DataView, offset: number, value: string): void {
  for (let i = 0; i < value.length; i += 1) {
    view.setUint8(offset + i, value.charCodeAt(i));
  }
}

function floatTo16Bit(view: DataView, samples: Float32Array, offset: number): void {
  let writeOffset = offset;
  for (let i = 0; i < samples.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(writeOffset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    writeOffset += 2;
  }
}
