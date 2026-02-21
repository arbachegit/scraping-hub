"""
Response Formatter - Uses LLM to generate conversational responses.

This module transforms raw query results into natural language responses
with the Atlas personality.
"""

import json
from typing import Any, Dict, List, Optional

import structlog

from api.agent.ai_providers.chain import get_provider_chain
from api.agent.models import ParsedIntent

logger = structlog.get_logger()

# Atlas system prompt - the conversational AI personality
ATLAS_SYSTEM_PROMPT = """Você é o Atlas, um agente inteligente de consulta de dados políticos e empresariais brasileiros.

## Sua Personalidade
- Especialista em dados políticos brasileiros
- Comunicativo, claro e objetivo
- Usa português brasileiro natural
- Fornece insights relevantes sobre os dados
- Sugere perguntas de acompanhamento úteis

## Ao Responder
1. Comece com uma síntese dos resultados encontrados
2. Destaque informações relevantes (partidos, cargos, municípios, eleições)
3. Se houver padrões interessantes nos dados, mencione-os
4. Termine sugerindo 2-3 perguntas de acompanhamento relacionadas

## Formato da Resposta
Responda em JSON:
{
  "text": "Resposta conversacional em português brasileiro",
  "highlights": ["ponto relevante 1", "ponto relevante 2"],
  "suggestions": ["Pergunta sugerida 1?", "Pergunta sugerida 2?", "Pergunta sugerida 3?"]
}

IMPORTANTE: Responda APENAS com JSON válido, sem markdown ou explicações adicionais."""


def _format_data_for_prompt(data: List[Dict[str, Any]], limit: int = 10) -> str:
    """Format data sample for inclusion in prompt."""
    if not data:
        return "Nenhum dado encontrado."

    sample = data[:limit]
    formatted = []

    for item in sample:
        # Build a concise representation
        parts = []

        # Handle politicos
        if "nome_completo" in item or "nome_urna" in item:
            nome = item.get("nome_urna") or item.get("nome_completo", "")
            if nome:
                parts.append(f"Nome: {nome}")

            if item.get("partido_sigla"):
                parts.append(f"Partido: {item['partido_sigla']}")

            if item.get("cargo_atual") or item.get("cargo"):
                cargo = item.get("cargo_atual") or item.get("cargo")
                parts.append(f"Cargo: {cargo}")

            if item.get("municipio"):
                parts.append(f"Município: {item['municipio']}")

            if item.get("ano_eleicao"):
                parts.append(f"Eleição: {item['ano_eleicao']}")

            if item.get("eleito") is not None:
                eleito = "Eleito" if item["eleito"] else "Não eleito"
                parts.append(eleito)

            if item.get("sexo"):
                sexo = "Feminino" if item["sexo"] == "F" else "Masculino"
                parts.append(f"Sexo: {sexo}")

        # Handle empresas
        elif "razao_social" in item or "nome_fantasia" in item:
            nome = item.get("nome_fantasia") or item.get("razao_social", "")
            if nome:
                parts.append(f"Empresa: {nome}")

            if item.get("cnpj"):
                parts.append(f"CNPJ: {item['cnpj']}")

            if item.get("cidade") and item.get("estado"):
                parts.append(f"Local: {item['cidade']}/{item['estado']}")

            if item.get("regime_tributario"):
                parts.append(f"Regime: {item['regime_tributario']}")

        # Handle pessoas
        elif "cargo" in item and "email" in item:
            nome = item.get("nome_completo", "")
            if nome:
                parts.append(f"Nome: {nome}")
            if item.get("cargo"):
                parts.append(f"Cargo: {item['cargo']}")

        # Generic fallback
        if not parts:
            for key, value in list(item.items())[:5]:
                if value and key != "id":
                    parts.append(f"{key}: {value}")

        formatted.append(" | ".join(parts))

    return "\n".join(formatted)


def _build_context_description(intent: ParsedIntent) -> str:
    """Build a context description from the intent."""
    parts = []

    # Entity type
    entity_names = {
        "empresas": "empresas",
        "pessoas": "pessoas",
        "noticias": "notícias",
        "politicos": "políticos",
    }
    parts.append(f"Tipo de consulta: {entity_names.get(intent.entity_type, intent.entity_type)}")

    # Filters
    if intent.filters:
        filter_parts = []
        for f in intent.filters:
            field = f.field
            value = f.value

            # Human-readable field names
            field_names = {
                "partido_sigla": "partido",
                "cargo": "cargo",
                "municipio": "município",
                "estado": "estado",
                "ano_eleicao": "ano da eleição",
                "eleito": "eleito",
                "sexo": "sexo",
                "nome_completo": "nome",
                "nome_urna": "nome de urna",
            }

            readable_field = field_names.get(field, field)

            # Format value
            if field == "sexo":
                value = "feminino" if value == "F" else "masculino"
            elif field == "eleito":
                value = "sim" if value else "não"

            filter_parts.append(f"{readable_field}: {value}")

        parts.append(f"Filtros: {', '.join(filter_parts)}")

    return "\n".join(parts)


