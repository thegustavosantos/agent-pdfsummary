# Changelog

Todas as mudanças relevantes do projeto são documentadas aqui.

---

## [Unreleased] — 2026-04-23

### Added
- `agentes/discovery.py` — script único que roda PO + Arquiteto e salva `discovery.md`; suporta `--force` para sobrescrever sem confirmação
- `agentes/agente_reviewer.py` — agente Reviewer que compara versões do código gerado e detecta regressões entre runs
- Cross-run memory: `orquestrador.py` lê o log da run anterior e passa bugs e veredito do QA como contexto ao Dev para evitar regressões

### Changed
- `discovery.json` → `discovery.md`: arquivo editável manualmente com seções `## Requisitos` e `## Plano Técnico`; orquestrador parseia as seções por cabeçalho em vez de desserializar JSON
- `agentes/agente_dev.py`: aceita parâmetro `memoria` e injeta bugs da run anterior no prompt via tag `<memoria_run_anterior>`
- `agentes/config.py`: expõe constantes `DISCOVERY_FILE`, `LOGS_DIR` e `OUTPUTS_DIR`

---

## [0.4.0] — 2026-04-23 · `9d9d057`

### Changed
- Centraliza modelo, `IDEIA` e caminhos em `config.py`; elimina hardcode duplicado nos agentes

---

## [0.3.0] — 2026-04-23 · `a13aafd`

### Added
- `agentes/agente_arquiteto.py` — agente Arquiteto que transforma requisitos do PO em plano técnico detalhado (funções, fluxo de dados, pontos de falha)
- Pipeline especializado no domínio de resumo de PDFs via CLI

### Changed
- Remove argumento `--ideia` do CLI; ideia fixada em `config.py`
- Move outputs de `agentes/outputs/` para `outputs/` na raiz do projeto

---

## [0.2.0] — 2026-04-23 · `2d38714`

### Changed
- Código gerado salvo em `outputs/codigo_gerado_<timestamp>.py` para rastreabilidade entre runs

---

## [0.1.1] — 2026-04-23 · `25c5593`

### Fixed
- Escopo do PO restrito a CLI simples em Python (sem web, cloud ou banco de dados)
- `max_tokens` do Dev aumentado para evitar truncamento do código gerado
- Caminho do diretório de logs corrigido

---

## [0.1.0] — 2026-04-23 · `60e57ba`

### Added
- Pipeline multi-agente inicial: PO → Dev → QA para sumarização de PDFs
- Loop de feedback Dev → QA com até `MAX_ITERACOES` iterações
- Log por run em `agentes/logs/run_<timestamp>.json`
