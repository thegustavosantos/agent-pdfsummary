import anthropic
import json

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Você é um engenheiro de QA sênior especializado em Python.
Sua função é analisar código, identificar bugs e verificar cobertura de requisitos.
Sempre responda em JSON válido, sem texto fora do JSON."""

# Possíveis vereditos
APROVADO            = "aprovado"
APROVADO_RESSALVAS  = "aprovado_com_ressalvas"
REPROVADO           = "reprovado"

def executar(codigo: str, requisitos: str) -> dict:
    """
    Analisa o código contra os requisitos.

    Retorna dict com:
        - veredito: "aprovado" | "aprovado_com_ressalvas" | "reprovado"
        - bugs: lista de problemas encontrados
        - cobertura: dict de RF/RNF → status
        - parecer: texto justificado
        - deve_reiterar: bool (True se Dev precisar corrigir)
    """

    prompt = f"""Analise o código abaixo contra os requisitos fornecidos.

<requisitos_po>
{requisitos}
</requisitos_po>

<codigo_dev>
{codigo}
</codigo_dev>

Responda APENAS com JSON neste formato exato:
{{
  "veredito": "aprovado" | "aprovado_com_ressalvas" | "reprovado",
  "bugs": ["descrição do bug 1", "descrição do bug 2"],
  "cobertura": {{
    "RF1": "atendido" | "parcial" | "ausente",
    "RF2": "atendido" | "parcial" | "ausente"
  }},
  "parecer": "texto justificado em 3-5 linhas",
  "deve_reiterar": true | false
}}

Regras para deve_reiterar:
- true  → se veredito for "reprovado" ou se houver bugs críticos
- false → se veredito for "aprovado" ou "aprovado_com_ressalvas" sem bugs críticos"""

    resposta = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    texto = resposta.content[0].text.strip()

    # Remove blocos de código markdown se o modelo os incluir
    if texto.startswith("```"):
        texto = "\n".join(texto.split("\n")[1:-1])

    return json.loads(texto)
