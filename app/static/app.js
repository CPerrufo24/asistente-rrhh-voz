const $ = (selector) => document.querySelector(selector);

const estado = {
  sessionId: null,
  socket: null,
  captureContext: null,
  playbackContext: null,
  captureNode: null,
  playbackNode: null,
  captureSource: null,
  captureGain: null,
  mediaStream: null,
  mensajeActivoUsuario: null,
  mensajeActivoAgente: null,
  trace: [],
  ultimaRespuesta: null,
  esperando: false,
  vozActiva: false,
};

const quickQuestions = [
  '¿Cuántos días de vacaciones me tocan? Soy E-1005',
  '¿Cuándo pagan el aguinaldo?',
  '¿Tienen becas para maestría?',
];

const refs = {};

function escapeHtml(texto) {
  return texto
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function setEstadoChat(texto) {
  refs.estadoChat.textContent = texto;
}

function setEstadoVoz(texto, clase = '') {
  refs.estadoVoz.textContent = texto;
  refs.estadoVoz.className = `estado ${clase}`.trim();
}

function mostrarError(texto) {
  if (!texto) {
    refs.errorChat.hidden = true;
    refs.errorChat.textContent = '';
    return;
  }
  refs.errorChat.hidden = false;
  refs.errorChat.textContent = texto;
}

function limpiarConversacion() {
  refs.mensajes.innerHTML = '';
  estado.mensajeActivoUsuario = null;
  estado.mensajeActivoAgente = null;
}

function limpiarTraza() {
  estado.trace = [];
  estado.ultimaRespuesta = null;
  refs.trazaLista.innerHTML = '';
  refs.metadatosUltimaRespuesta.innerHTML = '';
}

function actualizarMetadatosUltimaRespuesta() {
  const datos = estado.ultimaRespuesta;
  if (!datos) {
    refs.metadatosUltimaRespuesta.innerHTML = '<div class="meta-card">Sin respuesta todavía.</div>';
    return;
  }
  refs.metadatosUltimaRespuesta.innerHTML = `
    <div class="meta-card"><strong>Latencia</strong><br />${datos.latencia_ms} ms</div>
    <div class="meta-card"><strong>Tokens de entrada</strong><br />${datos.tokens.entrada}</div>
    <div class="meta-card"><strong>Tokens de salida</strong><br />${datos.tokens.salida}</div>
    <div class="meta-card"><strong>Fuentes</strong><br />${datos.fuentes.length ? datos.fuentes.join(', ') : 'Sin fuentes citadas'}</div>
  `;
}

function renderizarTraza() {
  refs.trazaLista.innerHTML = '';
  if (!estado.trace.length) {
    refs.trazaLista.innerHTML = '<div class="traza-item"><p class="detalle">La traza aparecerá aquí.</p></div>';
    actualizarMetadatosUltimaRespuesta();
    return;
  }

  for (const item of estado.trace) {
    const nodo = document.createElement('article');
    nodo.className = `traza-item${item.alerta_inyeccion ? ' alerta' : ''}`;
    const titulo = item.tipo === 'tool' ? `Tool: ${item.nombre}` : `Resultado: ${item.nombre}`;
    const args = item.tipo === 'tool' ? `<pre>${escapeHtml(JSON.stringify(item.args, null, 2))}</pre>` : '';
    const fuentes = item.tipo === 'tool_resultado'
      ? `<div class="tags">${(item.fuentes || []).map((fuente) => `<span class="tag">${escapeHtml(String(fuente))}</span>`).join('')}${item.alerta_inyeccion ? '<span class="tag peligro">Alerta de inyección</span>' : ''}</div>`
      : '';
    nodo.innerHTML = `
      <div class="traza-item-head">
        <h3>${escapeHtml(titulo)}</h3>
        <span class="trace-small">${escapeHtml(item.tipo)}</span>
      </div>
      ${args}
      ${fuentes}
    `;
    refs.trazaLista.appendChild(nodo);
  }
  actualizarMetadatosUltimaRespuesta();
}

function crearMensaje(rol, texto, claseExtra = '') {
  const nodo = document.createElement('article');
  nodo.className = `mensaje ${rol}${claseExtra ? ` ${claseExtra}` : ''}`;
  nodo.innerHTML = `
    <span class="meta">${rol === 'usuario' ? 'Usuario' : rol === 'agente' ? 'Asistente' : 'Sistema'}</span>
    <div class="contenido"></div>
  `;
  nodo.querySelector('.contenido').textContent = texto;
  refs.mensajes.appendChild(nodo);
  refs.mensajes.scrollTop = refs.mensajes.scrollHeight;
  return nodo;
}

function actualizarMensaje(nodo, texto, final = false) {
  const contenido = nodo.querySelector('.contenido');
  contenido.textContent = texto;
  nodo.classList.toggle('parcial', !final);
  refs.mensajes.scrollTop = refs.mensajes.scrollHeight;
}

function asegurarMensajeVoz(rol) {
  const clave = rol === 'usuario' ? 'mensajeActivoUsuario' : 'mensajeActivoAgente';
  if (!estado[clave]) {
    const nodo = crearMensaje(rol, '');
    nodo.classList.add('voz');
    estado[clave] = nodo;
  }
  return estado[clave];
}

async function obtenerSesionNueva() {
  const respuesta = await fetch('/api/sesiones', { method: 'POST' });
  if (!respuesta.ok) {
    throw new Error('No se pudo crear la sesión.');
  }
  const datos = await respuesta.json();
  estado.sessionId = datos.session_id;
  return estado.sessionId;
}

async function enviarChat() {
  const mensaje = refs.mensajeInput.value.trim();
  if (!mensaje) {
    mostrarError('Escribe un mensaje para continuar.');
    return;
  }
  if (!estado.sessionId) {
    await obtenerSesionNueva();
  }
  mostrarError('');
  estado.esperando = true;
  refs.enviarBtn.disabled = true;
  refs.mensajeInput.disabled = true;
  setEstadoChat('Pensando…');
  crearMensaje('usuario', mensaje);
  refs.mensajeInput.value = '';

  try {
    const respuesta = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: estado.sessionId, mensaje }),
    });
    const datos = await respuesta.json();
    if (!respuesta.ok) {
      throw new Error(datos.detail || 'No se pudo completar la consulta.');
    }
    estado.ultimaRespuesta = datos;
    estado.trace = datos.traza || [];
    actualizarMetadatosUltimaRespuesta();
    renderizarTraza();
    crearMensaje('agente', datos.respuesta || '');
    setEstadoChat('Respuesta lista');
  } catch (error) {
    mostrarError(error.message || 'Error inesperado al enviar el mensaje.');
    setEstadoChat('Error');
    crearMensaje('sistema', error.message || 'No fue posible atender la consulta.');
  } finally {
    estado.esperando = false;
    refs.enviarBtn.disabled = false;
    refs.mensajeInput.disabled = false;
    refs.mensajeInput.focus();
  }
}

