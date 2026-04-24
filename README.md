# agent-pdfsummary

Pipeline multi-agente que gera um script Python de resumo de PDFs via CLI.

O pipeline é dividido em duas fases: **Discovery** (executado uma única vez) e **Orquestração** (executado a cada iteração de melhoria).

```
╔══ DISCOVERY (uma vez) ═══════════════════════════════════════╗
║                                                               ║
║  ┌──────────┐  requisitos  ┌────────────┐  plano técnico     ║
║  │  Agente  │ ───────────▶ │   Agente   │ ──────────────▶    ║
║  │    PO    │              │  Arquiteto │   discovery.md      ║
║  └──────────┘              └────────────┘  (editável)         ║
╚═══════════════════════════════════════════════════════════════╝

╔══ ORQUESTRAÇÃO (a cada run) ═════════════════════════════════╗
║                                                               ║
║  discovery.md ──▶ ┌─────────┐  código                        ║
║  memória anterior │  Agente │ ──────────▶ ┌──────────┐       ║
║  (bugs do QA)  ──▶│   Dev   │             │  Agente  │       ║
║                   └─────────┘             │    QA    │       ║
║                       ▲                   └────┬─────┘       ║
║                       │  feedback              │              ║
║                       └────────────────────────┘             ║
║                          (se deve_reiterar = true)            ║
║                                                               ║
║  código anterior ──▶ ┌──────────┐                            ║
║  código atual    ──▶ │  Agente  │ ──▶ evolucoes / regressoes  ║
║                      │ Reviewer │                             ║
║                      └──────────┘                             ║
╚═══════════════════════════════════════════════════════════════╝
```

## Estrutura

```
agent-pdfsummary/
├── agentes/
│   ├── discovery.py         # fase 1 — roda PO + Arquiteto, gera discovery.md
│   ├── orquestrador.py      # fase 2 — pipeline Dev → QA → Reviewer
│   ├── agente_po.py         # define requisitos do domínio PDF summary
│   ├── agente_arquiteto.py  # define plano técnico antes do Dev escrever
│   ├── agente_dev.py        # implementa o código seguindo o plano
│   ├── agente_qa.py         # analisa e retorna veredito em JSON
│   ├── agente_reviewer.py   # compara versões e detecta regressões
│   ├── config.py            # configuração central (modelo, caminhos, limites)
│   └── logs/                # log JSON de cada run (gitignored)
├── outputs/                 # código gerado em cada run
├── discovery.md             # requisitos + plano técnico (editável manualmente)
├── .env.example
├── .gitignore
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

## Instalação

```bash
git clone https://github.com/thegustavosantos/agent-pdfsummary.git
cd agent-pdfsummary

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edite .env e adicione sua ANTHROPIC_API_KEY
```

## Uso

```bash
cd agentes

# 1ª vez — gera discovery.md com requisitos e plano técnico
python discovery.py

# rodar o pipeline de geração e revisão de código
python orquestrador.py

# permitir mais tentativas de correção pelo Dev
python orquestrador.py --max-iter 5

# regenerar o discovery (ex: mudança de escopo)
python discovery.py --force
```

> **Dica:** após rodar `discovery.py`, abra `discovery.md` na raiz e edite os requisitos ou o plano técnico antes de rodar o orquestrador.

## Como funciona

### Fase 1 — Discovery (uma vez)

1. **PO** gera requisitos funcionais e técnicos para um script CLI de resumo de PDFs
2. **Arquiteto** recebe os requisitos e entrega um plano técnico: funções, fluxo de dados, constantes, pontos de falha e formato de saída
3. O resultado é salvo em `discovery.md` — editável manualmente antes de cada run

### Fase 2 — Orquestração (a cada run)

4. **Dev** lê `discovery.md` e implementa o script seguindo o plano do Arquiteto; recebe bugs da run anterior como contexto para evitar regressões
5. **QA** analisa o código e retorna um JSON com `veredito`, `bugs`, `cobertura` e `deve_reiterar`
6. Se `deve_reiterar = true`, o feedback volta ao Dev para correção — o ciclo se repete até aprovação ou limite de iterações
7. **Reviewer** compara o código gerado com a versão anterior e aponta evoluções e regressões
8. Ao final, o código é salvo em `outputs/codigo_gerado_<timestamp>.py` e o log em `agentes/logs/`

## Vereditos do QA

| Veredito | Significado |
|---|---|
| `aprovado` | Sem ressalvas, pronto para uso |
| `aprovado_com_ressalvas` | Funcional, mas com pontos de melhoria |
| `reprovado` | Bugs críticos — Dev recebe feedback e corrige |

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `ANTHROPIC_API_KEY` | Chave da API Anthropic (obrigatória) |

## Requisitos

- Python 3.10+
- Conta na [Anthropic](https://console.anthropic.com) com acesso à API
