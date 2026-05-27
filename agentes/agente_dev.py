import re
import anthropic
from config import MODELO_AGENTES, MODELO_GERADO
from executor_shell import verificar_sintaxe, salvar_na_sandbox

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Você é um desenvolvedor Python sênior especializado em scripts CLI.
Sua função é receber requisitos e entregar um script Python completo, funcional e pronto para rodar.

Regras obrigatórias:
- Entregue SEMPRE um script CLI — sem Streamlit, Flask, FastAPI ou qualquer framework web
- O script deve ser executável via terminal: python resumidor.py arquivo.pdf
- Escreva o script COMPLETO do início ao fim — nunca truncar ou usar reticências no meio do código
- Apenas o código Python, sem explicações fora do código"""

MAX_TENTATIVAS_SINTAXE = 3


def _extrair_codigo(texto: str) -> str:
    """Remove blocos markdown ```python se o modelo os incluir."""
    match = re.search(r"```python\s*(.*?)```", texto, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*(.*?)```", texto, re.DOTALL)
    if match:
        return match.group(1).strip()
    return texto.strip()


def _gerar_codigo(prompt: str) -> str:
    """Chama a API e retorna o código extraído."""
    resposta = client.messages.create(
        model=MODELO_AGENTES,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extrair_codigo(resposta.content[0].text)


def executar(requisitos: str, plano: str = None, feedback_qa: str = None, memoria: str = None) -> str:
    """
    Recebe requisitos, plano técnico, feedback do QA e memória da run anterior.
    Após gerar o código, valida a sintaxe no shell e corrige automaticamente se necessário.
    """

    bloco_memoria = ""
    if memoria:
        bloco_memoria = f"""
<memoria_run_anterior>
{memoria}
</memoria_run_anterior>

Leve em conta os problemas da run anterior listados acima para não repeti-los.
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
{bloco_memoria}
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
{bloco_memoria}
Instrucoes:
1. Siga o plano tecnico a risca: use os nomes de funcoes, parametros e retornos definidos
2. Implemente TODOS os pontos de falha listados no plano
3. Use PyMuPDF (fitz) para extracao de texto e anthropic para o resumo
4. Use SEMPRE o modelo "{MODELO_GERADO}" na chamada à API — ignore qualquer outro modelo que apareça no plano
5. Adicione comentarios explicando cada bloco
6. Use argparse conforme o plano define

IMPORTANTE: Escreva o script inteiro, do import ate a ultima linha. Nunca truncar."""

    # ── Loop de auto-validação de sintaxe ─────────────────────────────────────
    codigo = _gerar_codigo(prompt)

    for tentativa in range(1, MAX_TENTATIVAS_SINTAXE + 1):
        caminho = salvar_na_sandbox(codigo, "resumidor.py")
        resultado = verificar_sintaxe(caminho)

        if resultado["sucesso"]:
            if tentativa > 1:
                print(f"  [dev] sintaxe OK na tentativa {tentativa}")
            else:
                print("  [dev] sintaxe OK ✓")
            break

        # Sintaxe falhou — pede correção focada no erro
        erro = resultado["stderr"]
        print(f"  [dev] erro de sintaxe (tentativa {tentativa}/{MAX_TENTATIVAS_SINTAXE}): {erro[:200]}")

        if tentativa == MAX_TENTATIVAS_SINTAXE:
            print("  [dev] limite de correções de sintaxe atingido — entregando código mesmo assim")
            break

        prompt_correcao = f"""O código abaixo tem um erro de sintaxe Python.

Erro reportado pelo interpretador:
{erro}

Código com erro:
```python
{codigo}
```

Corrija APENAS o erro de sintaxe e entregue o código completo corrigido.
Não altere nenhuma outra parte do código."""

        codigo = _gerar_codigo(prompt_correcao)

    return codigo