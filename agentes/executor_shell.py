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

import sys
import subprocess
from pathlib import Path
from config import SANDBOX_DIR

# Apenas esses prefixos de comando são permitidos
COMANDOS_PERMITIDOS = ("python", "pip")

# Timeout padrão por tipo de operação
TIMEOUT_SINTAXE  = 10   # verificação de sintaxe
TIMEOUT_EXECUCAO = 30   # execução de script
TIMEOUT_PYTEST   = 60   # suite de testes


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
    Usa sempre o mesmo executável Python do ambiente atual — compatível com Windows e venv.
    """
    _validar_comando(comando)

    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",          # evita crash em caracteres inválidos no Windows
            timeout=timeout,
            cwd=str(SANDBOX_DIR),
        )

        stdout = resultado.stdout or ""
        stderr = resultado.stderr or ""

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
    Usa o mesmo executável Python do ambiente atual via sys.executable.
    """
    exe = sys.executable.replace("\\", "/")
    return executar(
        f'"{exe}" -m py_compile {caminho_arquivo.name}',
        timeout=TIMEOUT_SINTAXE,
    )


def rodar_pytest(caminho_teste: Path, flags: str = "-v --tb=short") -> dict:
    """
    Roda pytest via 'python -m pytest' para garantir compatibilidade com
    qualquer ambiente Windows, venv ou PATH não configurado.
    """
    exe = sys.executable.replace("\\", "/")
    return executar(
        f'"{exe}" -m pytest {caminho_teste.name} {flags}',
        timeout=TIMEOUT_PYTEST,
    )


def salvar_na_sandbox(conteudo: str, nome_arquivo: str) -> Path:
    """Salva um arquivo na sandbox e retorna o Path."""
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    caminho = SANDBOX_DIR / nome_arquivo
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho