import json
import re
import anthropic
from app.core.config import settings
from app.core.schemas import (
    EntradaProposta,
    ResultadoAnalise,
    HorasEstimadas,
    PrecoSugerido,
    Complexidade,
)


TEMPLATE_ANALISE = """
Você é um especialista sênior em análise e precificação de projetos de tecnologia no mercado brasileiro, com mais de 15 anos de experiência avaliando propostas freelance nas áreas de desenvolvimento web, mobile e sistemas.

Analise com profundidade a proposta abaixo e forneça uma análise técnica detalhada.

═══════════════════════════════════════════════════
DADOS DA PROPOSTA
═══════════════════════════════════════════════════
Título:             {titulo}
Prazo do Cliente:   {prazo_cliente}
Tecnologias:        {tecnologias}
Nível do Freelancer:{nivel_freelancer}
Valor Hora (BRL):   R$ {valor_hora:.2f}

DESCRIÇÃO COMPLETA:
{descricao}
═══════════════════════════════════════════════════

INSTRUÇÕES PARA A ANÁLISE:
1. Leia a descrição com atenção e identifique TODOS os requisitos, explícitos e implícitos.
2. Considere o nível do freelancer ao estimar horas e complexidade técnica.
3. Some todas as funcionalidades para calcular uma estimativa de horas realista.
4. Calcule o preço sugerido com base no valor hora × horas estimadas.
5. Identifique riscos reais do projeto, não genéricos.
6. Identifique red flags que podem indicar problemas futuros (escopo aberto, prazo irreal, etc.).
7. Formule perguntas específicas que devem ser feitas ao cliente antes de aceitar.
8. A recomendação deve ser objetiva: aceitar, negociar (com condições) ou recusar (com motivo).

Retorne APENAS um objeto JSON válido, sem markdown, sem texto adicional, com a seguinte estrutura:

{{
  "scope_summary": "Resumo técnico e objetivo de todos os requisitos identificados na proposta (2-4 frases)",
  "estimated_hours": {{
    "min": <inteiro - estimativa otimista considerando tudo correndo bem>,
    "max": <inteiro - estimativa realista com imprevistos típicos>
  }},
  "suggested_price": {{
    "min": <decimal - valor_hora × horas_min>,
    "max": <decimal - valor_hora × horas_max>,
    "currency": "BRL"
  }},
  "complexity": "<baixa|media|alta|muito_alta>",
  "risks": [
    "Risco específico 1 identificado na proposta",
    "Risco específico 2",
    "..."
  ],
  "red_flags": [
    "Ponto de atenção 1 que pode gerar problemas",
    "..."
  ],
  "questions_to_ask": [
    "Pergunta específica 1 para o cliente",
    "Pergunta específica 2",
    "..."
  ],
  "recommendation": "Recomendação objetiva: aceitar / negociar (com condições específicas) / recusar (com motivo claro). Seja direto e justifique."
}}
"""


class AnalisadorDePropostas:
    def __init__(self) -> None:
        self._cliente = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._modelo = "claude-sonnet-4-6"
        self._max_tokens = 2048

    async def analisar(self, entrada: EntradaProposta) -> ResultadoAnalise:
        prompt = self._montar_prompt(entrada)
        resposta_bruta = await self._processar(prompt)
        dados = self._extrair_json(resposta_bruta)
        return self._construir_resultado(dados, entrada.valor_hora)

    def _montar_prompt(self, entrada: EntradaProposta) -> str:
        tecnologias_str = ", ".join(entrada.tecnologias) if entrada.tecnologias else "Não especificadas"
        nivel_map = {"junior": "Júnior", "pleno": "Pleno", "senior": "Sênior"}
        nivel_str = nivel_map.get(entrada.nivel_freelancer.value, entrada.nivel_freelancer.value)

        return TEMPLATE_ANALISE.format(
            titulo=entrada.titulo,
            prazo_cliente=entrada.prazo_cliente,
            tecnologias=tecnologias_str,
            nivel_freelancer=nivel_str,
            valor_hora=entrada.valor_hora,
            descricao=entrada.descricao,
        )

    async def _processar(self, prompt: str) -> str:
        mensagem = await self._cliente.messages.create(
            model=self._modelo,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return mensagem.content[0].text

    def _extrair_json(self, texto: str) -> dict:
        texto = texto.strip()

        bloco_json = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", texto)
        if bloco_json:
            texto = bloco_json.group(1).strip()

        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            inicio = texto.find("{")
            fim = texto.rfind("}") + 1
            if inicio != -1 and fim > inicio:
                try:
                    return json.loads(texto[inicio:fim])
                except json.JSONDecodeError:
                    pass

        raise ValueError(f"Não foi possível extrair JSON válido da resposta: {texto[:200]}")

    def _construir_resultado(self, dados: dict, valor_hora: float) -> ResultadoAnalise:
        horas = dados.get("estimated_hours", {})
        preco = dados.get("suggested_price", {})

        horas_min = int(horas.get("min", 1))
        horas_max = int(horas.get("max", horas_min + 10))

        preco_min = float(preco.get("min", horas_min * valor_hora))
        preco_max = float(preco.get("max", horas_max * valor_hora))

        complexidade_raw = dados.get("complexity", "media").lower().replace(" ", "_")
        mapa_complexidade = {
            "baixa": Complexidade.BAIXA,
            "media": Complexidade.MEDIA,
            "média": Complexidade.MEDIA,
            "alta": Complexidade.ALTA,
            "muito_alta": Complexidade.MUITO_ALTA,
            "muito alta": Complexidade.MUITO_ALTA,
        }
        complexidade = mapa_complexidade.get(complexidade_raw, Complexidade.MEDIA)

        return ResultadoAnalise(
            scope_summary=dados.get("scope_summary", "Escopo não identificado."),
            estimated_hours=HorasEstimadas(min=horas_min, max=horas_max),
            suggested_price=PrecoSugerido(min=preco_min, max=preco_max, currency="BRL"),
            complexity=complexidade,
            risks=dados.get("risks", []),
            red_flags=dados.get("red_flags", []),
            questions_to_ask=dados.get("questions_to_ask", []),
            recommendation=dados.get("recommendation", "Analise com cautela."),
        )


analisador = AnalisadorDePropostas()
