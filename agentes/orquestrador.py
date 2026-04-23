"""
orquestrador.py
───────────────
Orquestra os agentes PO → Dev → QA em sequência.
Se o QA reprovar, devolve o feedback ao Dev e reitera (até MAX_ITERACOES).

Uso:
    python orquestrador.py
    python orquestrador.py --ideia "transcrever áudios para texto"
    python orquestrador.py --max-iter 5
"""

import sys
import json
import argparse
import textwrap
from datetime import datetime
from pathlib import Path

# Importa os agentes — todos na mesma pasta
import agente_po
import agente_dev
import agente_qa

# ── Configuração ──────────────────────────────────────────────────────────────
MAX_ITERACOES = 3          # quantas vezes o Dev pode corrigir antes de desistir
SALVAR_LOG    = True       # grava resultado final em logs/


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


def salvar_log(ideia: str, requisitos: str, codigo: str, resultado_qa: dict) -> None:
    """Grava um arquivo de log com todos os artefatos gerados."""
    pasta = Path(__file__).parent / "logs"
    pasta.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo   = pasta / f"run_{timestamp}.json"

    log = {
        "timestamp" : timestamp,
        "ideia"     : ideia,
        "requisitos": requisitos,
        "codigo"    : codigo,
        "qa"        : resultado_qa,
    }

    arquivo.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Log salvo em: {arquivo}")


# ── Orquestrador ──────────────────────────────────────────────────────────────
def orquestrar(ideia: str, max_iter: int = MAX_ITERACOES) -> None:

    print(f"\n{'═' * 60}")
    print(f"  ORQUESTRADOR MULTI-AGENTE")
    print(f"  Ideia: {ideia}")
    print(f"{'═' * 60}")

    # ── FASE 1: PO ────────────────────────────────────────────────────────────
    separador("AGENTE 1 — Product Owner")
    print("  Gerando requisitos...")

    requisitos = agente_po.executar(ideia)

    print(resumir(requisitos))

    # ── FASE 2 + 3: Dev → QA (com loop de feedback) ───────────────────────────
    feedback_qa   = None
    resultado_qa  = None
    codigo        = None

    for iteracao in range(1, max_iter + 1):

        # Dev
        label = "AGENTE 2 — Dev" if iteracao == 1 else f"AGENTE 2 — Dev (revisão {iteracao - 1})"
        separador(label)
        print("  Escrevendo código..." if iteracao == 1 else "  Corrigindo código com base no feedback do QA...")

        codigo = agente_dev.executar(requisitos, feedback_qa=feedback_qa)

        print(resumir(codigo, max_chars=500))

        # QA
        separador(f"AGENTE 3 — QA (iteração {iteracao}/{max_iter})")
        print("  Analisando código...")

        resultado_qa = agente_qa.executar(codigo, requisitos)

        veredito      = resultado_qa.get("veredito", "desconhecido")
        deve_reiterar = resultado_qa.get("deve_reiterar", False)
        bugs          = resultado_qa.get("bugs", [])
        parecer       = resultado_qa.get("parecer", "")

        # Exibe resultado do QA
        icone = {"aprovado": "✅", "aprovado_com_ressalvas": "⚠️", "reprovado": "❌"}.get(veredito, "?")
        print(f"\n  Veredito: {icone}  {veredito.upper().replace('_', ' ')}")

        if bugs:
            print(f"\n  Bugs encontrados ({len(bugs)}):")
            for i, bug in enumerate(bugs, 1):
                print(f"    {i}. {bug}")

        print(f"\n  Parecer: {parecer}")

        # Cobertura
        cobertura = resultado_qa.get("cobertura", {})
        if cobertura:
            ausentes = [k for k, v in cobertura.items() if v == "ausente"]
            parciais = [k for k, v in cobertura.items() if v == "parcial"]
            if ausentes:
                print(f"  Requisitos ausentes : {', '.join(ausentes)}")
            if parciais:
                print(f"  Requisitos parciais : {', '.join(parciais)}")

        # ── Decisão de loop ───────────────────────────────────────────────────
        if not deve_reiterar:
            print(f"\n  QA liberou. Encerrando com {iteracao} iteração(ões).")
            break

        if iteracao == max_iter:
            print(f"\n  ⚠️  Limite de {max_iter} iterações atingido. Encerrando mesmo com ressalvas.")
            break

        # Prepara feedback para o Dev
        feedback_qa = f"Veredito: {veredito}\n\nBugs:\n"
        feedback_qa += "\n".join(f"- {b}" for b in bugs)
        feedback_qa += f"\n\nParecer geral: {parecer}"
        print(f"\n  Devolvendo feedback ao Dev para correção...")

    # ── RESULTADO FINAL ───────────────────────────────────────────────────────
    separador("RESULTADO FINAL", char="═")
    print(f"\n  Iterações realizadas : {iteracao}")
    print(f"  Veredito final       : {resultado_qa.get('veredito', '?').upper().replace('_', ' ')}")
    print(f"\n{'═' * 60}\n")

    # Salva log
    if SALVAR_LOG:
        salvar_log(ideia, requisitos, codigo, resultado_qa)

    # Grava o código final em arquivo
    saida = Path(__file__).parent / f"codigo_gerado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    saida.write_text(codigo, encoding="utf-8")
    print(f"  Código final salvo em: {saida}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Orquestrador multi-agente PO → Dev → QA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Exemplos:
              python orquestrador.py
              python orquestrador.py --ideia "converter imagens para PDF"
              python orquestrador.py --ideia "resumir PDFs" --max-iter 5
        """)
    )
    parser.add_argument(
        "--ideia",
        default="resumir PDFs automaticamente para o usuário",
        help="Descrição da ideia do produto (default: resumir PDFs)"
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=MAX_ITERACOES,
        help=f"Máximo de iterações Dev→QA (default: {MAX_ITERACOES})"
    )

    args = parser.parse_args()
    orquestrar(ideia=args.ideia, max_iter=args.max_iter)


if __name__ == "__main__":
    main()
