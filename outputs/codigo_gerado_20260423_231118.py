```python
#!/usr/bin/env python3
"""
resumidor.py — Script CLI para resumir arquivos PDF usando a API da Anthropic.

Uso:
    python resumidor.py arquivo.pdf

Dependências:
    pip install pymupdf anthropic
"""

import os
import sys
import pathlib

import fitz  # PyMuPDF
import anthropic

# ---------------------------------------------------------------------------
# Constantes e configurações globais
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB em bytes
MAX_PAGES = 50                           # Número máximo de páginas permitidas
MAX_CHARS = 50_000                       # Limite de caracteres enviados à API
OUTPUT_SUFFIX = "_resumo.txt"            # Sufixo do arquivo de saída gerado
ANTHROPIC_MODEL = "claude-sonnet-4-5"   # Modelo da Anthropic utilizado

USAGE_INSTRUCTION = "Uso: python resumidor.py arquivo.pdf"

# Template do prompt enviado à API — {text} é substituído pelo conteúdo extraído
PROMPT_TEMPLATE = (
    "Leia o texto a seguir e produza um resumo claro e objetivo em português, "
    "destacando os pontos principais:\n\n{text}"
)


# ---------------------------------------------------------------------------
# Funções
# ---------------------------------------------------------------------------

def parse_arguments() -> str:
    """
    Valida que exatamente um argumento foi passado via CLI.

    Retorna o caminho do arquivo informado como string.
    Encerra o programa com mensagem de uso se nenhum argumento for fornecido.
    """
    # Verifica se o usuário informou pelo menos um argumento além do nome do script
    if len(sys.argv) < 2:
        print("Erro: nenhum arquivo informado.")
        print(USAGE_INSTRUCTION)
        sys.exit(1)

    # Retorna o primeiro argumento posicional (caminho do PDF)
    return sys.argv[1]


def validate_pdf(filepath: str) -> pathlib.Path:
    """
    Valida o arquivo informado pelo usuário.

    Verificações realizadas (em ordem):
      1. Extensão deve ser .pdf
      2. Arquivo deve existir no sistema de arquivos
      3. Tamanho não pode exceder MAX_FILE_SIZE_BYTES (20 MB)
      4. Número de páginas não pode exceder MAX_PAGES (50)

    Parâmetros:
        filepath: caminho bruto do arquivo como string

    Retorna:
        pathlib.Path validado do arquivo PDF
    """
    pdf_path = pathlib.Path(filepath)

    # --- Verificação 1: extensão do arquivo ---
    if pdf_path.suffix.lower() != ".pdf":
        print("Erro: o arquivo deve ter extensão .pdf.")
        sys.exit(1)

    # --- Verificação 2: existência do arquivo ---
    if not pdf_path.exists():
        print(f"Erro: arquivo '{filepath}' não encontrado.")
        sys.exit(1)

    # --- Verificação 3: tamanho máximo ---
    file_size = os.path.getsize(pdf_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        print("Erro: arquivo excede o limite de 20 MB.")
        sys.exit(1)

    # --- Verificação 4: número máximo de páginas ---
    # Abre o documento apenas para contar páginas; será fechado em seguida
    try:
        doc = fitz.open(str(pdf_path))
        num_pages = len(doc)
        doc.close()
    except fitz.FileDataError as exc:
        print(f"Erro ao abrir o PDF: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"Erro ao abrir o PDF: {exc}")
        sys.exit(1)

    if num_pages > MAX_PAGES:
        print("Erro: o PDF excede o limite de 50 páginas.")
        sys.exit(1)

    return pdf_path


def extract_text(filepath: pathlib.Path) -> str:
    """
    Abre o PDF com PyMuPDF e extrai o texto de todas as páginas.

    O texto de cada página é concatenado com quebra de linha dupla entre elas.
    Encerra o programa com aviso se o texto resultante estiver vazio.

    Parâmetros:
        filepath: pathlib.Path validado do arquivo PDF

    Retorna:
        String com o texto completo extraído do PDF
    """
    try:
        doc = fitz.open(str(filepath))
    except fitz.FileDataError as exc:
        print(f"Erro ao abrir o PDF: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"Erro ao abrir o PDF: {exc}")
        sys.exit(1)

    # Percorre todas as páginas e coleta o texto de cada uma
    pages_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text()  # Extrai texto da página atual
        pages_text.append(page_text)

    doc.close()

    # Junta o texto de todas as páginas
    full_text = "\n\n".join(pages_text)

    # Verifica se algum texto foi extraído (PDFs de imagem retornam string vazia)
    if not full_text.strip():
        print(
            "Erro: nenhum texto pôde ser extraído. "
            "O PDF pode ser baseado em imagem."
        )
        sys.exit(1)

    return full_text


def truncate_text(text: str, limit: int) -> str:
    """
    Retorna os primeiros `limit` caracteres do texto.

    Se o texto já estiver dentro do limite, é retornado sem modificações.
    Função pura — sem efeitos colaterais.

    Parâmetros:
        text:  string com o texto completo extraído
        limit: número máximo de caracteres permitidos

    Retorna:
        String truncada ou original conforme o limite
    """
    if len(text) <= limit:
        return text

    # Informa ao usuário que o texto foi truncado
    print(
        f"Aviso: o texto extraído ({len(text)} caracteres) excede o limite de "
        f"{limit} caracteres e será truncado antes do envio à API."
    )
    return text[:limit]


def call_anthropic_api(text: str) -> str:
    """
    Envia o texto para a API da Anthropic e retorna o resumo gerado.

    Instancia o cliente Anthropic (lê ANTHROPIC_API_KEY do ambiente),
    constrói o prompt usando PROMPT_TEMPLATE e faz a chamada síncrona.
    Encerra o programa com mensagem de erro se a chamada falhar.

    Parâmetros:
        text: string com o texto (possivelmente truncado) a ser resumido

    Retorna:
        String com o conteúdo textual do resumo gerado pela API
    """
    # Monta o prompt final substituindo {text} pelo conteúdo extraído
    prompt = PROMPT_TEMPLATE.format(text=text)

    try:
        # Instancia o cliente — a chave de API é lida automaticamente
        # da variável de ambiente ANTHROPIC_API_KEY
        client = anthropic.Anthropic()

        print("Enviando texto para a API da Anthropic. Aguarde...")

        # Realiza a chamada à API com o modelo definido
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

    except anthropic.APIConnectionError as exc:
        print(f"Erro de conexão com a API Anthropic: {exc}")
        sys.exit(1)
    except anthropic.AuthenticationError as exc:
        print(f"Erro de autenticação na API Anthropic: {exc}")
        sys.exit(1)
    except anthropic.RateLimitError as exc:
        print(f"Limite de requisições atingido na API Anthropic: {exc}")
        sys.exit(1)
    except anthropic.APIStatusError as exc:
        print(f"Erro retornado pela API Anthropic (status {exc.status_code}): {exc.message}")
        sys.exit(1)
    except Exception as exc:
        print(f"Erro inesperado ao chamar a API Anthropic: {exc}")
        sys.exit(1)

    # Extrai apenas o conteúdo textual da resposta
    summary = message.content[0].text
    return summary


def build_output_path(filepath: pathlib.Path) -> pathlib.Path:
    """
    Deriva o caminho do arquivo de saída a partir do nome original do PDF.

    O arquivo de saída é criado na mesma pasta do PDF original,
    com o sufixo OUTPUT_SUFFIX substituindo a extensão .pdf.

    Exemplo:
        entrada:  /docs/relatorio.pdf
        saída:    /docs/relatorio_resumo.txt

    Parâmetros:
        filepath: pathlib.Path do arquivo PDF original

    Retorna:
        pathlib.Path do arquivo .txt de destino
    """
    # Remove a extensão .pdf e adiciona o sufixo de resumo
    stem = filepath.stem                     # Nome sem extensão
    output_filename = stem + OUTPUT_SUFFIX   # Ex: "relatorio_resumo.txt"
    output_path = filepath.parent / output_filename  # Mesma pasta do PDF

    return output_path


def save_summary(summary: str, output_path: pathlib.Path) -> None:
    """
    Grava o resumo gerado no arquivo .txt de destino.

    Encerra o programa com mensagem de erro se a gravação falhar.

    Parâmetros:
        summary:     string com o resumo gerado pela API
        output_path: pathlib.Path do arquivo de destino
    """
    try:
        # Grava o arquivo com codificação UTF-8 para suporte completo a português
        output_path.write_text(summary, encoding="utf-8")
    except OSError as exc:
        print(f"Erro ao salvar o arquivo de resumo: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"Erro inesperado ao salvar o arquivo de resumo: {exc}")
        sys.exit(1)


def print_results(summary: str, output_path: pathlib.Path) -> None:
    """
    Imprime o resumo no terminal seguido do caminho do arquivo salvo.

    Parâmetros:
        summary:     string com o resumo gerado
        output_path: pathlib.Path do arquivo onde o resumo foi salvo
    """
    # Separador visual para destacar o resumo no terminal
    separator = "=" * 60

    print()
    print(separator)
    print("RESUMO GERADO:")
    print(separator)
    print(summary)
    print(separator)
    print()
    print(f"Resumo salvo em: {output_path.resolve()}")


def main() -> None:
    """
    Ponto de entrada principal do script.

    Orquestra a execução sequencial de todas as funções:
      1. Lê e valida o argumento CLI
      2. Valida o arquivo PDF
      3. Extrai o texto do PDF
      4. Trunca o texto se necessário
      5. Envia o texto para a API da Anthropic
      6. Determina o caminho do arquivo de saída
      7. Salva o resumo em disco
      8. Exibe o resumo e o caminho do arquivo no terminal
    """
    # Passo 1 — Lê o argumento passado via linha de comando
    filepath_str = parse_arguments()

    # Passo 2 — Valida o arquivo PDF (existência, extensão, tamanho, páginas)
    pdf_path = validate_pdf(filepath_str)

    print(f"Arquivo validado: {pdf_path.resolve()}")

    # Passo 3 — Extrai o texto completo do PDF
    print("Extraindo texto do PDF...")
    raw_text = extract_text(pdf_path)
    print(f"Texto extraído: {len(raw_text)} caracteres.")

    # Passo 4 — Trunca o texto ao limite máximo permitido pela API
    safe_text = truncate_text(raw_text, MAX_CHARS)

    # Passo 5 — Envia o texto para a API e obtém o resumo
    summary = call_anthropic_api(safe_text)

    # Passo 6 — Constrói o caminho do arquivo de saída
    output_path = build_output_path(pdf_path)

    # Passo 7 — Salva o resumo no arquivo .txt
    save_summary(summary, output_path)

    # Passo 8 — Exibe o resumo e o caminho do arquivo no terminal
    print_results(summary, output_path)


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
```