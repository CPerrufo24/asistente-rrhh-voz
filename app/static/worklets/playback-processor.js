class PlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.cola = [];
    this.actual = null;
    this.indice = 0;

    this.port.onmessage = (evento) => {
      const dato = evento.data;
      if (dato && dato.tipo === 'limpiar') {
        this.cola = [];
        this.actual = null;
        this.indice = 0;
        return;
      }
      if (dato instanceof ArrayBuffer) {
        this.cola.push(new Int16Array(dato));
      }
    };
  }

  _siguienteMuestra() {
    if (!this.actual || this.indice >= this.actual.length) {
      this.actual = this.cola.shift() || null;
      this.indice = 0;
    }
    if (!this.actual) {
      return 0;
    }
    const valor = this.actual[this.indice];
    this.indice += 1;
    return valor / 0x8000;
  }

  process(_inputs, outputs) {
    const salida = outputs[0];
    if (!salida || !salida.length) {
      return true;
    }

    const canales = salida.length;
    const longitud = salida[0].length;
    for (let i = 0; i < longitud; i += 1) {
      const muestra = this._siguienteMuestra();
      for (let canal = 0; canal < canales; canal += 1) {
        salida[canal][i] = muestra;
      }
    }

    return true;
  }
}

registerProcessor('playback-processor', PlaybackProcessor);
