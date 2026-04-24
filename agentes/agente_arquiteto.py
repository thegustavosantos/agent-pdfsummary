import anthropic

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Você é um arquiteto de software Python especializado em scripts CLI.
Sua função é receber requisitos e produzir um plano técnico detalhado para o desenvolvedor.

Regras obrigatórias:
- Não escreva código — apenas o plano
- Defina cada função: nome, parâmetros, retorno e responsabilidade em uma linha
- Defina o fluxo de dados entre as funções (quem chama quem)
- Aponte os pontos de falha e como cada um deve ser tratado
- Seja preciso o suficiente para que o Dev não precise tomar nenhuma decisão de estrutura"""


def executar(requisitos: str) -> str:
    """Recebe requisitos do PO e retorna um plano técnico estruturado."""

    prompt = f"""Com base nos requisitos abaixo, produza um plano técnico para um script Python CLI.

<requisitos_po>
{requisitos}
</requisitos_po>

Entregue SOMENTE estas seções:

1. ESTRUTURA DE FUNÇÕES
   Para cada função: nome(params) -> retorno — responsabilidade em uma linha

2. FLUXO DE DADOS
   Sequência de chamadas do main() até a saída final, em pseudocódigo simples

3. CONSTANTES E CONFIGURAÇÕES
   Valores fixos que o Dev deve declarar no topo do arquivo (limites, nomes, etc)

4. PONTOS DE FALHA
   Lista de erros esperados e como cada um deve ser tratado (qual exceção, qual mensagem)

5. FORMATO DE SAÍDA
   Exatamente o que deve ser impresso no terminal e o que deve ser salvo em arquivo

Sem introduções. Sem conclusões. Apenas as 5 seções."""

    resposta = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return resposta.content[0].text.strip()
