# config.py
# ─────────────────────────────────────────────────────────
# Configuração central do pipeline agent-pdfsummary.
# Todos os agentes importam daqui — nunca hardcode nesses valores nos prompts.

from pathlib import Path

# Raiz do projeto (um nível acima de agents/)
ROOT = Path(__file__).parent.parent

# Ideia central do produto — imutável, define o domínio do pipeline
IDEIA = "resumir PDFs automaticamente para o usuário via script CLI em Python"

# Modelo usado por todos os agentes do pipeline
MODELO_AGENTES = "claude-sonnet-4-6"

# Modelo que o código GERADO pelo Dev deve usar para resumir PDFs
MODELO_GERADO  = "claude-sonnet-4-6"

# Limite de iterações Dev → QA
MAX_ITERACOES  = 3

# Caminhos
DISCOVERY_FILE = ROOT / "discovery.md"     # requisitos + plano salvos pelo PO/Arquiteto
LOGS_DIR       = Path(__file__).parent / "logs"
OUTPUTS_DIR    = ROOT / "outputs"
