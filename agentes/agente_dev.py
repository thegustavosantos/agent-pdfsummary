import anthropic
from config import MODELO_AGENTES, MODELO_GERADO

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Você é um desenvolvedor Python sênior especializado em scripts CLI.
Sua função é receber requisitos e entregar um script Python completo, funcional e pronto para rodar.

Regras obrigatórias:
- Entregue SEMPRE um script CLI — sem Streamlit, Flask, FastAPI ou qualquer framework web
- O script deve ser executável via terminal: python resumidor.py arquivo.pdf
- Escreva o script COMPLETO do início ao fim — nunca truncar ou usar reticências no meio do código
- Apenas o código Python, sem explicações fora do código"""

def executar(requisitos: str, plano: str = None, feedback_qa: str = None) -> str:
    """
    Recebe requisitos do PO e plano técnico do Arquiteto e retorna código Python.
    Se feedback_qa for fornecido, corrige o código anterior com base no parecer do QA.
    """

    if feedback_qa:
        prompt = f"""O QA reprovou ou pediu correcoes no seu codigo anterior.

<feedback_qa>
{feedback_qa}
</feedback_qa>

<requisitos_originais>
{requisitos}
</requisitos_originais>

<plano_tecnico>
{plano or "Sem plano disponivel — use seu julgamento."}
</plano_tecnico>

Corrija todos os problemas apontados pelo QA seguindo o plano tecnico.
Entregue o codigo COMPLETO revisado. Nao use reticencias nem deixe funcoes incompletas."""
    else:
        prompt = f"""Implemente o script Python CLI abaixo seguindo EXATAMENTE o plano tecnico do Arquiteto.

<requisitos_po>
{requisitos}
</requisitos_po>

<plano_tecnico>
{plano or "Sem plano disponivel — use seu julgamento."}
</plano_tecnico>

Instrucoes:
1. Siga o plano tecnico a risca: use os nomes de funcoes, parametros e retornos definidos
2. Implemente TODOS os pontos de falha listados no plano
3. Use PyMuPDF (fitz) para extracao de texto e anthropic para o resumo
4. Use SEMPRE o modelo "{MODELO_GERADO}" na chamada à API — ignore qualquer outro modelo que apareça no plano
5. Adicione comentarios explicando cada bloco
6. Use argparse conforme o plano define

IMPORTANTE: Escreva o script inteiro, do import ate a ultima linha. Nunca truncar."""

    resposta = client.messages.create(
        model=MODELO_AGENTES,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return resposta.content[0].text.strip()
