```python
#!/usr/bin/env python3
"""
resumidor.py — Resumidor de PDFs via API Anthropic
Uso: python resumidor.py <arquivo.pdf>
"""

import os
import sys
from datetime import datetime

import anthropic
import fitz  # PyMuPDF

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
MODEL_NAME = "claude-sonnet-4-5"
PROMPT_TEMPLATE = (
    "Leia o texto abaixo e produza um resumo em português, "
    "em linguagem direta, com entre 5 e 10 linhas.\n\n"
    "Texto:\n{text}"
)


# ---------------------------------------------------------------------------
# 1. parse_arguments
# ---------------------------------------------------------------------------
def parse_arguments() -> str:
    """Lê e retorna o caminho do arquivo PDF passado via sys.argv[1]."""
    if len(sys.argv) < 2:
        print("Uso: python resumidor.py <arquivo.pdf>")
        sys.exit(1)
    return sys.argv[1]


# ---------------------------------------------------------------------------
# 2. validate_file
# ---------------------------------------------------------------------------
def validate_file(pdf_path: str) -> None:
    """
    Valida, nesta ordem:
      1. Existência do arquivo
      2. Extensão .pdf
      3. Tamanho máximo de 20 MB
    Encerra com sys.exit(1) em qualquer violação.
    """
    # 1. Existência — verificada PRIMEIRO conforme requisito
    if not os.path.exists(pdf_path):
        print(f"Erro: arquivo '{pdf_path}' não encontrado.")
        sys.exit(1)

    # 2. Extensão
    if not pdf_path.lower().endswith(".pdf"):
        print("Erro: o arquivo deve ter extensão .pdf.")
        sys.exit(1)

    # 3. Tamanho
    file_size = os.path.getsize(pdf_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        print(f"Erro: arquivo excede o limite de {MAX_FILE_SIZE_MB} MB.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 3. validate_api_key
# ---------------------------------------------------------------------------
def validate_api_key() -> str:
    """
    Lê ANTHROPIC_API_KEY do ambiente.
    Encerra com mensagem orientativa se não estiver definida.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print(
            "Erro: variável de ambiente ANTHROPIC_API_KEY não definida. "
            "Defina-a com: export ANTHROPIC_API_KEY='sua-chave'"
        )
        sys.exit(1)
    return api_key


# ---------------------------------------------------------------------------
# 4. extract_text
# ---------------------------------------------------------------------------
def extract_text(pdf_path: str) -> str:
    """
    Abre o PDF com fitz UMA única vez, itera pelas páginas (máx. 50),
    concatena e retorna o texto bruto extraído.
    Encerra com sys.exit(1) se o arquivo estiver corrompido ou ilegível.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        print(
            f"Erro: não foi possível ler o arquivo PDF. "
            f"Verifique se ele está corrompido. (Detalhe: {exc})"
        )
        sys.exit(1)

    try:
        total_pages = len(doc)
        if total_pages > MAX_PAGES:
            print(
                f"Aviso: PDF com mais de {MAX_PAGES} páginas — "
                f"apenas as primeiras {MAX_PAGES} serão processadas."
            )

        pages_to_read = min(total_pages, MAX_PAGES)
        text_parts: list[str] = []

        for page_index in range(pages_to_read):
            try:
                page = doc[page_index]
                text_parts.append(page.get_text())
            except Exception as exc:
                print(
                    f"Erro: não foi possível ler a página {page_index + 1} do PDF. "
                    f"Verifique se ele está corrompido. (Detalhe: {exc})"
                )
                sys.exit(1)

        return "".join(text_parts)

    finally:
        doc.close()


# ---------------------------------------------------------------------------
# 5. validate_text
# ---------------------------------------------------------------------------
def validate_text(text: str) -> str:
    """
    Verifica comprimento mínimo (50 chars) e trunca em 100.000 chars com aviso.
    Retorna o texto pronto para envio à API.
    """
    if len(text) < MIN_CHARS:
        print("Erro: PDF sem texto legível.")
        sys.exit(1)

    if len(text) > MAX_CHARS:
        print(f"Aviso: texto truncado para {MAX_CHARS:,} caracteres.")
        text = text[:MAX_CHARS]

    return text


# ---------------------------------------------------------------------------
# 6. call_anthropic_api
# ---------------------------------------------------------------------------
def call_anthropic_api(text: str, api_key: str) -> str:
    """
    Monta o prompt em português, chama a API Anthropic e retorna o resumo.
    Encerra com sys.exit(1) em caso de qualquer falha na API.
    """
    prompt = PROMPT_TEMPLATE.format(text=text)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            timeout=API_TIMEOUT_SECONDS,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as exc:
        print(f"Erro na API Anthropic (status {exc.status_code}): {exc.message}")
        sys.exit(1)
    except anthropic.APIConnectionError as exc:
        print(f"Erro de conexão com a API Anthropic: {exc}")
        sys.exit(1)
    except anthropic.APITimeoutError:
        print(
            f"Erro: a requisição à API Anthropic excedeu o tempo limite "
            f"de {API_TIMEOUT_SECONDS} segundos."
        )
        sys.exit(1)
    except anthropic.AuthenticationError:
        print(
            "Erro: chave de API inválida. "
            "Verifique o valor de ANTHROPIC_API_KEY."
        )
        sys.exit(1)
    except Exception as exc:
        print(f"Erro inesperado ao chamar a API Anthropic: {exc}")
        sys.exit(1)

    # Acesso protegido ao conteúdo da resposta
    content = getattr(message, "content", None)
    if not content or not isinstance(content, list) or len(content) == 0:
        print("Erro: a API Anthropic retornou uma resposta vazia ou inesperada.")
        sys.exit(1)

    first_block = content[0]
    summary = getattr(first_block, "text", None)
    if not summary:
        print("Erro: não foi possível extrair o texto do resumo da resposta da API.")
        sys.exit(1)

    return summary.strip()


# ---------------------------------------------------------------------------
# 7. build_output_path
# ---------------------------------------------------------------------------
def build_output_path(pdf_path: str) -> str:
    """
    Deriva e retorna o caminho do arquivo .txt de saída
    com sufixo _resumo na mesma pasta do PDF.
    """
    base, _ = os.path.splitext(pdf_path)
    return base + OUTPUT_SUFFIX + OUTPUT_EXTENSION


# ---------------------------------------------------------------------------
# 8. save_summary
# ---------------------------------------------------------------------------
def save_summary(summary: str, pdf_path: str, output_path: str) -> None:
    """
    Grava o arquivo .txt com cabeçalho (nome do PDF + data/hora)
    e o corpo do resumo. Encerra com sys.exit(1) em caso de falha de escrita.
    """
    pdf_basename = os.path.basename(pdf_path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = (
        f"Arquivo: {pdf_basename}\n"
        f"Gerado em: {timestamp}\n"
        f"{'=' * 60}\n\n"
    )

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(summary)
            f.write("\n")
    except OSError as exc:
        print(f"Erro: não foi possível salvar o resumo em '{output_path}'. Detalhe: {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 9. print_summary
# ---------------------------------------------------------------------------
def print_summary(summary: str, output_path: str) -> None:
    """Imprime o resumo formatado no terminal."""
    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    print(summary)
    print("=" * 60)
    print(f"\nResumo salvo em: {output_path}\n")


# ---------------------------------------------------------------------------
# 10. main
# ---------------------------------------------------------------------------
def main() -> None:
    """Orquestra todas as funções na sequência correta."""
    # 1. Leitura do argumento
    pdf_path = parse_arguments()

    # 2. Validação do arquivo (existência → extensão → tamanho)
    validate_file(pdf_path)

    # 3. Validação da chave de API antes de qualquer processamento pesado
    api_key = validate_api_key()

    # 4. Extração de texto (abre o PDF apenas uma vez)
    raw_text = extract_text(pdf_path)

    # 5. Validação e truncamento do texto
    clean_text = validate_text(raw_text)

    # 6. Chamada à API Anthropic
    summary = call_anthropic_api(clean_text, api_key)

    # 7. Derivação do caminho de saída
    output_path = build_output_path(pdf_path)

    # 8. Persistência do resumo
    save_summary(summary, pdf_path, output_path)

    # 9. Exibição no terminal
    print_summary(summary, output_path)


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
```