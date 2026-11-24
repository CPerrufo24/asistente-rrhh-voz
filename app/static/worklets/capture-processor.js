class CaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.samples = [];
    this.chunkSize = Math.round(sampleRate / 10);
  }

  process(inputs) {
    const entrada = inputs[0] && inputs[0][0];
    if (!entrada) {
      return true;
    }

    for (let i = 0; i < entrada.length; i += 1) {
      const muestra = Math.max(-1, Math.min(1, entrada[i]));
      this.samples.push(muestra < 0 ? Math.round(muestra * 0x8000) : Math.round(muestra * 0x7fff));
    }

    while (this.samples.length >= this.chunkSize) {
      const bloque = new Int16Array(this.samples.slice(0, this.chunkSize));
      this.port.postMessage(bloque.buffer, [bloque.buffer]);
      this.samples = this.samples.slice(this.chunkSize);
    }

    return true;
  }
}

registerProcessor('capture-processor', CaptureProcessor);
