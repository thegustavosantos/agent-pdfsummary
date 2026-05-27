import re
import json
import anthropic
from pathlib import Path
from config import MODELO_AGENTES, SANDBOX_DIR
from executor_shell import rodar_pytest, salvar_na_sandbox

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Você é um engenheiro de QA sênior especializado em Python.
Sua função é analisar código, gerar testes pytest e interpretar resultados de execução real.
Sempre responda em JSON válido, sem texto fora do JSON."""

APROVADO           = "aprovado"
APROVADO_RESSALVAS = "aprovado_com_ressalvas"
REPROVADO          = "reprovado"


def _extrair_codigo(texto: str) -> str:
    """Remove blocos markdown se o modelo os incluir."""
    match = re.search(r"```python\s*(.*?)```", texto, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*(.*?)```", texto, re.DOTALL)
    if match:
        return match.group(1).strip()
    return texto.strip()


def _gerar_testes(codigo: str, requisitos: str) -> str:
    """Pede ao LLM para gerar um arquivo pytest para o código."""
    prompt = f"""Gere um arquivo pytest completo para testar o código abaixo.

<requisitos>
{requisitos}
</requisitos>

<codigo>
{codigo}
</codigo>

Regras obrigatórias:
- Use apenas pytest e unittest.mock — sem dependências externas
- Mock TODAS as chamadas à API Anthropic (anthropic.Anthropic)
- Mock TODAS as chamadas ao fitz (PyMuPDF) que abrem arquivos reais
- Use tmp_path do pytest para criar arquivos temporários quando necessário
- Teste os cenários: argumento ausente, arquivo inexistente, extensão inválida, texto vazio, falha na API
- Mínimo de 5 testes, máximo de 10
- Cada teste deve ser independente e rodar sem arquivos reais na máquina

Entregue APENAS o código Python do arquivo de testes, sem explicações."""

    resposta = client.messages.create(
        model=MODELO_AGENTES,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extrair_codigo(resposta.content[0].text)


def _interpretar_resultado_pytest(
    codigo: str,
    requisitos: str,
    resultado_pytest: dict,
    testes: str,
) -> dict:
    """Pede ao LLM para interpretar o resultado real do pytest e retornar o veredito JSON."""

    status = "PASSOU" if resultado_pytest["sucesso"] else "FALHOU"
    saida  = resultado_pytest["stdout"] or resultado_pytest["stderr"]

    prompt = f"""O QA rodou pytest no código abaixo e obteve o resultado real.

<requisitos_po>
{requisitos}
</requisitos_po>

<codigo_dev>
{codigo}
</codigo_dev>

<resultado_pytest status="{status}">
{saida[:3000]}
</resultado_pytest>

Com base no resultado real do pytest E na análise estática do código, responda APENAS com JSON:
{{
  "veredito": "aprovado" | "aprovado_com_ressalvas" | "reprovado",
  "bugs": ["bug 1", "bug 2"],
  "testes_passaram": {str(resultado_pytest["sucesso"]).lower()},
  "cobertura": {{
    "RF1": "atendido" | "parcial" | "ausente"
  }},
  "parecer": "texto justificado em 3-5 linhas mencionando resultado do pytest",
  "deve_reiterar": true | false
}}

Regras para deve_reiterar:
- true  → se pytest falhou OU se houver bugs críticos
- false → se pytest passou E sem bugs críticos"""

    resposta = client.messages.create(
        model=MODELO_AGENTES,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    texto = resposta.content[0].text.strip()
    if texto.startswith("```"):
        texto = "\n".join(texto.split("\n")[1:-1])

    resultado = json.loads(texto)
    # Injeta o output real do pytest no resultado para o log
    resultado["pytest_output"] = saida[:2000]
    return resultado


def executar(codigo: str, requisitos: str) -> dict:
    """
    1. Gera testes pytest para o código
    2. Salva os testes na sandbox
    3. Roda pytest de verdade no shell
    4. Interpreta o resultado real e retorna o veredito
    """

    # ── Gera testes ───────────────────────────────────────────────────────────
    print("  [qa] gerando testes pytest...")
    testes = _gerar_testes(codigo, requisitos)

    # Salva testes na sandbox (o código já foi salvo pelo Dev)
    caminho_testes = salvar_na_sandbox(testes, "test_resumidor.py")
    print(f"  [qa] testes salvos em: {caminho_testes}")

    # ── Instala dependências mínimas na sandbox se necessário ─────────────────
    # pytest já deve estar instalado no ambiente do projeto

    # ── Roda pytest ───────────────────────────────────────────────────────────
    print("  [qa] rodando pytest...")
    resultado_pytest = rodar_pytest(caminho_testes)

    status_icon = "✓" if resultado_pytest["sucesso"] else "✗"
    print(f"  [qa] pytest {status_icon}  exit_code={resultado_pytest['exit_code']}")

    # Mostra resumo do pytest no terminal
    saida = resultado_pytest["stdout"] or resultado_pytest["stderr"]
    for linha in saida.splitlines()[-8:]:  # últimas 8 linhas (resumo do pytest)
        if linha.strip():
            print(f"       {linha}")

    # ── Interpreta resultado ──────────────────────────────────────────────────
    print("  [qa] interpretando resultado...")
    return _interpretar_resultado_pytest(codigo, requisitos, resultado_pytest, testes)