"""
orquestrador.py
───────────────
Pipeline multi-agente especializado em geração de código para resumo de PDFs.

Fluxo: PO → Arquiteto → Dev → QA
Se o QA reprovar, devolve o feedback ao Dev e reitera (até MAX_ITERACOES).

Uso:
    python orquestrador.py
    python orquestrador.py --max-iter 5
"""

import json
import argparse
import textwrap
from datetime import datetime
from pathlib import Path

import agente_po
import agente_arquiteto
import agente_dev
import agente_qa

# ── Configuração ──────────────────────────────────────────────────────────────
IDEIA         = "resumir PDFs automaticamente para o usuário via script CLI em Python"
MAX_ITERACOES = 3
SALVAR_LOG    = True


# ── Helpers de display ────────────────────────────────────────────────────────
def separador(titulo: str, char: str = "─", largura: int = 60) -> None:
    print(f"\n{char * largura}")
    print(f"  {titulo}")
    print(f"{char * largura}")


def resumir(texto: str, max_chars: int = 400) -> str:
    """Trunca texto longo para exibição no terminal."""
    if len(texto) <= max_chars:
        return texto
    return texto[:max_chars] + f"\n  ... ({len(texto) - max_chars} chars omitidos)"


def salvar_log(requisitos: str, plano: str, codigo: str, resultado_qa: dict) -> None:
    """Grava um arquivo de log com todos os artefatos gerados."""
    pasta = Path(__file__).parent / "logs"
    pasta.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo   = pasta / f"run_{timestamp}.json"

    log = {
        "timestamp" : timestamp,
        "requisitos": requisitos,
        "plano"     : plano,
        "codigo"    : codigo,
        "qa"        : resultado_qa,
    }

    arquivo.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Log salvo em: {arquivo}")


# ── Pipeline ──────────────────────────────────────────────────────────────────
def orquestrar(max_iter: int = MAX_ITERACOES) -> None:

    print(f"\n{'═' * 60}")
    print(f"  AGENT-PDFSUMMARY — Pipeline multi-agente")
    print(f"{'═' * 60}")

    # ── FASE 1: PO ────────────────────────────────────────────────────────────
    separador("AGENTE 1 — Product Owner")
    print("  Gerando requisitos...")

    requisitos = agente_po.executar(IDEIA)
    print(resumir(requisitos))

    # ── FASE 2: Arquiteto ─────────────────────────────────────────────────────
    separador("AGENTE 2 — Arquiteto")
    print("  Definindo plano técnico...")

    plano = agente_arquiteto.executar(requisitos)
    print(resumir(plano))

    # ── FASE 3 + 4: Dev → QA (com loop de feedback) ───────────────────────────
    feedback_qa  = None
    resultado_qa = None
    codigo       = None

    for iteracao in range(1, max_iter + 1):

        # Dev
        label = "AGENTE 3 — Dev" if iteracao == 1 else f"AGENTE 3 — Dev (revisão {iteracao - 1})"
        separador(label)
        print("  Escrevendo código..." if iteracao == 1 else "  Corrigindo com base no feedback do QA...")

        codigo = agente_dev.executar(requisitos, plano=plano, feedback_qa=feedback_qa)
        print(resumir(codigo, max_chars=500))

        # QA
        separador(f"AGENTE 4 — QA (iteração {iteracao}/{max_iter})")
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

    # ── Resultado final ───────────────────────────────────────────────────────
    separador("RESULTADO FINAL", char="═")
    print(f"\n  Iterações realizadas : {iteracao}")
    print(f"  Veredito final       : {resultado_qa.get('veredito', '?').upper().replace('_', ' ')}")
    print(f"\n{'═' * 60}\n")

    if SALVAR_LOG:
        salvar_log(requisitos, plano, codigo, resultado_qa)

    pasta_outputs = Path(__file__).parent.parent / "outputs"
    pasta_outputs.mkdir(exist_ok=True)
    saida = pasta_outputs / f"codigo_gerado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    saida.write_text(codigo, encoding="utf-8")
    print(f"  Código final salvo em: {saida}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="agent-pdfsummary — pipeline multi-agente PO → Arquiteto → Dev → QA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Exemplos:
              python orquestrador.py
              python orquestrador.py --max-iter 5
        """)
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=MAX_ITERACOES,
        help=f"Máximo de iterações Dev→QA (default: {MAX_ITERACOES})"
    )

    args = parser.parse_args()
    orquestrar(max_iter=args.max_iter)


if __name__ == "__main__":
    main()
