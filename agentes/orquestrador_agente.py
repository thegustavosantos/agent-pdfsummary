"""
orquestrador_agente.py
──────────────────────
Orquestrador com raciocínio dinâmico usando Stateless Orchestrator pattern.

Diferença do orquestrador.py (sequencial fixo):
- Um LLM decide qual agente chamar a seguir com base no estado atual
- O contexto passado ao decisor é sempre pequeno e fixo — sem acúmulo de histórico
- A sequência emerge do raciocínio, não do código

Custo por decisão: ~500 tokens (fixo, independente de iterações)

Uso:
    python orquestrador_agente.py
    python orquestrador_agente.py --max-iter 5 --verbose
"""

import json
import argparse
import textwrap
from datetime import datetime
from pathlib import Path

import anthropic
import agente_dev
import agente_qa
import agente_reviewer
from config import (
    MODELO_AGENTES,
    MAX_ITERACOES as MAX_ITERACOES_DEFAULT,
    DISCOVERY_FILE,
    LOGS_DIR,
    OUTPUTS_DIR,
)

SALVAR_LOG = True

# ── Ações disponíveis para o decisor ─────────────────────────────────────────
ACOES = ["dev", "qa", "reviewer", "encerrar"]

DESCRICAO_ACOES = """
- dev       → escreve ou corrige o código Python
- qa        → analisa o código e retorna veredito (aprovado / reprovado)
- reviewer  → compara o código atual com a versão anterior e detecta regressões
- encerrar  → pipeline concluído, salva resultados e termina
"""

# ── Decisor stateless ─────────────────────────────────────────────────────────
decisor_client = anthropic.Anthropic()


def decidir_proxima_acao(estado: dict, verbose: bool = False) -> str:
    """
    Chama o LLM UMA vez com o estado atual resumido.
    Contexto pequeno e fixo — sem histórico acumulado.
    Retorna o nome da próxima ação a executar.
    """

    prompt = f"""Você é o orquestrador de um pipeline de geração de código Python.
Seu único trabalho é decidir qual a próxima ação a executar com base no estado atual.

ESTADO ATUAL:
- Última ação executada : {estado['ultima_acao']}
- Código gerado         : {'sim' if estado['tem_codigo'] else 'não'}
- Veredito do QA        : {estado['veredito_qa'] or 'pendente'}
- QA deve reiterar      : {estado['deve_reiterar']}
- Iterações Dev→QA      : {estado['iteracoes']} de {estado['max_iter']}
- Versão anterior existe: {estado['tem_codigo_anterior']}
- Reviewer executou     : {estado['reviewer_executou']}
- Regressões detectadas : {estado['regressoes_detectadas']}

AÇÕES DISPONÍVEIS:{DESCRICAO_ACOES}

REGRAS DE DECISÃO:
1. Se não há código → chame "dev"
2. Se há código mas QA não rodou ainda → chame "qa"
3. Se QA reprovou E iterações < max_iter → chame "dev"
4. Se QA aprovou E há versão anterior E reviewer não executou → chame "reviewer"
5. Se QA aprovou E (sem versão anterior OU reviewer já executou) → chame "encerrar"
6. Se iterações atingiu max_iter → chame "encerrar"

Responda APENAS com uma palavra: o nome exato da ação."""

    if verbose:
        print(f"\n  [decisor] estado: {json.dumps(estado, ensure_ascii=False)}")

    resposta = decisor_client.messages.create(
        model=MODELO_AGENTES,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )

    acao = resposta.content[0].text.strip().lower()

    # Valida que a resposta é uma ação conhecida
    if acao not in ACOES:
        # Fallback seguro se o modelo responder algo inesperado
        print(f"  [decisor] ação desconhecida '{acao}' — usando fallback 'encerrar'")
        acao = "encerrar"

    if verbose:
        print(f"  [decisor] próxima ação: {acao}")

    return acao


# ── Helpers de display ────────────────────────────────────────────────────────
def separador(titulo: str, char: str = "─", largura: int = 60) -> None:
    print(f"\n{char * largura}")
    print(f"  {titulo}")
    print(f"{char * largura}")


def resumir(texto: str, max_chars: int = 400) -> str:
    if len(texto) <= max_chars:
        return texto
    return texto[:max_chars] + f"\n  ... ({len(texto) - max_chars} chars omitidos)"


