import anthropic

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Você é um desenvolvedor Python sênior.
Sua função é receber requisitos e entregar código funcional, bem comentado e pronto para rodar.
Entregue apenas o código Python, sem explicações fora do código.
Antes de escrever, liste as decisões técnicas que vai tomar.
"""

def executar(requisitos: str, feedback_qa: str = None) -> str:
    """
    Recebe requisitos do PO e retorna código Python.
    Se feedback_qa for fornecido, corrige o código anterior com base no parecer do QA.
    """

    if feedback_qa:
        prompt = f"""O QA reprovou ou pediu correções no seu código anterior.

<feedback_qa>
{feedback_qa}
</feedback_qa>

<requisitos_originais>
{requisitos}
</requisitos_originais>

Corrija todos os problemas apontados pelo QA e entregue o código revisado completo."""
    else:
        prompt = f"""Com base nos requisitos abaixo, escreva um script Python funcional.

<requisitos_po>
{requisitos}
</requisitos_po>

Instruções:
1. Use PyMuPDF (fitz) para extração de texto de PDFs
2. Use a biblioteca anthropic para geração do resumo
3. Trate erros: arquivo não encontrado, PDF corrompido, texto vazio
4. Adicione comentários explicando cada bloco principal
5. Inclua exemplo de uso comentado no final"""

    resposta = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return resposta.content[0].text.strip()
