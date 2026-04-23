import anthropic

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Você é um Product Owner experiente em sistemas de processamento de documentos.
Sua função é receber uma ideia de produto e transformá-la em requisitos claros e acionáveis.
Seja objetivo, use listas numeradas, não escreva código."""

def executar(ideia: str) -> str:
    """Recebe uma ideia de produto e retorna os requisitos estruturados."""

    prompt = f"""A ideia do produto é: "{ideia}"

Sua tarefa:
1. Escreva os requisitos funcionais (o que o sistema faz)
2. Escreva os requisitos não funcionais (performance, segurança, limites)
3. Defina os critérios de aceitação para a feature principal
4. Descreva o fluxo do usuário em 3 a 5 passos"""

    resposta = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return resposta.content[0].text.strip()
