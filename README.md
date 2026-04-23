# agent-pdfsummary

Orquestrador multi-agente que transforma uma ideia em código Python testado e aprovado — automaticamente.

O pipeline segue o fluxo **PO → Dev → QA**, com loop de feedback até aprovação ou limite de iterações.

```
ideia (texto)
    │
    ▼
┌─────────┐     requisitos      ┌─────────┐     código        ┌─────────┐
│  Agente │ ─────────────────▶  │  Agente │ ───────────────▶  │  Agente │
│   PO    │                     │   Dev   │  ◀─── feedback ── │   QA    │
└─────────┘                     └─────────┘   (se reprovado)  └─────────┘
                                                                    │
                                                              aprovado?
                                                                    │
                                                             codigo_gerado.py
```

## Estrutura

```
agent-pdfsummary/
├── agentes/
│   ├── orquestrador.py   # ponto de entrada — orquestra o pipeline
│   ├── agente_po.py      # gera requisitos a partir da ideia
│   ├── agente_dev.py     # escreve e corrige o código
│   └── agente_qa.py      # analisa, retorna veredito em JSON
├── tests/
│   └── test_resumidor.py # testes pytest gerados pelo QA
├── logs/                 # runs gravadas em JSON (gitignored)
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Instalação

```bash
git clone https://github.com/seu-usuario/agent-pdfsummary.git
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

# ideia padrão: resumir PDFs
python orquestrador.py

# outra ideia de produto
python orquestrador.py --ideia "transcrever áudios para texto"

# mais tentativas de correção pelo Dev
python orquestrador.py --ideia "resumir PDFs" --max-iter 5
```

## Como funciona

1. **PO** recebe a ideia e gera requisitos funcionais, não funcionais e critérios de aceitação
2. **Dev** recebe os requisitos e escreve o código Python
3. **QA** analisa o código e retorna um JSON com `veredito`, `bugs`, `cobertura` e `deve_reiterar`
4. Se `deve_reiterar = true`, o feedback volta ao Dev para correção — o ciclo se repete
5. Ao final, o código aprovado é salvo em `codigo_gerado_<timestamp>.py` e o log em `logs/`

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
