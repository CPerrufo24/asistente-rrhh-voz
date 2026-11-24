"""RAG léxico sobre el reglamento interno y la LFT, con BM25 propio."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app import config

_K1 = 1.5
_B = 0.75
# Bono por cada término de la consulta que aparece en el título del artículo (multiplica su IDF).
# El título nombra el tema ("Aguinaldo anual") y debe pesar más que palabras genéricas del cuerpo.
PESO_TITULO = 1.5

_RE_ARTICULO_LFT = re.compile(r"^###\s+Art[ií]culo\s+(.+?)\s*$", re.IGNORECASE)
_RE_ARTICULO_REGLAMENTO = re.compile(
    r"^###\s+Art[ií]culo\s+(\d+)(?:\.\s*(.*?))?\s*$", re.IGNORECASE
)
_RE_ENCABEZADO = re.compile(r"^\s*#{2,3}\s+")
_RE_CAPITULO = re.compile(r"^\s*(?:CAP[IÍ]TULO|T[IÍ]TULO)\b", re.IGNORECASE)
_RE_PUNTUACION = re.compile(r"[^a-z0-9]+")

_STOPWORDS = frozenset(
    """
    a al algo algunas alguno algunos ante antes aqui asi aun bajo cada como con
    contra cual cuales cualquier cuando cuanta cuantas cuanto cuantos de del desde
    donde dos durante e el ella ellas ellos en entre era eran eres es esa esas ese
    eso esos esta estan estas este esto estos estoy fue fueron ha han hasta hay la
    las le les lo los mas me mi mis mucho muy nada ni no nos nosotros o os otra
    otro otros para pero poco por porque pues que quien quienes se sea segun ser si
    sin sobre son su sus tan tanto te tiene tienen todo todos tras tu tus un una
    unas uno unos vosotros y ya yo
    """.split()
)


@dataclass(frozen=True)
class Fragmento:
    """Un artículo o fragmento de un documento normativo."""

    id: str
    fuente: str
    titulo: str
    texto: str


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(caracter for caracter in descompuesto if not unicodedata.combining(caracter))


def normalizar(texto: str) -> list[str]:
    """Normaliza y tokeniza texto en español para la búsqueda léxica."""
    limpio = _sin_acentos(texto).lower()
    limpio = _RE_PUNTUACION.sub(" ", limpio)
    palabras: list[str] = []
    for palabra in limpio.split():
        if palabra in _STOPWORDS:
            continue
        if len(palabra) > 4:
            if palabra.endswith("es"):
                palabra = palabra[:-2]
            elif palabra.endswith("s"):
                palabra = palabra[:-1]
        if palabra and palabra not in _STOPWORDS:
            palabras.append(palabra)
    return palabras


def _slug(texto: str) -> str:
    limpio = _sin_acentos(texto).lower()
    return re.sub(r"[^a-z0-9]+", "-", limpio).strip("-")


def _cargar_lft(ruta: Path) -> list[Fragmento]:
    if not ruta.is_file():
        return []
    fragmentos: list[Fragmento] = []
    actual: tuple[str, str] | None = None
    cuerpo: list[str] = []

    def cerrar() -> None:
        if actual is None:
            return
        designacion, titulo = actual
        texto = "\n".join(cuerpo).strip()
        if texto:
            fragmentos.append(
                Fragmento(
                    id=f"lft-{_slug(designacion)}",
                    fuente=f"LFT, artículo {designacion}",
                    titulo=titulo,
                    texto=texto,
                )
            )

    for linea in ruta.read_text(encoding="utf-8").splitlines():
        coincidencia = _RE_ARTICULO_LFT.match(linea)
        if coincidencia:
            cerrar()
            designacion = coincidencia.group(1).strip()
            actual = (designacion, f"Artículo {designacion}")
            cuerpo = []
            continue
        if _RE_ENCABEZADO.match(linea) or _RE_CAPITULO.match(linea):
            cerrar()
            actual = None
            cuerpo = []
            continue
        if actual is not None:
            cuerpo.append(linea.rstrip())
    cerrar()
    return fragmentos


def _cargar_reglamento(ruta: Path) -> list[Fragmento]:
    if not ruta.is_file():
        return []
    fragmentos: list[Fragmento] = []
    actual: tuple[str, str] | None = None
    cuerpo: list[str] = []

    def cerrar() -> None:
        if actual is None:
            return
        numero, titulo = actual
        texto = "\n".join(cuerpo).strip()
        if texto:
            fragmentos.append(
                Fragmento(
                    id=f"reglamento-{_slug(numero)}",
                    fuente=f"Reglamento interno, artículo {numero}",
                    titulo=titulo,
                    texto=texto,
                )
            )

    for linea in ruta.read_text(encoding="utf-8").splitlines():
        coincidencia = _RE_ARTICULO_REGLAMENTO.match(linea)
        if coincidencia:
            cerrar()
            numero = coincidencia.group(1).strip()
            titulo = (coincidencia.group(2) or "").strip()
            actual = (numero, titulo)
            cuerpo = []
            continue
        if _RE_ENCABEZADO.match(linea) or _RE_CAPITULO.match(linea):
            cerrar()
            actual = None
            cuerpo = []
            continue
        if actual is not None:
            cuerpo.append(linea.rstrip())
    cerrar()
    return fragmentos


def cargar_corpus(dir_datos: Path) -> list[Fragmento]:
    """Carga un fragmento por artículo del reglamento interno y de la LFT."""
    fragmentos = _cargar_reglamento(dir_datos / "reglamento" / "reglamento_interno.md")
    fragmentos.extend(_cargar_lft(dir_datos / "lft" / "lft_articulos.md"))
    return fragmentos


class IndiceBM25:
    """Índice BM25 (k1=1.5, b=0.75) con el título ponderado al doble."""

    def __init__(self, fragmentos: list[Fragmento]) -> None:
        self.fragmentos = list(fragmentos)
        self._frecuencias: list[Counter[str]] = []
        self._longitudes: list[int] = []
        self._titulos: list[set[str]] = []
        documentos_con_palabra: Counter[str] = Counter()

        for fragmento in self.fragmentos:
            self._titulos.append(set(normalizar(fragmento.titulo)))
            tokens = normalizar(fragmento.titulo) + normalizar(fragmento.texto)
            frecuencias = Counter(tokens)
            self._frecuencias.append(frecuencias)
            self._longitudes.append(len(tokens))
            documentos_con_palabra.update(frecuencias.keys())

        total = len(self.fragmentos)
        self._idf = {
            palabra: math.log(1 + (total - frecuencia + 0.5) / (frecuencia + 0.5))
            for palabra, frecuencia in documentos_con_palabra.items()
        }
        self._longitud_promedio = sum(self._longitudes) / total if total else 0.0

    def buscar(self, consulta: str, k: int) -> list[tuple[Fragmento, float]]:
        """Devuelve hasta k fragmentos ordenados por puntaje BM25, sin ceros."""
        if k <= 0 or not self.fragmentos:
            return []
        terminos = normalizar(consulta)
        if not terminos:
            return []

        puntuados: list[tuple[Fragmento, float]] = []
        for fragmento, frecuencias, longitud, titulo in zip(
            self.fragmentos, self._frecuencias, self._longitudes, self._titulos, strict=True
        ):
            puntaje = 0.0
            for termino in set(terminos) & titulo:
                puntaje += PESO_TITULO * self._idf.get(termino, 0.0)
            for termino in terminos:
                frecuencia = frecuencias.get(termino, 0)
                if not frecuencia:
                    continue
                idf = self._idf.get(termino)
                if idf is None:
                    continue
                denominador = frecuencia + _K1 * (1 - _B + _B * longitud / self._longitud_promedio)
                puntaje += idf * frecuencia * (_K1 + 1) / denominador
            if puntaje > 0:
                puntuados.append((fragmento, puntaje))

        puntuados.sort(key=lambda item: (-item[1], item[0].id))
        return puntuados[:k]


_INDICES: dict[str, IndiceBM25] = {}


def obtener_indice() -> IndiceBM25:
    """Devuelve el índice del corpus, cacheado por la ruta de datos configurada."""
    clave = str(config.DIR_DATOS)
    if clave not in _INDICES:
        _INDICES[clave] = IndiceBM25(cargar_corpus(config.DIR_DATOS))
    return _INDICES[clave]


def reiniciar_indice() -> None:
    """Limpia la caché de índices (útil en pruebas)."""
    _INDICES.clear()
