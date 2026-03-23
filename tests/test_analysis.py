import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_analisar_proposta_sucesso(cliente_http, proposta_exemplo, resultado_mock):
    with patch(
        "app.api.routes.analysis.analisador.analisar",
        new_callable=AsyncMock,
        return_value=resultado_mock,
    ):
        response = await cliente_http.post("/analyze", json=proposta_exemplo)

    assert response.status_code == 201
    data = response.json()

    assert data["id"] == 1
    assert data["titulo"] == proposta_exemplo["titulo"]
    assert data["nivel_freelancer"] == "pleno"
    assert data["valor_hora"] == 90.0

    resultado = data["resultado"]
    assert resultado["complexity"] == "alta"
    assert resultado["estimated_hours"]["min"] == 160
    assert resultado["estimated_hours"]["max"] == 260
    assert resultado["suggested_price"]["min"] == 14400.0
    assert resultado["suggested_price"]["max"] == 23400.0
    assert resultado["suggested_price"]["currency"] == "BRL"
    assert len(resultado["risks"]) >= 1
    assert len(resultado["red_flags"]) >= 1
    assert len(resultado["questions_to_ask"]) >= 1
    assert len(resultado["recommendation"]) > 0
    assert len(resultado["scope_summary"]) > 0


@pytest.mark.asyncio
async def test_analisar_proposta_campos_obrigatorios(cliente_http):
    response = await cliente_http.post("/analyze", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_titulo_curto(cliente_http):
    payload = {
        "titulo": "OK",
        "descricao": "Descrição válida e suficientemente longa para passar na validação mínima.",
        "prazo_cliente": "1 mês",
        "tecnologias": ["Python"],
        "nivel_freelancer": "junior",
        "valor_hora": 50.0,
    }
    response = await cliente_http.post("/analyze", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_valor_hora_invalido(cliente_http):
    payload = {
        "titulo": "Título válido para teste",
        "descricao": "Descrição válida e suficientemente longa para passar na validação mínima.",
        "prazo_cliente": "1 mês",
        "tecnologias": ["Python"],
        "nivel_freelancer": "senior",
        "valor_hora": -50.0,
    }
    response = await cliente_http.post("/analyze", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_nivel_invalido(cliente_http, proposta_exemplo):
    payload = {**proposta_exemplo, "nivel_freelancer": "estagiario"}
    response = await cliente_http.post("/analyze", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_listar_analises_vazio(cliente_http):
    response = await cliente_http.get("/analyses")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_listar_analises_com_dados(cliente_http, proposta_exemplo, resultado_mock):
    with patch(
        "app.api.routes.analysis.analisador.analisar",
        new_callable=AsyncMock,
        return_value=resultado_mock,
    ):
        await cliente_http.post("/analyze", json=proposta_exemplo)
        await cliente_http.post("/analyze", json={**proposta_exemplo, "titulo": "Segundo Projeto de Teste"})

    response = await cliente_http.get("/analyses")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["titulo"] == "Segundo Projeto de Teste"


@pytest.mark.asyncio
async def test_listar_analises_filtro_complexidade(cliente_http, proposta_exemplo, resultado_mock):
    with patch(
        "app.api.routes.analysis.analisador.analisar",
        new_callable=AsyncMock,
        return_value=resultado_mock,
    ):
        await cliente_http.post("/analyze", json=proposta_exemplo)

    response_alta = await cliente_http.get("/analyses?complexidade=alta")
    assert response_alta.status_code == 200
    assert len(response_alta.json()) == 1

    response_baixa = await cliente_http.get("/analyses?complexidade=baixa")
    assert response_baixa.status_code == 200
    assert len(response_baixa.json()) == 0


@pytest.mark.asyncio
async def test_buscar_analise_por_id(cliente_http, proposta_exemplo, resultado_mock):
    with patch(
        "app.api.routes.analysis.analisador.analisar",
        new_callable=AsyncMock,
        return_value=resultado_mock,
    ):
        post_response = await cliente_http.post("/analyze", json=proposta_exemplo)
    analise_id = post_response.json()["id"]

    response = await cliente_http.get(f"/analyses/{analise_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == analise_id
    assert data["titulo"] == proposta_exemplo["titulo"]


@pytest.mark.asyncio
async def test_buscar_analise_nao_encontrada(cliente_http):
    response = await cliente_http.get("/analyses/99999")
    assert response.status_code == 404
    assert "não encontrada" in response.json()["detail"]


@pytest.mark.asyncio
async def test_health_check(cliente_http):
    response = await cliente_http.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_listar_analises_paginacao(cliente_http, proposta_exemplo, resultado_mock):
    with patch(
        "app.api.routes.analysis.analisador.analisar",
        new_callable=AsyncMock,
        return_value=resultado_mock,
    ):
        for i in range(5):
            await cliente_http.post("/analyze", json={**proposta_exemplo, "titulo": f"Projeto {i+1}"})

    response_pagina1 = await cliente_http.get("/analyses?limite=3&pagina=1")
    assert response_pagina1.status_code == 200
    assert len(response_pagina1.json()) == 3

    response_pagina2 = await cliente_http.get("/analyses?limite=3&pagina=2")
    assert response_pagina2.status_code == 200
    assert len(response_pagina2.json()) == 2
