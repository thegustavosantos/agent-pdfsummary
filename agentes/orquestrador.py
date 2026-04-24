"""
orquestrador.py
───────────────
Pipeline principal: Dev → QA (com loop de feedback) → Reviewer.

Lê requisitos e plano de discovery.md — gerado uma única vez por discovery.py.
Lê o log da run anterior para passar contexto de memória ao Dev.
Ao final, o Reviewer compara a versão gerada com a anterior e aponta regressões.

Uso:
    python orquestrador.py
    python orquestrador.py --max-iter 5
"""

import json
import argparse
import textwrap
from datetime import datetime
from pathlib import Path

import agente_dev
import agente_qa
import agente_reviewer
from config import (
    MAX_ITERACOES as MAX_ITERACOES_DEFAULT,
    DISCOVERY_FILE,
    LOGS_DIR,
    OUTPUTS_DIR,
)

SALVAR_LOG = True


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
    """Lê discovery.md. Aborta se não existir ou estiver mal formatado."""
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


# ── Memória — log da run anterior ─────────────────────────────────────────────
def carregar_ultimo_log() -> dict | None:
    """Retorna o log mais recente em logs/ ou None se não houver."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logs = sorted(LOGS_DIR.glob("run_*.json"))
    if not logs:
        return None
    return json.loads(logs[-1].read_text(encoding="utf-8"))


def montar_contexto_memoria(log: dict | None) -> str | None:
    """Transforma o log anterior em contexto legível para o Dev."""
    if not log:
        return None

    qa = log.get("qa", {})
    bugs = qa.get("bugs", [])
    veredito = qa.get("veredito", "desconhecido")
    parecer = qa.get("parecer", "")
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
def salvar_log(requisitos: str, plano: str, codigo: str, resultado_qa: dict) -> Path:
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
    return arquivo


# ── Pipeline ──────────────────────────────────────────────────────────────────
def orquestrar(max_iter: int = MAX_ITERACOES_DEFAULT) -> None:

    print(f"\n{'═' * 60}")
    print(f"  AGENT-PDFSUMMARY — Pipeline")
    print(f"{'═' * 60}")

    # ── Carrega discovery ─────────────────────────────────────────────────────
    separador("DISCOVERY")
    discovery  = carregar_discovery()
    requisitos = discovery["requisitos"]
    plano      = discovery["plano"]

    # ── Carrega memória da run anterior ───────────────────────────────────────
    ultimo_log     = carregar_ultimo_log()
    contexto_memoria = montar_contexto_memoria(ultimo_log)
    codigo_anterior  = ultimo_log.get("codigo") if ultimo_log else None
    qa_anterior      = ultimo_log.get("qa", {}) if ultimo_log else {}

    if contexto_memoria:
        separador("MEMÓRIA — Run anterior")
        print(resumir(contexto_memoria))
    else:
        print("\n  Sem runs anteriores — iniciando do zero.")

    # ── Dev → QA (com loop de feedback) ───────────────────────────────────────
    feedback_qa  = None
    resultado_qa = None
    codigo       = None

    for iteracao in range(1, max_iter + 1):

        label = "AGENTE 1 — Dev" if iteracao == 1 else f"AGENTE 1 — Dev (revisão {iteracao - 1})"
        separador(label)
        print("  Escrevendo código..." if iteracao == 1 else "  Corrigindo com base no feedback do QA...")

        codigo = agente_dev.executar(
            requisitos,
            plano=plano,
            feedback_qa=feedback_qa,
            memoria=contexto_memoria,
        )
        print(resumir(codigo, max_chars=500))

        separador(f"AGENTE 2 — QA (iteração {iteracao}/{max_iter})")
        print("  Analisando código...")

        resultado_qa  = agente_qa.executar(codigo, requisitos)
        veredito      = resultado_qa.get("veredito", "desconhecido")
        deve_reiterar = resultado_qa.get("deve_reiterar", False)
        bugs          = resultado_qa.get("bugs", [])
        parecer       = resultado_qa.get("parecer", "")

        icone = {"aprovado": "✅", "aprovado_com_ressalvas": "⚠️", "reprovado": "❌"}.get(veredito, "?")
        print(f"\n  Veredito: {icone}  {veredito.upper().replace('_', ' ')}")

        if bugs:
            print(f"\n  Bugs encontrados ({len(bugs)}):")
            for i, bug in enumerate(bugs, 1):
                print(f"    {i}. {bug}")

        print(f"\n  Parecer: {parecer}")

        cobertura = resultado_qa.get("cobertura", {})
        if cobertura:
            ausentes = [k for k, v in cobertura.items() if v == "ausente"]
            parciais = [k for k, v in cobertura.items() if v == "parcial"]
            if ausentes:
                print(f"  Requisitos ausentes : {', '.join(ausentes)}")
            if parciais:
                print(f"  Requisitos parciais : {', '.join(parciais)}")

        if not deve_reiterar:
            print(f"\n  QA liberou. Encerrando com {iteracao} iteração(ões).")
            break

        if iteracao == max_iter:
            print(f"\n  ⚠️  Limite de {max_iter} iterações atingido. Encerrando.")
            break

        feedback_qa  = f"Veredito: {veredito}\n\nBugs:\n"
        feedback_qa += "\n".join(f"- {b}" for b in bugs)
        feedback_qa += f"\n\nParecer geral: {parecer}"
        print(f"\n  Devolvendo feedback ao Dev para correção...")

    # ── Reviewer — compara com versão anterior ────────────────────────────────
    if codigo_anterior:
        separador("AGENTE 3 — Reviewer")
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
    else:
        review = {}
        print("\n  Sem versão anterior — Reviewer pulado.")

    # ── Resultado final ───────────────────────────────────────────────────────
    separador("RESULTADO FINAL", char="═")
    print(f"\n  Iterações realizadas : {iteracao}")
    print(f"  Veredito QA          : {resultado_qa.get('veredito', '?').upper().replace('_', ' ')}")
    if review:
        status_review = "SEM REGRESSÕES" if review.get("aprovado") else "⚠️  REGRESSÕES DETECTADAS"
        print(f"  Reviewer             : {status_review}")
    print(f"\n{'═' * 60}\n")

    # ── Salva log e código ────────────────────────────────────────────────────
    if SALVAR_LOG:
        salvar_log(requisitos, plano, codigo, resultado_qa)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    saida = OUTPUTS_DIR / f"codigo_gerado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    saida.write_text(codigo, encoding="utf-8")
    print(f"  Código final salvo em: {saida}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="agent-pdfsummary — pipeline Dev → QA → Reviewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Pré-requisito: rodar discovery.py antes da primeira execução.

            Exemplos:
              python discovery.py
              python orquestrador.py
              python orquestrador.py --max-iter 5
        """)
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=MAX_ITERACOES_DEFAULT,
        help=f"Máximo de iterações Dev→QA (default: {MAX_ITERACOES_DEFAULT})"
    )

    args = parser.parse_args()
    orquestrar(max_iter=args.max_iter)


if __name__ == "__main__":
    main()
