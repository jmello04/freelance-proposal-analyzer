from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

PATCH_ANALISAR = "app.api.routes.analysis.obter_analisador"


def _mock_analisador(resultado_mock):
    instancia = AsyncMock()
    instancia.analisar = AsyncMock(return_value=resultado_mock)
    return instancia


# ══════════════════════════════════════════════════════════════
# POST /analyze
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_analisar_proposta_sucesso(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        response = await cliente_http.post("/analyze", json=proposta_exemplo)

    assert response.status_code == 201, response.text
    data = response.json()

    assert data["id"] == 1
    assert data["titulo"] == proposta_exemplo["titulo"]
    assert data["nivel_freelancer"] == "pleno"
    assert data["valor_hora"] == 90.0
    assert "criado_em" in data

    res = data["resultado"]
    assert res["complexity"] == "alta"
    assert res["estimated_hours"]["min"] == 160
    assert res["estimated_hours"]["max"] == 260
    assert res["suggested_price"]["min"] == 14400.0
    assert res["suggested_price"]["max"] == 23400.0
    assert res["suggested_price"]["currency"] == "BRL"
    assert len(res["risks"]) >= 1
    assert len(res["red_flags"]) >= 1
    assert len(res["questions_to_ask"]) >= 1
    assert res["recommendation"]
    assert res["scope_summary"]


@pytest.mark.asyncio
async def test_analisar_proposta_persistida_no_banco(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        post = await cliente_http.post("/analyze", json=proposta_exemplo)

    analise_id = post.json()["id"]
    get = await cliente_http.get(f"/analyses/{analise_id}")

    assert get.status_code == 200
    assert get.json()["titulo"] == proposta_exemplo["titulo"]
    assert get.json()["resultado"]["complexity"] == "alta"


@pytest.mark.asyncio
async def test_analisar_proposta_corpo_vazio(cliente_http):
    assert (await cliente_http.post("/analyze", json={})).status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_titulo_curto(cliente_http):
    payload = {
        "titulo": "OK",
        "descricao": "Descrição suficientemente longa para passar na validação mínima do Pydantic.",
        "prazo_cliente": "1 mês",
        "tecnologias": ["Python"],
        "nivel_freelancer": "junior",
        "valor_hora": 50.0,
    }
    assert (await cliente_http.post("/analyze", json=payload)).status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_descricao_curta(cliente_http):
    payload = {
        "titulo": "Título válido para o teste",
        "descricao": "Curta",
        "prazo_cliente": "1 mês",
        "tecnologias": ["Python"],
        "nivel_freelancer": "junior",
        "valor_hora": 50.0,
    }
    assert (await cliente_http.post("/analyze", json=payload)).status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_valor_hora_negativo(cliente_http):
    payload = {
        "titulo": "Título válido para o teste",
        "descricao": "Descrição suficientemente longa para passar na validação mínima do Pydantic.",
        "prazo_cliente": "1 mês",
        "tecnologias": ["Python"],
        "nivel_freelancer": "senior",
        "valor_hora": -50.0,
    }
    assert (await cliente_http.post("/analyze", json=payload)).status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_nivel_invalido(cliente_http, proposta_exemplo):
    payload = {**proposta_exemplo, "nivel_freelancer": "estagiario"}
    assert (await cliente_http.post("/analyze", json=payload)).status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_tecnologias_vazias(cliente_http, proposta_exemplo):
    payload = {**proposta_exemplo, "tecnologias": []}
    assert (await cliente_http.post("/analyze", json=payload)).status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_tecnologias_so_espacos(cliente_http, proposta_exemplo):
    payload = {**proposta_exemplo, "tecnologias": ["   ", "  "]}
    assert (await cliente_http.post("/analyze", json=payload)).status_code == 422


# ══════════════════════════════════════════════════════════════
# GET /analyses  (resposta paginada)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_listar_analises_banco_vazio(cliente_http):
    response = await cliente_http.get("/analyses")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["itens"] == []
    assert data["pagina"] == 1
    assert data["total_paginas"] == 0


@pytest.mark.asyncio
async def test_listar_analises_metadados_paginacao(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        for i in range(1, 6):
            await cliente_http.post("/analyze", json={**proposta_exemplo, "titulo": f"Projeto {i}"})

    p1 = await cliente_http.get("/analyses?limite=3&pagina=1")
    p2 = await cliente_http.get("/analyses?limite=3&pagina=2")

    assert p1.status_code == 200
    d1 = p1.json()
    assert d1["total"] == 5
    assert d1["total_paginas"] == 2
    assert d1["pagina"] == 1
    assert d1["limite"] == 3
    assert len(d1["itens"]) == 3

    assert p2.status_code == 200
    d2 = p2.json()
    assert d2["pagina"] == 2
    assert len(d2["itens"]) == 2

    ids_p1 = {a["id"] for a in d1["itens"]}
    ids_p2 = {a["id"] for a in d2["itens"]}
    assert ids_p1.isdisjoint(ids_p2), "Páginas não devem conter registros duplicados"


@pytest.mark.asyncio
async def test_listar_analises_ordem_decrescente(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        await cliente_http.post("/analyze", json={**proposta_exemplo, "titulo": "Projeto Antigo"})
        await cliente_http.post("/analyze", json={**proposta_exemplo, "titulo": "Projeto Recente"})

    data = (await cliente_http.get("/analyses")).json()
    assert data["itens"][0]["titulo"] == "Projeto Recente"


@pytest.mark.asyncio
async def test_listar_analises_filtro_complexidade(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        await cliente_http.post("/analyze", json=proposta_exemplo)

    alta = (await cliente_http.get("/analyses?complexidade=alta")).json()
    baixa = (await cliente_http.get("/analyses?complexidade=baixa")).json()

    assert alta["total"] == 1
    assert baixa["total"] == 0


@pytest.mark.asyncio
async def test_listar_analises_campos_obrigatorios(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        await cliente_http.post("/analyze", json=proposta_exemplo)

    item = (await cliente_http.get("/analyses")).json()["itens"][0]
    campos = {"id", "titulo", "complexidade", "preco_min", "preco_max",
              "horas_min", "horas_max", "nivel_freelancer", "criado_em"}
    assert campos.issubset(item.keys())


@pytest.mark.asyncio
async def test_listar_analises_limite_invalido(cliente_http):
    assert (await cliente_http.get("/analyses?limite=0")).status_code == 422


# ══════════════════════════════════════════════════════════════
# GET /analyses/{id}
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_buscar_analise_por_id_sucesso(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        analise_id = (await cliente_http.post("/analyze", json=proposta_exemplo)).json()["id"]

    response = await cliente_http.get(f"/analyses/{analise_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == analise_id
    assert data["titulo"] == proposta_exemplo["titulo"]
    assert "scope_summary" in data["resultado"]


@pytest.mark.asyncio
async def test_buscar_analise_nao_encontrada(cliente_http):
    response = await cliente_http.get("/analyses/99999")
    assert response.status_code == 404
    assert "não encontrada" in response.json()["detail"]


@pytest.mark.asyncio
async def test_buscar_analise_id_invalido(cliente_http):
    assert (await cliente_http.get("/analyses/abc")).status_code == 422


# ══════════════════════════════════════════════════════════════
# GET /stats
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_estatisticas_banco_vazio(cliente_http):
    response = await cliente_http.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_analises"] == 0
    assert data["preco_medio"]["min"] == 0.0
    assert data["preco_medio"]["max"] == 0.0
    assert data["horas_medias"]["min"] == 0.0
    assert data["por_complexidade"] == {}


@pytest.mark.asyncio
async def test_estatisticas_com_dados(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        await cliente_http.post("/analyze", json=proposta_exemplo)
        await cliente_http.post("/analyze", json={**proposta_exemplo, "titulo": "Segundo Projeto"})

    response = await cliente_http.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_analises"] == 2
    assert data["preco_medio"]["min"] == 14400.0
    assert data["preco_medio"]["max"] == 23400.0
    assert data["horas_medias"]["min"] == 160.0
    assert data["por_complexidade"].get("alta") == 2


# ══════════════════════════════════════════════════════════════
# GET /health
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health_check(cliente_http):
    response = await cliente_http.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "versao" in data
    assert "app" in data
