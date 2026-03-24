from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


PATCH_ANALISAR = "app.api.routes.analysis.obter_analisador"


def _mock_analisador(resultado_mock):
    instancia = AsyncMock()
    instancia.analisar = AsyncMock(return_value=resultado_mock)
    return instancia


# ──────────────────────────────────────────────────────────────
# POST /analyze
# ──────────────────────────────────────────────────────────────

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
async def test_analisar_proposta_salva_no_banco(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        post_resp = await cliente_http.post("/analyze", json=proposta_exemplo)

    analise_id = post_resp.json()["id"]
    get_resp = await cliente_http.get(f"/analyses/{analise_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["titulo"] == proposta_exemplo["titulo"]


@pytest.mark.asyncio
async def test_analisar_proposta_corpo_vazio(cliente_http):
    response = await cliente_http.post("/analyze", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_titulo_curto(cliente_http):
    payload = {
        "titulo": "OK",
        "descricao": "Descrição com tamanho suficiente para passar na validação mínima do Pydantic.",
        "prazo_cliente": "1 mês",
        "tecnologias": ["Python"],
        "nivel_freelancer": "junior",
        "valor_hora": 50.0,
    }
    response = await cliente_http.post("/analyze", json=payload)
    assert response.status_code == 422


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
    response = await cliente_http.post("/analyze", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_valor_hora_negativo(cliente_http):
    payload = {
        "titulo": "Título válido para o teste",
        "descricao": "Descrição com tamanho suficiente para passar na validação mínima do Pydantic.",
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
async def test_analisar_proposta_tecnologias_vazias(cliente_http, proposta_exemplo):
    payload = {**proposta_exemplo, "tecnologias": []}
    response = await cliente_http.post("/analyze", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analisar_proposta_tecnologias_so_espacos(cliente_http, proposta_exemplo):
    payload = {**proposta_exemplo, "tecnologias": ["   ", "  "]}
    response = await cliente_http.post("/analyze", json=payload)
    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────
# GET /analyses
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_listar_analises_banco_vazio(cliente_http):
    response = await cliente_http.get("/analyses")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_listar_analises_ordem_decrescente(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        await cliente_http.post("/analyze", json={**proposta_exemplo, "titulo": "Projeto Antigo"})
        await cliente_http.post("/analyze", json={**proposta_exemplo, "titulo": "Projeto Recente"})

    response = await cliente_http.get("/analyses")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["titulo"] == "Projeto Recente"


@pytest.mark.asyncio
async def test_listar_analises_filtro_complexidade_alta(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        await cliente_http.post("/analyze", json=proposta_exemplo)

    response_alta = await cliente_http.get("/analyses?complexidade=alta")
    assert response_alta.status_code == 200
    assert len(response_alta.json()) == 1

    response_baixa = await cliente_http.get("/analyses?complexidade=baixa")
    assert response_baixa.status_code == 200
    assert len(response_baixa.json()) == 0


@pytest.mark.asyncio
async def test_listar_analises_paginacao(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        for i in range(1, 6):
            await cliente_http.post("/analyze", json={**proposta_exemplo, "titulo": f"Projeto {i}"})

    p1 = await cliente_http.get("/analyses?limite=3&pagina=1")
    p2 = await cliente_http.get("/analyses?limite=3&pagina=2")

    assert p1.status_code == 200
    assert p2.status_code == 200
    assert len(p1.json()) == 3
    assert len(p2.json()) == 2

    ids_p1 = {a["id"] for a in p1.json()}
    ids_p2 = {a["id"] for a in p2.json()}
    assert ids_p1.isdisjoint(ids_p2), "Páginas não devem ter registros duplicados"


@pytest.mark.asyncio
async def test_listar_analises_limite_invalido(cliente_http):
    response = await cliente_http.get("/analyses?limite=0")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_listar_analises_campos_retornados(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        await cliente_http.post("/analyze", json=proposta_exemplo)

    response = await cliente_http.get("/analyses")
    item = response.json()[0]

    campos_obrigatorios = {"id", "titulo", "complexidade", "preco_min", "preco_max",
                           "horas_min", "horas_max", "nivel_freelancer", "criado_em"}
    assert campos_obrigatorios.issubset(item.keys())


# ──────────────────────────────────────────────────────────────
# GET /analyses/{id}
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_buscar_analise_por_id_sucesso(cliente_http, proposta_exemplo, resultado_mock):
    with patch(PATCH_ANALISAR, return_value=_mock_analisador(resultado_mock)):
        post = await cliente_http.post("/analyze", json=proposta_exemplo)

    analise_id = post.json()["id"]
    response = await cliente_http.get(f"/analyses/{analise_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == analise_id
    assert data["titulo"] == proposta_exemplo["titulo"]
    assert "resultado" in data
    assert "scope_summary" in data["resultado"]


@pytest.mark.asyncio
async def test_buscar_analise_nao_encontrada(cliente_http):
    response = await cliente_http.get("/analyses/99999")
    assert response.status_code == 404
    assert "não encontrada" in response.json()["detail"]


@pytest.mark.asyncio
async def test_buscar_analise_id_invalido(cliente_http):
    response = await cliente_http.get("/analyses/abc")
    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────
# Sistema
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(cliente_http):
    response = await cliente_http.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "versao" in data
    assert "app" in data
