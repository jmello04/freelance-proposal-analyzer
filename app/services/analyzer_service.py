from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic

from app.core.config import settings
from app.core.schemas import (
    Complexidade,
    EntradaProposta,
    HorasEstimadas,
    NivelFreelancer,
    PrecoSugerido,
    ResultadoAnalise,
)

logger = logging.getLogger(__name__)

_NIVEL_LABELS: dict[str, str] = {
    NivelFreelancer.JUNIOR: "Júnior",
    NivelFreelancer.PLENO: "Pleno",
    NivelFreelancer.SENIOR: "Sênior",
}

_COMPLEXIDADE_MAP: dict[str, Complexidade] = {
    "baixa": Complexidade.BAIXA,
    "media": Complexidade.MEDIA,
    "média": Complexidade.MEDIA,
    "alta": Complexidade.ALTA,
    "muito_alta": Complexidade.MUITO_ALTA,
    "muito alta": Complexidade.MUITO_ALTA,
}

_TEMPLATE_PROMPT = """\
Você é um especialista sênior em análise e precificação de projetos de tecnologia \
no mercado brasileiro, com mais de 15 anos de experiência avaliando propostas \
freelance em desenvolvimento web, mobile e sistemas corporativos.

Analise com profundidade técnica a proposta abaixo e retorne uma avaliação detalhada.

═══════════════════════════════════════════════════════
DADOS DA PROPOSTA
═══════════════════════════════════════════════════════
Título:              {titulo}
Prazo do Cliente:    {prazo_cliente}
Tecnologias:         {tecnologias}
Nível do Freelancer: {nivel_freelancer}
Valor Hora (BRL):    R$ {valor_hora:.2f}

DESCRIÇÃO COMPLETA:
{descricao}
═══════════════════════════════════════════════════════

INSTRUÇÕES:
1. Identifique TODOS os requisitos, explícitos e implícitos na descrição.
2. Considere o nível do freelancer ao estimar a complexidade e o tempo.
3. Calcule a estimativa de horas contemplando: desenvolvimento, testes, ajustes e deploy.
4. O preço sugerido deve ser: valor_hora × horas_estimadas.
5. Aponte riscos reais e específicos deste projeto — não riscos genéricos.
6. Red flags são situações que podem gerar conflito ou prejuízo: escopo aberto, \
prazo irreal, orçamento inconsistente, requisitos contraditórios.
7. Formule perguntas que esclarecem ambiguidades antes de fechar o contrato.
8. A recomendação deve ser objetiva: ACEITAR, NEGOCIAR (com condições claras) \
ou RECUSAR (com motivo).

Retorne EXCLUSIVAMENTE um objeto JSON válido, sem markdown, sem texto adicional:

{{
  "scope_summary": "Resumo técnico e objetivo de todos os requisitos identificados (2-4 frases)",
  "estimated_hours": {{
    "min": <inteiro - cenário otimista>,
    "max": <inteiro - cenário realista com imprevistos>
  }},
  "suggested_price": {{
    "min": <decimal - valor_hora × horas_min>,
    "max": <decimal - valor_hora × horas_max>,
    "currency": "BRL"
  }},
  "complexity": "<baixa|media|alta|muito_alta>",
  "risks": [
    "Risco específico 1",
    "Risco específico 2"
  ],
  "red_flags": [
    "Ponto de atenção crítico 1"
  ],
  "questions_to_ask": [
    "Pergunta estratégica 1 para o cliente",
    "Pergunta estratégica 2"
  ],
  "recommendation": "ACEITAR/NEGOCIAR/RECUSAR — justificativa clara e objetiva."
}}
"""