async function crearCapturaAudio() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const contexto = new AudioContext({ sampleRate: 16000 });
  await contexto.audioWorklet.addModule('/static/worklets/capture-processor.js');
  const fuente = contexto.createMediaStreamSource(stream);
  const nodo = new AudioWorkletNode(contexto, 'capture-processor');
  const ganancia = contexto.createGain();
  ganancia.gain.value = 0;
  fuente.connect(nodo).connect(ganancia).connect(contexto.destination);
  return { contexto, fuente, nodo, ganancia, stream };
}

async function crearReproduccionAudio() {
  const contexto = new AudioContext({ sampleRate: 24000 });
  await contexto.audioWorklet.addModule('/static/worklets/playback-processor.js');
  const nodo = new AudioWorkletNode(contexto, 'playback-processor');
  const ganancia = contexto.createGain();
  ganancia.gain.value = 1;
  nodo.connect(ganancia).connect(contexto.destination);
  return { contexto, nodo, ganancia };
}

async function iniciarVoz() {
  if (estado.vozActiva) {
    return;
  }
  if (!estado.sessionId) {
    await obtenerSesionNueva();
  }
  setEstadoVoz('Conectando…');
  refs.vozBtn.textContent = 'Colgar';
  try {
    const [captura, reproduccion] = await Promise.all([crearCapturaAudio(), crearReproduccionAudio()]);
    estado.captureContext = captura.contexto;
    estado.captureSource = captura.fuente;
    estado.captureNode = captura.nodo;
    estado.captureGain = captura.ganancia;
    estado.mediaStream = captura.stream;
    estado.playbackContext = reproduccion.contexto;
    estado.playbackNode = reproduccion.nodo;

    const socket = new WebSocket(`/ws/voz/${estado.sessionId}`);
    socket.binaryType = 'arraybuffer';
    estado.socket = socket;

    socket.addEventListener('open', async () => {
      estado.vozActiva = true;
      await estado.captureContext.resume();
      await estado.playbackContext.resume();
      setEstadoVoz('Escuchando', 'escuchando');
    });

    socket.addEventListener('message', (evento) => {
      if (typeof evento.data === 'string') {
        const mensaje = JSON.parse(evento.data);
        if (mensaje.tipo === 'usuario') {
          const nodo = asegurarMensajeVoz('usuario');
          actualizarMensaje(nodo, mensaje.texto || '...', mensaje.final);
          if (mensaje.final) {
            estado.mensajeActivoUsuario = null;
          }
          return;
        }
        if (mensaje.tipo === 'agente') {
          setEstadoVoz('El agente habla', 'habla');
          const nodo = asegurarMensajeVoz('agente');
          actualizarMensaje(nodo, mensaje.texto || '...', mensaje.final);
          if (mensaje.final) {
            estado.mensajeActivoAgente = null;
            setEstadoVoz('Escuchando', 'escuchando');
          }
          return;
        }
        if (mensaje.tipo === 'interrumpido') {
          if (estado.playbackNode) {
            estado.playbackNode.port.postMessage({ tipo: 'limpiar' });
          }
          setEstadoVoz('Escuchando', 'escuchando');
          crearMensaje('sistema', 'El agente fue interrumpido.');
          return;
        }
        if (mensaje.tipo === 'turno_completo') {
          setEstadoVoz('Escuchando', 'escuchando');
          return;
        }
        if (mensaje.tipo === 'error') {
          setEstadoVoz('Error', 'error');
          mostrarError(mensaje.mensaje || 'Se produjo un error en la voz.');
          crearMensaje('sistema', mensaje.mensaje || 'Error en la voz.');
          return;
        }
        if (mensaje.tipo === 'tool' || mensaje.tipo === 'tool_resultado') {
          estado.trace.push(mensaje);
          renderizarTraza();
        }
        return;
      }

      if (estado.playbackNode && evento.data instanceof ArrayBuffer) {
        estado.playbackNode.port.postMessage(evento.data, [evento.data]);
      }
    });

    socket.addEventListener('close', () => {
      detenerVoz(false);
    });

    socket.addEventListener('error', () => {
      setEstadoVoz('Error', 'error');
      mostrarError('No se pudo abrir el canal de voz.');
    });
  } catch (error) {
    setEstadoVoz('Error', 'error');
    mostrarError(error.message || 'No se pudo activar el micrófono.');
    detenerVoz();
  }
}

