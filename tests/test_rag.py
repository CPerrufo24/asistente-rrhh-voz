from pathlib import Path

from app import config
from app.rag import IndiceBM25, cargar_corpus, obtener_indice, reiniciar_indice
from app.tools.politicas import AVISO, buscar_politica


def test_cargar_corpus_parsea_reglamento(tmp_path):
    carpeta = tmp_path / "reglamento"
    carpeta.mkdir()
    (carpeta / "reglamento_interno.md").write_text(
        """# Reglamento interno

Texto de introducción que no debe formar parte de ningún artículo.

## Capítulo I. Disposiciones generales

### Artículo 1. Jornada de trabajo

La jornada ordinaria es de cuarenta horas semanales.

### Artículo 2. Vacaciones

Se otorgan dos días adicionales a partir de cinco años de antigüedad.
""",
        encoding="utf-8",
    )

    corpus = cargar_corpus(tmp_path)

    assert len(corpus) == 2
    assert corpus[0].fuente == "Reglamento interno, artículo 1"
    assert corpus[0].titulo == "Jornada de trabajo"
    assert "cuarenta horas" in corpus[0].texto
    assert "introducción" not in corpus[0].texto
    assert corpus[1].fuente == "Reglamento interno, artículo 2"
    assert corpus[1].titulo == "Vacaciones"


def test_corpus_lft_incluye_fraccion(tmp_path):
    carpeta = tmp_path / "lft"
    carpeta.mkdir()
    (carpeta / "lft_articulos.md").write_text(
        """# LFT

### Artículo 132, fracción XXVII Bis

Artículo 132.- Permiso de paternidad de cinco días.

### Artículo 87

Artículo 87.- Aguinaldo anual.
""",
        encoding="utf-8",
    )

    corpus = cargar_corpus(tmp_path)

    assert [fragmento.fuente for fragmento in corpus] == [
        "LFT, artículo 132, fracción XXVII Bis",
        "LFT, artículo 87",
    ]


def test_indice_prioriza_el_titulo():
    from app.rag import Fragmento

    fragmentos = [
        Fragmento("a", "A", "Aguinaldo", "Texto sobre otra prestación."),
        Fragmento("b", "B", "Otra cosa", "El aguinaldo se paga en diciembre."),
    ]
    indice = IndiceBM25(fragmentos)

    resultados = indice.buscar("aguinaldo", 2)

    assert len(resultados) == 2
    assert resultados[0][0].id == "a"
    assert resultados[0][1] > resultados[1][1]


def test_aguinaldo_encuentra_articulo_87_de_la_lft():
    datos = Path(__file__).resolve().parents[1] / "data"
    config.DIR_DATOS = datos
    reiniciar_indice()
    try:
        resultado = buscar_politica("aguinaldo")
        assert resultado["sin_resultados"] is False
        assert resultado["aviso"] == AVISO
        assert any(
            fragmento["fuente"] == "LFT, artículo 87" for fragmento in resultado["resultados"]
        )
        assert obtener_indice().fragmentos
    finally:
        reiniciar_indice()


def test_consulta_ajena_no_devuelve_resultados():
    datos = Path(__file__).resolve().parents[1] / "data"
    config.DIR_DATOS = datos
    reiniciar_indice()
    try:
        resultado = buscar_politica("receta de pozole")
        assert resultado["sin_resultados"] is True
        assert resultado["resultados"] == []
    finally:
        reiniciar_indice()
