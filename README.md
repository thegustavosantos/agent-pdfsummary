# agent-pdfsummary

Pipeline multi-agente especializado em geração de código Python para resumo de PDFs.

O pipeline segue o fluxo **PO → Arquiteto → Dev → QA**, com loop de feedback entre Dev e QA até aprovação ou limite de iterações.

```
┌──────────┐  requisitos  ┌────────────┐  plano técnico  ┌─────────┐
│  Agente  │ ───────────▶ │   Agente   │ ──────────────▶ │  Agente │
│    PO    │              │  Arquiteto │                  │   Dev   │
└──────────┘              └────────────┘                  └────┬────┘
                                                               │  código
                                                          ┌────▼────┐
                                                          │  Agente │
                                                          │   QA    │
                                                          └────┬────┘
                                                               │
                                              reprovado? ──────┘ (feedback → Dev)
                                              aprovado?  ──────▶ codigo_gerado.py
```

## Estrutura

```
agent-pdfsummary/
├── agents/
│   ├── orquestrador.py      # ponto de entrada — orquestra o pipeline
│   ├── agente_po.py         # define requisitos do domínio PDF summary
│   ├── agente_arquiteto.py  # define plano técnico antes do Dev escrever
│   ├── agente_dev.py        # implementa o código seguindo o plano
│   └── agente_qa.py         # analisa e retorna veredito em JSON
├── outputs/                 # código gerado em cada run (versionado)
├── logs/                    # logs JSON de cada run (gitignored)
├── .env.example
├── .gitignore
├── requirements.txt
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
cd agents

# rodar o pipeline completo
python orquestrador.py

# permitir mais tentativas de correção pelo Dev
python orquestrador.py --max-iter 5
```

## Como funciona

1. **PO** gera requisitos funcionais e técnicos para um script CLI de resumo de PDFs
2. **Arquiteto** recebe os requisitos e entrega um plano técnico: funções, fluxo de dados, constantes, pontos de falha e formato de saída
3. **Dev** implementa o script seguindo exatamente o plano do Arquiteto
4. **QA** analisa o código e retorna um JSON com `veredito`, `bugs`, `cobertura` e `deve_reiterar`
5. Se `deve_reiterar = true`, o feedback volta ao Dev para correção — o ciclo se repete
6. Ao final, o código aprovado é salvo em `codigo_gerado_<timestamp>.py` e o log completo em `logs/`

## Vereditos do QA

| Veredito | Significado |
|---|---|
| `aprovado` | Sem ressalvas, pronto para uso |
| `aprovado_com_ressalvas` | Funciona, mas há pontos de melhoria |
| `reprovado` | Bugs críticos — Dev recebe feedback e corrige |

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `ANTHROPIC_API_KEY` | Chave da API Anthropic (obrigatória) |

## Requisitos

- Python 3.9+
- Conta na [Anthropic](https://console.anthropic.com) com acesso à API
