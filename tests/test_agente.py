from app.agent import HERRAMIENTAS, cargar_prompt, crear_agente


def test_agente_tiene_herramientas():
    agente = crear_agente()
    assert len(agente.tools) == len(HERRAMIENTAS) >= 2


def test_prompt_versionado_se_carga():
    prompt = cargar_prompt("v2")
    assert "<!--" not in prompt
    assert "buscar_politica" in prompt


def test_parametros_del_modelo_explicitos():
    from app import config

    agente = crear_agente()
    assert agente.generate_content_config.temperature == config.TEMPERATURA == 0.2
    assert agente.generate_content_config.max_output_tokens == config.MAX_TOKENS_SALIDA