# ── Discovery ─────────────────────────────────────────────────────────────────
def carregar_discovery() -> dict:
    if not DISCOVERY_FILE.exists():
        print("\n  Erro: discovery.md não encontrado.")
        print("  Execute primeiro: python discovery.py\n")
        raise SystemExit(1)

    texto = DISCOVERY_FILE.read_text(encoding="utf-8")

    gerado_em = "?"
    for linha in texto.splitlines():
        if linha.startswith("**Gerado em:**"):
            gerado_em = linha.split("**Gerado em:**", 1)[1].strip()
            break

    partes_req = texto.split("## Requisitos", 1)
    if len(partes_req) < 2:
        print("\n  Erro: seção '## Requisitos' não encontrada em discovery.md\n")
        raise SystemExit(1)

    partes_plano = partes_req[1].split("## Plano Técnico", 1)
    if len(partes_plano) < 2:
        print("\n  Erro: seção '## Plano Técnico' não encontrada em discovery.md\n")
        raise SystemExit(1)

    requisitos = partes_req[1].split("## Plano Técnico", 1)[0].strip()
    plano      = partes_plano[1].strip()

    print(f"  Discovery carregado ({gerado_em})")
    return {"gerado_em": gerado_em, "requisitos": requisitos, "plano": plano}


# ── Memória ───────────────────────────────────────────────────────────────────
def carregar_ultimo_log() -> dict | None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logs = sorted(LOGS_DIR.glob("run_*.json"))
    if not logs:
        return None
    return json.loads(logs[-1].read_text(encoding="utf-8"))


def montar_contexto_memoria(log: dict | None) -> str | None:
    if not log:
        return None
    qa       = log.get("qa", {})
    bugs     = qa.get("bugs", [])
    veredito = qa.get("veredito", "desconhecido")
    parecer  = qa.get("parecer", "")
    timestamp = log.get("timestamp", "?")

    if not bugs and veredito == "aprovado":
        return None

    linhas = [
        f"Na run anterior ({timestamp}), o QA retornou veredito '{veredito}'.",
        f"Parecer: {parecer}",
    ]
    if bugs:
        linhas.append("Bugs reportados que devem ser evitados nesta versão:")
        for b in bugs:
            linhas.append(f"  - {b}")
    return "\n".join(linhas)


