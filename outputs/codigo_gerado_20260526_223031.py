```python
#!/usr/bin/env python3
"""
resumidor.py — Resumidor de PDFs via API Anthropic
Uso: python resumidor.py arquivo.pdf
"""

import os
import sys
from datetime import datetime

import fitz  # PyMuPDF
import anthropic

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_PAGES = 50
MAX_CHARS = 100_000
MIN_CHARS = 50
OUTPUT_SUFFIX = "_resumo"
OUTPUT_EXTENSION = ".txt"
API_TIMEOUT_SECONDS = 60
MODEL_ID = "claude-sonnet-4-5"
PROMPT_TEMPLATE = (
    "Leia o texto abaixo e produza um resumo em português, "
    "em linguagem direta, com entre 5 e 10 linhas.\n\n"
    "Texto:\n{text}"
)


# ---------------------------------------------------------------------------
# Funções
# ---------------------------------------------------------------------------

def parse_arguments() -> str:
    """Lê e retorna o caminho do arquivo PDF passado via sys.argv[1]."""
    if len(sys.argv) < 2:
        print("Uso: python resumidor.py <arquivo.pdf>")
        sys.exit(1)
    return sys.argv[1]


def validate_file(pdf_path: str) -> None:
    """
    Valida existência do arquivo, extensão .pdf e tamanho máximo de 20 MB.
    Encerra com sys.exit(1) em qualquer violação.
    """
    # Valida extensão antes de checar existência para dar mensagem mais precisa
    # quando o arquivo existe mas tem extensão errada. Para arquivos inexistentes
    # sem extensão .pdf, reportamos 'não encontrado' (comportamento aceitável).
    if not pdf_path.lower().endswith(".pdf"):
        print("Erro: o arquivo deve ter extensão .pdf.")
        sys.exit(1)

    if not os.path.exists(pdf_path):
        print(f"Erro: arquivo '{pdf_path}' não encontrado.")
        sys.exit(1)

    file_size = os.path.getsize(pdf_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        print("Erro: arquivo excede o limite de 20 MB.")
        sys.exit(1)


def extract_text(pdf_path: str) -> str:
    """
    Abre o PDF com fitz, itera pelas páginas (máx. 50),
    concatena e retorna o texto bruto extraído.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        print("Erro: não foi possível ler o arquivo PDF. Verifique se ele está corrompido.")
        sys.exit(1)

    try:
        total_pages = len(doc)

        if total_pages == 0:
            return ""

        if total_pages > MAX_PAGES:
            print(f"Aviso: PDF com mais de {MAX_PAGES} páginas — apenas as primeiras {MAX_PAGES} serão processadas.")

        pages_to_read = min(total_pages, MAX_PAGES)
        text_parts = []

        for page_num in range(pages_to_read):
            page = doc.load_page(page_num)
            text_parts.append(page.get_text())

        return "".join(text_parts)

    except Exception:
        print("Erro: não foi possível ler o arquivo PDF. Verifique se ele está corrompido.")
        sys.exit(1)
    finally:
        doc.close()


def validate_text(text: str) -> str:
    """
    Verifica se o texto tem pelo menos 50 caracteres.
    Trunca para 100.000 caracteres com aviso se exceder.
    Retorna o texto pronto para envio.
    """
    if len(text) < MIN_CHARS:
        print("PDF sem texto legível")
        sys.exit(1)

    if len(text) > MAX_CHARS:
        print("Aviso: texto truncado para 100.000 caracteres.")
        text = text[:MAX_CHARS]

    return text


def call_anthropic_api(text: str) -> str:
    """
    Monta o prompt em português, chama a API Anthropic com o modelo definido
    e retorna a string do resumo recebido.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("Erro: variável de ambiente ANTHROPIC_API_KEY não definida.")
        sys.exit(1)

    # O timeout é passado no construtor do cliente para garantir que seja
    # respeitado independentemente da versão do SDK.
    client = anthropic.Anthropic(api_key=api_key, timeout=API_TIMEOUT_SECONDS)

    prompt = PROMPT_TEMPLATE.format(text=text)

    try:
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        return message.content[0].text

    # AuthenticationError deve vir ANTES de APIStatusError pois pode ser subclasse
    except anthropic.AuthenticationError:
        print("Erro: chave de API Anthropic inválida ou não autorizada.")
        sys.exit(1)
    except anthropic.APITimeoutError:
        print("Erro: tempo limite de resposta da API Anthropic excedido.")
        sys.exit(1)
    except anthropic.RateLimitError:
        print("Erro: limite de requisições da API Anthropic atingido. Tente novamente em instantes.")
        sys.exit(1)
    except anthropic.APIStatusError as exc:
        print(f"Erro na API Anthropic (status {exc.status_code}): {exc.message}")
        sys.exit(1)
    except anthropic.APIConnectionError:
        print("Erro: não foi possível conectar à API Anthropic. Verifique sua conexão com a internet.")
        sys.exit(1)
    except anthropic.APIError as exc:
        print(f"Erro na API Anthropic: {exc}")
        sys.exit(1)


def build_output_path(pdf_path: str) -> str:
    """
    Deriva e retorna o caminho do arquivo .txt de saída
    com sufixo _resumo na mesma pasta do PDF.
    """
    base, _ = os.path.splitext(pdf_path)
    return base + OUTPUT_SUFFIX + OUTPUT_EXTENSION


def save_summary(summary: str, pdf_path: str, output_path: str) -> None:
    """
    Grava o arquivo .txt com cabeçalho (nome do PDF + data/hora)
    e o corpo do resumo.
    """
    pdf_basename = os.path.basename(pdf_path)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    header = (
        f"Arquivo original : {pdf_basename}\n"
        f"Gerado em        : {now}\n"
        f"{'-' * 60}\n\n"
    )

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(summary)
            f.write("\n")
        print(f"\nResumo salvo em: {output_path}")
    except OSError as exc:
        print(f"Aviso: não foi possível salvar o arquivo de saída — {exc}")


def print_summary(summary: str) -> None:
    """Imprime o resumo formatado no terminal."""
    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    print(summary)
    print("=" * 60)


def main() -> None:
    """Orquestra todas as funções na sequência correta."""
    pdf_path = parse_arguments()
    validate_file(pdf_path)
    raw_text = extract_text(pdf_path)
    clean_text = validate_text(raw_text)
    summary = call_anthropic_api(clean_text)
    output_path = build_output_path(pdf_path)
    save_summary(summary, pdf_path, output_path)
    print_summary(summary)


if __name__ == "__main__":
    main()
```