async def generate_conversational_response(
    intent: ParsedIntent,
    data: List[Dict[str, Any]],
    total_count: int,
    external_info: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a conversational response using LLM.

    Args:
        intent: The parsed intent
        data: Query results
        total_count: Total count of matching records
        external_info: External information from Perplexity (if any)

    Returns:
        Dict with 'text', 'highlights', and 'suggestions'
    """
    chain = get_provider_chain()

    if not chain.has_providers:
        logger.warning("no_ai_providers_available")
        return _generate_fallback_response(intent, data, total_count)

    # Build the user prompt
    context = _build_context_description(intent)
    data_sample = _format_data_for_prompt(data, limit=15)

    user_prompt = f"""## Contexto da Consulta
{context}

## Resultados Encontrados
Total: {total_count} registro(s)

{data_sample}
"""

    if external_info:
        user_prompt += f"""
## Informação Externa (Perplexity)
{external_info}
"""

    user_prompt += """
## Tarefa
Analise os dados acima e gere uma resposta conversacional informativa.
Responda em JSON com os campos: text, highlights, suggestions"""

    try:
        response = await chain.complete(
            prompt=user_prompt,
            system_prompt=ATLAS_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=1500,
        )

        if response.success and response.content:
            return _parse_llm_response(response.content, intent, data, total_count)

        logger.warning(
            "llm_response_failed",
            error=response.error,
            provider=response.provider,
        )
        return _generate_fallback_response(intent, data, total_count)

    except Exception as e:
        logger.error("response_generation_error", error=str(e))
        return _generate_fallback_response(intent, data, total_count)


def _parse_llm_response(
    content: str,
    intent: ParsedIntent,
    data: List[Dict[str, Any]],
    total_count: int,
) -> Dict[str, Any]:
    """Parse the LLM response, falling back to extraction if JSON fails."""
    import re

    try:
        # Try to extract JSON from the content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            parsed = json.loads(json_match.group())

            return {
                "text": parsed.get("text", content),
                "highlights": parsed.get("highlights", []),
                "suggestions": parsed.get("suggestions", _generate_default_suggestions(intent)),
            }

    except json.JSONDecodeError:
        pass

    # If JSON parsing fails, use the content as text
    return {
        "text": content,
        "highlights": [],
        "suggestions": _generate_default_suggestions(intent),
    }


def _generate_fallback_response(
    intent: ParsedIntent,
    data: List[Dict[str, Any]],
    total_count: int,
) -> Dict[str, Any]:
    """Generate a fallback response without LLM."""
    entity_names = {
        "empresas": ("empresa", "empresas"),
        "pessoas": ("pessoa", "pessoas"),
        "noticias": ("notícia", "notícias"),
        "politicos": ("político", "políticos"),
    }

    singular, plural = entity_names.get(intent.entity_type, ("item", "itens"))

    if total_count == 0:
        text = f"Não encontrei nenhum(a) {singular} com os critérios informados. Tente ajustar os filtros."
    elif total_count == 1:
        text = f"Encontrei 1 {singular}."
        if data and intent.entity_type == "politicos":
            item = data[0]
            nome = item.get("nome_urna") or item.get("nome_completo", "")
            partido = item.get("partido_sigla", "")
            cargo = item.get("cargo_atual") or item.get("cargo", "")
            if nome:
                text = f"Encontrei {nome}"
                if partido:
                    text += f" ({partido})"
                if cargo:
                    text += f", {cargo}"
                text += "."
    else:
        text = f"Encontrei {total_count} {plural}."
        if len(data) < total_count:
            text += f" Mostrando os primeiros {len(data)}."

    return {
        "text": text,
        "highlights": [],
        "suggestions": _generate_default_suggestions(intent),
    }


def _generate_default_suggestions(intent: ParsedIntent) -> List[str]:
    """Generate default follow-up suggestions based on intent."""
    if intent.entity_type == "politicos":
        # Check what filters are already applied
        has_party = any(f.field in ("partido_sigla", "partido") for f in intent.filters)
        has_cargo = any(f.field == "cargo" for f in intent.filters)
        has_municipio = any(f.field in ("municipio", "cidade") for f in intent.filters)
        has_year = any(f.field == "ano_eleicao" for f in intent.filters)

        suggestions = []

        if not has_party:
            suggestions.append("Quais são os principais partidos representados?")
        if not has_cargo:
            suggestions.append("Quantos foram eleitos para cada cargo?")
        if not has_municipio:
            suggestions.append("Quais municípios têm mais representantes?")
        if not has_year:
            suggestions.append("Como foi o desempenho nas eleições de 2024?")

        # Always add some general suggestions
        suggestions.extend([
            "Quais políticos foram reeleitos?",
            "Qual a distribuição por gênero?",
        ])

        return suggestions[:3]

    elif intent.entity_type == "empresas":
        return [
            "Quais são as maiores por capital social?",
            "Quantas são do Simples Nacional?",
            "Quais os principais segmentos (CNAE)?",
        ]

    elif intent.entity_type == "pessoas":
        return [
            "Quais os cargos mais comuns?",
            "Quantos têm LinkedIn cadastrado?",
            "Buscar em outra empresa?",
        ]

    return [
        "Posso ajudar com mais alguma consulta?",
        "Deseja filtrar por outros critérios?",
        "Quer ver mais detalhes de algum registro?",
    ]