# ── Log ───────────────────────────────────────────────────────────────────────
def salvar_log(requisitos: str, plano: str, codigo: str, resultado_qa: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo = LOGS_DIR / f"run_{timestamp}.json"
    log = {
        "timestamp" : timestamp,
        "requisitos": requisitos,
        "plano"     : plano,
        "codigo"    : codigo,
        "qa"        : resultado_qa,
    }
    arquivo.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Log salvo em: {arquivo}")


# ── Pipeline com decisor ──────────────────────────────────────────────────────
def orquestrar(max_iter: int = MAX_ITERACOES_DEFAULT, verbose: bool = False) -> None:

    print(f"\n{'═' * 60}")
    print(f"  AGENT-PDFSUMMARY — Stateless Orchestrator")
    print(f"{'═' * 60}")

    # Carrega contexto fixo
    separador("DISCOVERY")
    discovery        = carregar_discovery()
    requisitos       = discovery["requisitos"]
    plano            = discovery["plano"]

    ultimo_log       = carregar_ultimo_log()
    contexto_memoria = montar_contexto_memoria(ultimo_log)
    codigo_anterior  = ultimo_log.get("codigo") if ultimo_log else None
    qa_anterior      = ultimo_log.get("qa", {}) if ultimo_log else {}

    if contexto_memoria:
        separador("MEMÓRIA — Run anterior")
        print(resumir(contexto_memoria))
    else:
        print("\n  Sem runs anteriores — iniciando do zero.")

    # Estado que o decisor consulta a cada turno
    estado = {
        "ultima_acao"         : "inicio",
        "tem_codigo"          : False,
        "veredito_qa"         : None,
        "deve_reiterar"       : False,
        "iteracoes"           : 0,
        "max_iter"            : max_iter,
        "tem_codigo_anterior" : codigo_anterior is not None,
        "reviewer_executou"   : False,
        "regressoes_detectadas": False,
    }

    # Variáveis de trabalho
    codigo       = None
    resultado_qa = {}
    feedback_qa  = None
    review       = {}
    turno        = 0

    # ── Loop principal ────────────────────────────────────────────────────────
    while True:
        turno += 1
        acao = decidir_proxima_acao(estado, verbose=verbose)

        # ── Dev ───────────────────────────────────────────────────────────────
        if acao == "dev":
            estado["iteracoes"] += 1
            label = "DEV" if estado["iteracoes"] == 1 else f"DEV (revisão {estado['iteracoes'] - 1})"
            separador(f"AGENTE — {label}  [turno {turno}]")
            print("  Escrevendo código..." if estado["iteracoes"] == 1 else "  Corrigindo com base no feedback do QA...")

            codigo = agente_dev.executar(
                requisitos,
                plano=plano,
                feedback_qa=feedback_qa,
                memoria=contexto_memoria,
            )
            print(resumir(codigo, max_chars=500))

            estado["tem_codigo"]  = True
            estado["ultima_acao"] = "dev"
            estado["veredito_qa"] = None   # reseta — QA precisa rodar no novo código

        # ── QA ────────────────────────────────────────────────────────────────
        elif acao == "qa":
            separador(f"AGENTE — QA  [turno {turno}]")
            print("  Analisando código...")

            resultado_qa  = agente_qa.executar(codigo, requisitos)
            veredito      = resultado_qa.get("veredito", "desconhecido")
            deve_reiterar = resultado_qa.get("deve_reiterar", False)
            bugs          = resultado_qa.get("bugs", [])
            parecer       = resultado_qa.get("parecer", "")

            icone = {"aprovado": "✅", "aprovado_com_ressalvas": "⚠️", "reprovado": "❌"}.get(veredito, "?")
            print(f"\n  Veredito: {icone}  {veredito.upper().replace('_', ' ')}")

            if bugs:
                print(f"\n  Bugs ({len(bugs)}):")
                for i, bug in enumerate(bugs, 1):
                    print(f"    {i}. {bug}")

            print(f"\n  Parecer: {parecer}")

            # Monta feedback para próximo Dev se necessário
            if deve_reiterar:
                feedback_qa  = f"Veredito: {veredito}\n\nBugs:\n"
                feedback_qa += "\n".join(f"- {b}" for b in bugs)
                feedback_qa += f"\n\nParecer: {parecer}"

            estado["veredito_qa"]   = veredito
            estado["deve_reiterar"] = deve_reiterar
            estado["ultima_acao"]   = "qa"

        # ── Reviewer ──────────────────────────────────────────────────────────
        elif acao == "reviewer":
            separador(f"AGENTE — REVIEWER  [turno {turno}]")
            print("  Comparando com versão anterior...")

            review = agente_reviewer.executar(codigo_anterior, codigo, qa_anterior)

            aprovado_review = review.get("aprovado", True)
            regressoes      = review.get("regressoes", [])
            evolucoes       = review.get("evolucoes", [])
            parecer_review  = review.get("parecer", "")

            icone_review = "✅" if aprovado_review else "⚠️"
            print(f"\n  {icone_review} {parecer_review}")

            if evolucoes:
                print(f"\n  Evoluções ({len(evolucoes)}):")
                for e in evolucoes:
                    print(f"    + {e}")

            if regressoes:
                print(f"\n  Regressões ({len(regressoes)}):")
                for r in regressoes:
                    print(f"    - {r}")

            estado["reviewer_executou"]    = True
            estado["regressoes_detectadas"] = not aprovado_review
            estado["ultima_acao"]          = "reviewer"

        # ── Encerrar ──────────────────────────────────────────────────────────
        elif acao == "encerrar":
            break

    # ── Resultado final ───────────────────────────────────────────────────────
    separador("RESULTADO FINAL", char="═")
    print(f"\n  Turnos do decisor    : {turno}")
    print(f"  Iterações Dev→QA     : {estado['iteracoes']}")
    print(f"  Veredito QA          : {resultado_qa.get('veredito', '?').upper().replace('_', ' ')}")
    if review:
        status_review = "SEM REGRESSÕES" if review.get("aprovado") else "⚠️  REGRESSÕES DETECTADAS"
        print(f"  Reviewer             : {status_review}")
    print(f"\n{'═' * 60}\n")

    if codigo and SALVAR_LOG:
        salvar_log(requisitos, plano, codigo, resultado_qa)

    if codigo:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        saida = OUTPUTS_DIR / f"codigo_gerado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        saida.write_text(codigo, encoding="utf-8")
        print(f"  Código final salvo em: {saida}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="agent-pdfsummary — Stateless Orchestrator (raciocínio dinâmico)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Pré-requisito: rodar discovery.py antes da primeira execução.

            Exemplos:
              python orquestrador_agente.py
              python orquestrador_agente.py --max-iter 5
              python orquestrador_agente.py --verbose   # mostra estado a cada decisão
        """)
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=MAX_ITERACOES_DEFAULT,
        help=f"Máximo de iterações Dev→QA (default: {MAX_ITERACOES_DEFAULT})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibe o estado completo e a decisão a cada turno do orquestrador"
    )

    args = parser.parse_args()
    orquestrar(max_iter=args.max_iter, verbose=args.verbose)


if __name__ == "__main__":
    main()
