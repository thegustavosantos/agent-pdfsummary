# Discovery — agent-pdfsummary

**Gerado em:** 2026-04-23 23:31:02
**Ideia:** resumir PDFs automaticamente para o usuário via script CLI em Python

## Requisitos

# Requisitos – resumidor.py

## 1. Requisitos Funcionais
- Aceita um arquivo .pdf como argumento via terminal (`python resumidor.py relatorio.pdf`)
- Extrai o texto bruto do PDF usando PyMuPDF (fitz)
- Envia o texto extraído para a API Anthropic e recebe um resumo em português
- Imprime o resumo no terminal ao final da execução
- Salva o resumo em um arquivo .txt com o mesmo nome do PDF (`relatorio_resumo.txt`)

## 2. Limites Técnicos
- Tamanho máximo do arquivo: 20 MB
- Número máximo de páginas: 50 páginas
- Texto enviado à API limitado a 100.000 caracteres (truncado com aviso se exceder)

## 3. Tratamento de Erros
- Arquivo não encontrado: imprime mensagem clara e encerra com `sys.exit(1)`
- Extensão diferente de .pdf: imprime aviso e encerra
- Texto extraído vazio ou abaixo de 50 caracteres: imprime "PDF sem texto legível" e encerra
- Falha na API Anthropic (timeout, chave inválida, etc): imprime a mensagem de erro da API e encerra
- PDF corrompido ou ilegível pelo fitz: captura exceção e imprime mensagem de arquivo inválido

## 4. Formato da Saída
- Resumo impresso diretamente no terminal ao fim da execução
- Resumo salvo em `.txt` na mesma pasta do PDF de entrada
- Arquivo `.txt` inclui nome do PDF original e data/hora da geração no cabeçalho
- Estrutura do resumo: 5 a 10 linhas em português, em linguagem direta

## Plano Técnico

# PLANO TÉCNICO — resumidor.py

---

## 1. ESTRUTURA DE FUNÇÕES

- `parse_arguments() -> str` — Lê e retorna o caminho do arquivo PDF passado via `sys.argv[1]`; encerra com mensagem de uso se nenhum argumento for fornecido
- `validate_file(pdf_path: str) -> None` — Valida existência do arquivo, extensão `.pdf` e tamanho máximo de 20 MB; encerra com `sys.exit(1)` em qualquer violação
- `extract_text(pdf_path: str) -> str` — Abre o PDF com `fitz`, itera pelas páginas (máx. 50), concatena e retorna o texto bruto extraído
- `validate_text(text: str) -> str` — Verifica se o texto tem pelo menos 50 caracteres; trunca para 100.000 caracteres com aviso se exceder; retorna o texto pronto para envio
- `call_anthropic_api(text: str) -> str` — Monta o prompt em português, chama a API Anthropic com o modelo definido e retorna a string do resumo recebido
- `build_output_path(pdf_path: str) -> str` — Deriva e retorna o caminho do arquivo `.txt` de saída com sufixo `_resumo` na mesma pasta do PDF
- `save_summary(summary: str, pdf_path: str, output_path: str) -> None` — Grava o arquivo `.txt` com cabeçalho (nome do PDF + data/hora) e o corpo do resumo
- `print_summary(summary: str) -> None` — Imprime o resumo formatado no terminal
- `main() -> None` — Orquestra todas as funções na sequência correta; ponto de entrada do script

---

## 2. FLUXO DE DADOS

```
main()
  │
  ├─► parse_arguments()
  │     └─► retorna: pdf_path (str)
  │
  ├─► validate_file(pdf_path)
  │     └─► sem retorno; encerra em falha
  │
  ├─► extract_text(pdf_path)
  │     └─► retorna: raw_text (str)
  │
  ├─► validate_text(raw_text)
  │     └─► retorna: clean_text (str, máx 100.000 chars)
  │
  ├─► call_anthropic_api(clean_text)
  │     └─► retorna: summary (str)
  │
  ├─► build_output_path(pdf_path)
  │     └─► retorna: output_path (str)
  │
  ├─► save_summary(summary, pdf_path, output_path)
  │     └─► sem retorno; grava arquivo .txt
  │
  └─► print_summary(summary)
        └─► sem retorno; imprime no terminal
```

---

## 3. CONSTANTES E CONFIGURAÇÕES

```python
MAX_FILE_SIZE_MB     = 20
MAX_FILE_SIZE_BYTES  = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_PAGES            = 50
MAX_CHARS            = 100_000
MIN_CHARS            = 50
OUTPUT_SUFFIX        = "_resumo"
OUTPUT_EXTENSION     = ".txt"
API_TIMEOUT_SECONDS  = 60
PROMPT_TEMPLATE      = (
    "Leia o texto abaixo e produza um resumo em português, "
    "em linguagem direta, com entre 5 e 10 linhas.\n\n"
    "Texto:\n{text}"
)
```

> O Dev deve declarar também a variável de ambiente `ANTHROPIC_API_KEY`, lida via `os.environ` em tempo de execução — nunca hard-coded.

---

## 4. PONTOS DE FALHA

| Situação | Exceção / Condição | Mensagem a exibir | Ação |
|---|---|---|---|
| Nenhum argumento passado | `len(sys.argv) < 2` | `"Uso: python resumidor.py <arquivo.pdf>"` | `sys.exit(1)` |
| Arquivo não encontrado | `not os.path.exists(pdf_path)` | `"Erro: arquivo '{pdf_path}' não encontrado."` | `sys.exit(1)` |
| Extensão diferente de .pdf | `not pdf_path.lower().endswith(".pdf")` | `"Erro: o arquivo deve ter extensão .pdf."` | `sys.exit(1)` |
| Arquivo excede 20 MB | tamanho > `MAX_FILE_SIZE_BYTES` | `"Erro: arquivo excede o limite de 20 MB."` | `sys.exit(1)` |
| PDF corrompido ou ilegível | `Exception` em `fitz.open()` ou `.get_text()` | `"Erro: não foi possível ler o arquivo PDF. Verifique se ele está corrompido."` | `sys.exit(1)` |
| PDF excede 50 páginas | `len(doc) > MAX_PAGES` | `"Aviso: PDF com mais de 50 páginas — apenas as primeiras 50 serão processadas."` | Continua com as 50 primeiras |
| Texto extraído insuficiente | `len(text) < MIN_CHARS` | `"Erro: PDF sem texto legível."` | `sys.exit(1)` |
| Texto excede 100.000 chars | `len(text) > MAX_CHARS` | `"Aviso: texto truncado para 100.000 caracteres."` | Trunca e continua |
| Chave de API ausente | `KeyError` / `os.environ` vazio | `"Erro: variável de ambiente ANTHROPIC_API_KEY não definida."` | `sys.exit(