class AnalisadorDePropostas:
    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY não configurada. "
                "Defina no arquivo .env antes de iniciar o servidor."
            )
        self._cliente = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._modelo = settings.ANALYSIS_MODEL
        self._max_tokens = settings.ANALYSIS_MAX_TOKENS
        logger.info("AnalisadorDePropostas inicializado. Modelo: %s", self._modelo)

    async def analisar(self, entrada: EntradaProposta) -> ResultadoAnalise:
        logger.info("Iniciando análise: '%s' | nível=%s", entrada.titulo, entrada.nivel_freelancer)
        prompt = self._montar_prompt(entrada)

        try:
            resposta_bruta = await self._chamar_api(prompt)
        except anthropic.AuthenticationError as exc:
            logger.error("Falha de autenticação na API: %s", exc)
            raise
        except anthropic.RateLimitError as exc:
            logger.warning("Limite de requisições atingido: %s", exc)
            raise
        except anthropic.APIStatusError as exc:
            logger.error("Erro na API (status %s): %s", exc.status_code, exc.message)
            raise
        except Exception as exc:
            logger.error("Erro inesperado ao chamar API: %s", exc)
            raise

        dados = self._extrair_json(resposta_bruta)
        resultado = self._construir_resultado(dados, entrada.valor_hora)
        logger.info(
            "Análise concluída: complexidade=%s | horas=%d-%d | preço=R$%.0f-R$%.0f",
            resultado.complexity.value,
            resultado.estimated_hours.min,
            resultado.estimated_hours.max,
            resultado.suggested_price.min,
            resultado.suggested_price.max,
        )
        return resultado

    def _montar_prompt(self, entrada: EntradaProposta) -> str:
        tecnologias_str = ", ".join(entrada.tecnologias)
        nivel_str = _NIVEL_LABELS.get(entrada.nivel_freelancer, entrada.nivel_freelancer.value)
        return _TEMPLATE_PROMPT.format(
            titulo=entrada.titulo,
            prazo_cliente=entrada.prazo_cliente,
            tecnologias=tecnologias_str,
            nivel_freelancer=nivel_str,
            valor_hora=entrada.valor_hora,
            descricao=entrada.descricao,
        )

    async def _chamar_api(self, prompt: str) -> str:
        mensagem = await self._cliente.messages.create(
            model=self._modelo,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return mensagem.content[0].text

    def _extrair_json(self, texto: str) -> dict[str, Any]:
        texto = texto.strip()

        bloco = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", texto)
        if bloco:
            texto = bloco.group(1).strip()

        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            pass

        inicio = texto.find("{")
        fim = texto.rfind("}") + 1
        if inicio != -1 and fim > inicio:
            try:
                return json.loads(texto[inicio:fim])
            except json.JSONDecodeError:
                pass

        logger.error("JSON inválido recebido: %s", texto[:300])
        raise ValueError("Resposta em formato inválido. Tente novamente.")

    def _construir_resultado(self, dados: dict[str, Any], valor_hora: float) -> ResultadoAnalise:
        horas = dados.get("estimated_hours", {})
        preco = dados.get("suggested_price", {})

        horas_min = max(1, int(horas.get("min", 1)))
        horas_max = max(horas_min, int(horas.get("max", horas_min + 10)))

        preco_min = float(preco.get("min", horas_min * valor_hora))
        preco_max = float(preco.get("max", horas_max * valor_hora))
        preco_min = max(0.0, preco_min)
        preco_max = max(preco_min, preco_max)

        complexidade_raw = str(dados.get("complexity", "media")).lower().strip()
        complexidade = _COMPLEXIDADE_MAP.get(complexidade_raw, Complexidade.MEDIA)

        return ResultadoAnalise(
            scope_summary=str(dados.get("scope_summary", "")).strip() or "Escopo não identificado.",
            estimated_hours=HorasEstimadas(min=horas_min, max=horas_max),
            suggested_price=PrecoSugerido(min=preco_min, max=preco_max, currency="BRL"),
            complexity=complexidade,
            risks=list(dados.get("risks", [])),
            red_flags=list(dados.get("red_flags", [])),
            questions_to_ask=list(dados.get("questions_to_ask", [])),
            recommendation=str(dados.get("recommendation", "Analise com cautela.")).strip(),
        )


_instancia: AnalisadorDePropostas | None = None


def obter_analisador() -> AnalisadorDePropostas:
    global _instancia
    if _instancia is None:
        _instancia = AnalisadorDePropostas()
    return _instancia
