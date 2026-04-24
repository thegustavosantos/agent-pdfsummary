"""
discovery.py
────────────
Roda PO + Arquiteto UMA única vez e salva o resultado em discovery.md na raiz.

O orquestrador principal lê esse arquivo em vez de chamar PO e Arquiteto a cada run.
Para regenerar o discovery (ex: mudança de escopo), rode este script novamente.
O arquivo discovery.md pode ser editado manualmente entre runs.

Uso:
    python discovery.py            # gera/sobrescreve discovery.md
    python discovery.py --force    # mesmo que acima, sem pedir confirmação
"""

import argparse
from datetime import datetime
from pathlib import Path

import agente_po
import agente_arquiteto
from config import DISCOVERY_FILE, IDEIA


def separador(titulo: str, char: str = "─", largura: int = 60) -> None:
    print(f"\n{char * largura}")
    print(f"  {titulo}")
    print(f"{char * largura}")


def resumir(texto: str, max_chars: int = 400) -> str:
    if len(texto) <= max_chars:
        return texto
    return texto[:max_chars] + f"\n  ... ({len(texto) - max_chars} chars omitidos)"


def rodar_discovery(force: bool = False) -> None:

    # Se já existe, pede confirmação antes de sobrescrever
    if DISCOVERY_FILE.exists() and not force:
        print(f"\n  discovery.md já existe em: {DISCOVERY_FILE}")
        resposta = input("  Deseja sobrescrever? (s/N): ").strip().lower()
        if resposta != "s":
            print("  Operação cancelada. Discovery existente mantido.\n")
            return

    print(f"\n{'═' * 60}")
    print(f"  DISCOVERY — PO + Arquiteto")
    print(f"  Ideia: {IDEIA}")
    print(f"{'═' * 60}")

    # ── PO ───────────────────────────────────────────────────────────────────
    separador("AGENTE 1 — Product Owner")
    print("  Gerando requisitos...")
    requisitos = agente_po.executar(IDEIA)
    print(resumir(requisitos))

    # ── Arquiteto ─────────────────────────────────────────────────────────────
    separador("AGENTE 2 — Arquiteto")
    print("  Definindo plano técnico...")
    plano = agente_arquiteto.executar(requisitos)
    print(resumir(plano))

    # ── Salva como Markdown (editável manualmente) ────────────────────────────
    gerado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conteudo = (
        f"# Discovery — agent-pdfsummary\n\n"
        f"**Gerado em:** {gerado_em}\n"
        f"**Ideia:** {IDEIA}\n\n"
        f"## Requisitos\n\n"
        f"{requisitos}\n\n"
        f"## Plano Técnico\n\n"
        f"{plano}\n"
    )

    DISCOVERY_FILE.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERY_FILE.write_text(conteudo, encoding="utf-8")

    print(f"\n{'═' * 60}")
    print(f"  Discovery salvo em: {DISCOVERY_FILE}")
    print(f"  Você pode editar discovery.md antes de rodar o pipeline.")
    print(f"  Execute 'python orquestrador.py' para rodar o pipeline.")
    print(f"{'═' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Gera e salva o discovery (PO + Arquiteto) em discovery.md"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescreve discovery.md existente sem pedir confirmação"
    )
    args = parser.parse_args()
    rodar_discovery(force=args.force)


if __name__ == "__main__":
    main()
