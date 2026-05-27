# Changelog

Todas as mudanças relevantes do projeto são documentadas aqui.

---

## [Unreleased]

---

## [0.8.0] — 2026-05-26 · `b5afd17`

### Refactor
- Renomeia `orquestrador.py` → `pipeline_sequencial.py` e `orquestrador_agente.py` → `pipeline_agente.py` — nomes refletem a diferença entre os dois modos de execução
- Move `agentes/logs/` → `logs/` na raiz do projeto — separa artefatos gerados do código fonte
- Atualiza `config.py`: `LOGS_DIR` passa a apontar para `ROOT / "logs"`
- Adiciona `__pycache__/`, `agentes/sandbox/` e `logs/` ao `.gitignore`

---

## [0.7.0] — 2026-05-26 · `e9fef6e`

### Added
- `agentes/executor_shell.py` — wrapper seguro para subprocess com whitelist de comandos (`python`, `pytest`, `pip`), timeout configurável por tipo de operação e execução isolada em `agentes/sandbox/`
- `agentes/sandbox/` — pasta isolada onde o código gerado é salvo e executado pelos agentes
- Auto-validação de sintaxe no `agente_dev.py`: após gerar o código, roda `python -m py_compile` na sandbox; corrige automaticamente erros de sintaxe em até 3 tentativas antes de entregar ao QA
- QA com pytest real no `agente_qa.py`: gera `test_resumidor.py` com mocks de fitz e Anthropic, executa `pytest` de verdade no shell e interpreta o output real para montar o veredito

### Changed
- `agentes/config.py`: adiciona constante `SANDBOX_DIR`
- `agentes/agente_dev.py`: extrai código de blocos markdown antes de salvar na sandbox
- `agentes/agente_qa.py`: veredito agora é baseado em resultado real de execução, não só análise estática; campo `pytest_output` adicionado ao JSON de retorno

---

## [0.6.0] — 2026-05-26 · `9b2e1d0`

### Added
- `agentes/pipeline_agente.py` (ex `orquestrador_agente.py`) — orquestrador com raciocínio dinâmico usando padrão Stateless Orchestrator: um LLM decide a próxima ação com base em um snapshot de estado fixo (~500 tokens por decisão), sem acúmulo de histórico
- Flag `--verbose` no `pipeline_agente.py`: exibe estado completo e decisão a cada turno do orquestrador
- Fallback seguro no decisor: se o LLM retornar ação desconhecida, encerra o pipeline em vez de travar

---

## [0.5.0] — 2026-04-23

### Added
- `agentes/discovery.py` — script único que roda PO + Arquiteto e salva `discovery.md`; suporta `--force` para sobrescrever sem confirmação
- `agentes/agente_reviewer.py` — agente Reviewer que compara versões do código gerado e detecta regressões entre runs
- Cross-run memory: `pipeline_sequencial.py` lê o log da run anterior e passa bugs e veredito do QA como contexto ao Dev para evitar regressões

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
- Log por run em `logs/run_<timestamp>.json`