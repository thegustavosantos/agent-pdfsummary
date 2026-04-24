import anthropic
import json
from config import MODELO_AGENTES

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Você é um engenheiro sênior especializado em revisão de código e detecção de regressões.
Sua função é comparar duas versões de um mesmo script Python e identificar o que evoluiu, regrediu ou foi perdido.
Responda sempre em JSON válido, sem texto fora do JSON."""


def executar(codigo_anterior: str, codigo_novo: str, qa_anterior: dict) -> dict:
    """
    Compara duas versões do código gerado pelo pipeline.

    Recebe:
        codigo_anterior : código da run anterior
        codigo_novo     : código da run atual
        qa_anterior     : resultado do QA da run anterior (para contexto)

    Retorna dict com:
        evolucoes      : o que melhorou em relação à versão anterior
        regressoes     : funcionalidades ou tratamentos que existiam antes e sumiram
        neutro         : mudanças sem impacto claro (refatorações, renomeações)
        aprovado       : bool — True se não há regressões críticas
        parecer        : texto resumido da comparação
    """

    bugs_anteriores = qa_anterior.get("bugs", [])
    veredito_anterior = qa_anterior.get("veredito", "desconhecido")

    prompt = f"""Compare as duas versões do script Python abaixo.

<versao_anterior>
{codigo_anterior}
</versao_anterior>

<versao_nova>
{codigo_novo}
</versao_nova>

Contexto do QA da versão anterior:
- Veredito: {veredito_anterior}
- Bugs reportados: {json.dumps(bugs_anteriores, ensure_ascii=False)}

Responda APENAS com JSON neste formato exato:
{{
  "evolucoes": ["descrição do que melhorou 1", "descrição do que melhorou 2"],
  "regressoes": ["descrição da regressão 1"],
  "neutro": ["mudança neutra 1"],
  "aprovado": true | false,
  "parecer": "texto resumido em 2-3 linhas comparando as versões"
}}

Regras:
- "regressoes" deve listar apenas perdas funcionais reais — tratamento de erro que sumiu, validação removida, comportamento alterado para pior
- "aprovado" é false se houver qualquer regressão crítica
- Se não houver versão anterior significativa para comparar, retorne listas vazias e aprovado: true"""

    resposta = client.messages.create(
        model=MODELO_AGENTES,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    texto = resposta.content[0].text.strip()

    if texto.startswith("```"):
        texto = "\n".join(texto.split("\n")[1:-1])

    return json.loads(texto)
