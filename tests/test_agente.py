from app.agent import HERRAMIENTAS, cargar_prompt, crear_agente


def test_agente_tiene_herramientas():
    agente = crear_agente()
    assert len(agente.tools) == len(HERRAMIENTAS) >= 2


def test_prompt_versionado_se_carga():
    prompt = cargar_prompt("v2")
    assert "<!--" not in prompt
    assert "buscar_politica" in prompt
