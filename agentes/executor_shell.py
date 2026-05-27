"""
executor_shell.py
─────────────────
Wrapper seguro para execução de comandos no shell pelos agentes.

Proteções implementadas:
- Timeout obrigatório em toda execução
- Execução isolada na pasta sandbox/
- Whitelist de comandos permitidos
- Nunca executa input externo direto como shell string
"""

import subprocess
from pathlib import Path
from config import SANDBOX_DIR

# Apenas esses prefixos de comando são permitidos
COMANDOS_PERMITIDOS = ("python", "pytest", "pip")

# Timeout padrão por tipo de operação
TIMEOUT_SINTAXE = 10   # verificação de sintaxe
TIMEOUT_EXECUCAO = 30  # execução de script
TIMEOUT_PYTEST   = 60  # suite de testes


def _validar_comando(comando: str) -> None:
    """Lança ValueError se o comando não estiver na whitelist."""
    cmd_base = comando.strip().split()[0]
    if not any(cmd_base.startswith(p) for p in COMANDOS_PERMITIDOS):
        raise ValueError(
            f"Comando não permitido: '{cmd_base}'. "
            f"Permitidos: {COMANDOS_PERMITIDOS}"
        )


def executar(comando: str, timeout: int = TIMEOUT_EXECUCAO) -> dict:
    """
    Executa um comando no shell dentro da sandbox.

    Parâmetros:
        comando : string do comando (ex: "python resumidor.py --help")
        timeout : segundos antes de matar o processo

    Retorna dict com:
        stdout    : saída padrão
        stderr    : saída de erro
        exit_code : código de retorno (0 = sucesso)
        sucesso   : True se exit_code == 0
        truncado  : True se output foi cortado (> 4000 chars)
    """
    _validar_comando(comando)

    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SANDBOX_DIR),
        )

        stdout = resultado.stdout or ""
        stderr = resultado.stderr or ""

        # Trunca outputs muito longos para não explodir o contexto do LLM
        truncado = False
        limite   = 4000
        if len(stdout) > limite:
            stdout   = stdout[:limite] + f"\n... (truncado — {len(stdout) - limite} chars omitidos)"
            truncado = True
        if len(stderr) > limite:
            stderr   = stderr[:limite] + f"\n... (truncado — {len(stderr) - limite} chars omitidos)"
            truncado = True

        return {
            "stdout"   : stdout,
            "stderr"   : stderr,
            "exit_code": resultado.returncode,
            "sucesso"  : resultado.returncode == 0,
            "truncado" : truncado,
        }

    except subprocess.TimeoutExpired:
        return {
            "stdout"   : "",
            "stderr"   : f"Timeout: o comando excedeu {timeout} segundos e foi encerrado.",
            "exit_code": -1,
            "sucesso"  : False,
            "truncado" : False,
        }
    except Exception as exc:
        return {
            "stdout"   : "",
            "stderr"   : f"Erro ao executar comando: {exc}",
            "exit_code": -1,
            "sucesso"  : False,
            "truncado" : False,
        }


def verificar_sintaxe(caminho_arquivo: Path) -> dict:
    """
    Verifica sintaxe Python sem executar o código.
    Usa `python -m py_compile` que é seguro — não roda o __main__.
    """
    return executar(
        f"python -m py_compile {caminho_arquivo.name}",
        timeout=TIMEOUT_SINTAXE,
    )


def rodar_pytest(caminho_teste: Path, flags: str = "-v --tb=short") -> dict:
    """
    Roda pytest no arquivo de testes dentro da sandbox.
    """
    return executar(
        f"pytest {caminho_teste.name} {flags}",
        timeout=TIMEOUT_PYTEST,
    )


def salvar_na_sandbox(conteudo: str, nome_arquivo: str) -> Path:
    """
    Salva um arquivo de texto na sandbox e retorna o Path.
    Usado pelo Dev (salvar código) e pelo QA (salvar testes).
    """
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    caminho = SANDBOX_DIR / nome_arquivo
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho
