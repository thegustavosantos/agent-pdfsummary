# config.py
# ─────────────────────────────────────────────────────────
# Configuração central do pipeline agent-pdfsummary.
# Todos os agentes importam daqui — nunca hardcode nesses valores nos prompts.

# Modelo usado por todos os agentes do pipeline
MODELO_AGENTES = "claude-sonnet-4-6"

# Modelo que o código GERADO pelo Dev deve usar para resumir PDFs
MODELO_GERADO  = "claude-sonnet-4-6"

# Limite de iterações Dev → QA
MAX_ITERACOES  = 3