function detenerVoz(limpiarSocket = true) {
  estado.vozActiva = false;
  refs.vozBtn.textContent = 'Hablar';
  if (limpiarSocket && estado.socket) {
    estado.socket.close();
  }
  estado.socket = null;

  if (estado.mediaStream) {
    for (const pista of estado.mediaStream.getTracks()) {
      pista.stop();
    }
  }
  estado.mediaStream = null;

  if (estado.captureSource) {
    try {
      estado.captureSource.disconnect();
    } catch (error) {
      void error;
    }
  }
  if (estado.captureNode) {
    try {
      estado.captureNode.disconnect();
    } catch (error) {
      void error;
    }
  }
  if (estado.captureGain) {
    try {
      estado.captureGain.disconnect();
    } catch (error) {
      void error;
    }
  }
  if (estado.captureContext) {
    estado.captureContext.close();
  }
  if (estado.playbackNode) {
    try {
      estado.playbackNode.disconnect();
    } catch (error) {
      void error;
    }
  }
  if (estado.playbackContext) {
    estado.playbackContext.close();
  }

  estado.captureContext = null;
  estado.captureNode = null;
  estado.captureSource = null;
  estado.captureGain = null;
  estado.playbackContext = null;
  estado.playbackNode = null;
  estado.mensajeActivoUsuario = null;
  estado.mensajeActivoAgente = null;
  setEstadoVoz('Inactivo');
}

async function nuevaConversacion() {
  detenerVoz();
  limpiarConversacion();
  limpiarTraza();
  await obtenerSesionNueva();
  setEstadoChat('Listo para escribir');
  mostrarError('');
  refs.mensajeInput.value = '';
  refs.mensajeInput.focus();
}

function poblarChips() {
  refs.chipsRapidos.innerHTML = '';
  for (const pregunta of quickQuestions) {
    const boton = document.createElement('button');
    boton.className = 'chip';
    boton.type = 'button';
    boton.textContent = pregunta;
    boton.addEventListener('click', () => {
      refs.mensajeInput.value = pregunta;
      enviarChat();
    });
    refs.chipsRapidos.appendChild(boton);
  }
}

function enlazarEventos() {
  refs.enviarBtn.addEventListener('click', enviarChat);
  refs.vozBtn.addEventListener('click', () => {
    if (estado.vozActiva) {
      detenerVoz();
      return;
    }
    iniciarVoz();
  });
  refs.nuevaConversacion.addEventListener('click', nuevaConversacion);
  refs.mensajeInput.addEventListener('keydown', (evento) => {
    if (evento.key === 'Enter' && !evento.shiftKey) {
      evento.preventDefault();
      enviarChat();
    }
  });
}

async function iniciar() {
  refs.estadoVoz = $('#estadoVoz');
  refs.estadoChat = $('#estadoChat');
  refs.mensajes = $('#mensajes');
  refs.mensajeInput = $('#mensajeInput');
  refs.enviarBtn = $('#enviarBtn');
  refs.vozBtn = $('#vozBtn');
  refs.nuevaConversacion = $('#nuevaConversacion');
  refs.errorChat = $('#errorChat');
  refs.chipsRapidos = $('#chipsRapidos');
  refs.trazaLista = $('#trazaLista');
  refs.metadatosUltimaRespuesta = $('#metadatosUltimaRespuesta');

  poblarChips();
  enlazarEventos();
  limpiarTraza();
  limpiarConversacion();
  await nuevaConversacion();
}

document.addEventListener('DOMContentLoaded', () => {
  iniciar().catch((error) => {
    console.error(error);
    mostrarError('No se pudo inicializar la interfaz.');
    setEstadoChat('Error');
  });
});
