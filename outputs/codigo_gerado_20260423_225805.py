```python
#!/usr/bin/env python3
"""
resumidor.py — Script CLI para resumir PDFs usando a API da Anthropic.

Uso:
    python resumidor.py arquivo.pdf

Requer:
    - PyMuPDF (fitz): pip install pymupdf
    - anthropic: pip install anthropic
    - Variável de ambiente ANTHROPIC_API_KEY definida
"""

import os
import sys
from pathlib import Path

import fitz  # PyMuPDF
import anthropic

# ---------------------------------------------------------------------------
# CONSTANTES E CONFIGURAÇÕES
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_MB    = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # 20_971_520 bytes
MAX_PAGES           = 50
MAX_CHARS           = 80_000
ANTHROPIC_MODEL     = "claude-3-5-sonnet-20241022"
OUTPUT_SUFFIX       = "_resumo.txt"
SEPARATOR           = "---"
API_KEY_ENV_VAR     = "ANTHROPIC_API_KEY"


# ---------------------------------------------------------------------------
# 1. PARSE ARGUMENTS
# ---------------------------------------------------------------------------

def parse_arguments() -> str:
    """
    Lê sys.argv e valida a presença do argumento obrigatório.

    Retorna o caminho do PDF informado como string.
    Encerra com exit code 1 se o argumento estiver ausente.
    """
    # O plano técnico especifica verificação manual via sys.argv (não argparse)
    if len(sys.argv) < 2:
        print("Uso: python resumidor.py arquivo.pdf")
        sys.exit(1)

    # Retorna o primeiro argumento posicional após o nome do script
    return sys.argv[1]


# ---------------------------------------------------------------------------
# 2. VALIDATE PDF FILE
# ---------------------------------------------------------------------------

def validate_pdf_file(pdf_path: str) -> Path:
    """
    Valida o arquivo informado antes de qualquer processamento.

    Verificações realizadas (na ordem):
      1. O arquivo existe no sistema de arquivos
      2. A extensão é .pdf (case-insensitive)
      3. O tamanho não ultrapassa MAX_FILE_SIZE_BYTES (20 MB)

    Retorna um objeto Path validado.
    Encerra com exit code 1 em qualquer falha de validação.
    """
    path = Path(pdf_path)

    # --- Verificação 1: existência do arquivo ---
    if not path.exists():
        print(f"Erro: arquivo não encontrado: {path}")
        sys.exit(1)

    # --- Verificação 2: extensão .pdf ---
    if path.suffix.lower() != ".pdf":
        print(f"Erro: o arquivo informado não é um PDF: {path}")
        sys.exit(1)

    # --- Verificação 3: tamanho máximo ---
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        print(f"Erro: arquivo excede o limite de {MAX_FILE_SIZE_MB} MB")
        sys.exit(1)

    return path


# ---------------------------------------------------------------------------
# 3. EXTRACT TEXT
# ---------------------------------------------------------------------------

def extract_text(pdf_path: Path) -> str:
    """
    Abre o PDF com PyMuPDF e extrai o texto bruto de até MAX_PAGES páginas.

    O texto de cada página é concatenado com uma quebra de linha dupla
    para preservar a separação visual entre páginas.

    Retorna a string com o texto completo extraído.
    Encerra com exit code 1 se o PDF estiver corrompido ou sem texto.
    """
    try:
        # Abre o documento PDF
        doc = fitz.open(str(pdf_path))
    except fitz.FileDataError as exc:
        # PDF corrompido ou com estrutura inválida reconhecida pelo PyMuPDF
        print("Erro: o arquivo não é um PDF válido ou está corrompido")
        sys.exit(1)
    except Exception as exc:
        # Qualquer outra exceção lançada pelo PyMuPDF ao abrir o arquivo
        print("Erro: o arquivo não é um PDF válido ou está corrompido")
        sys.exit(1)

    # Limita o número de páginas processadas
    total_pages = min(len(doc), MAX_PAGES)

    # Extrai e concatena o texto de cada página
    pages_text = []
    for page_index in range(total_pages):
        page = doc[page_index]
        page_text = page.get_text()  # extrai texto selecionável da página
        pages_text.append(page_text)

    # Fecha o documento para liberar recursos
    doc.close()

    # Junta todas as páginas com separação dupla
    full_text = "\n\n".join(pages_text)

    # --- Verificação: texto vazio após extração ---
    if not full_text.strip():
        print("Aviso: o PDF não contém texto selecionável (pode ser imagem)")
        sys.exit(1)

    return full_text


# ---------------------------------------------------------------------------
# 4. TRUNCATE TEXT
# ---------------------------------------------------------------------------

def truncate_text(text: str, max_chars: int) -> str:
    """
    Trunca o texto no limite de caracteres definido.

    Se o texto for menor ou igual ao limite, retorna sem alteração.
    Caso contrário, retorna os primeiros max_chars caracteres.

    Retorna a string resultante (possivelmente truncada).
    """
    if len(text) <= max_chars:
        return text

    # Trunca e informa ao usuário que o texto foi cortado
    print(
        f"Aviso: o texto extraído foi truncado de {len(text):,} "
        f"para {max_chars:,} caracteres antes de enviar à API."
    )
    return text[:max_chars]


# ---------------------------------------------------------------------------
# 5. BUILD PROMPT
# ---------------------------------------------------------------------------

def build_prompt(text: str) -> str:
    """
    Monta a instrução completa a ser enviada à API da Anthropic.

    O prompt solicita um resumo em português, em texto simples,
    sem formatação markdown.

    Retorna a string do prompt completo.
    """
    prompt = (
        "Você é um assistente especializado em resumir documentos em português.\n\n"
        "Leia o texto abaixo, extraído de um arquivo PDF, e produza um resumo completo "
        "em português brasileiro.\n\n"
        "Regras obrigatórias para o resumo:\n"
        "- Escreva em texto simples, sem formatação markdown\n"
        "- Não use asteriscos, cerquilhas, backticks nem hífens de lista\n"
        "- Não use bullets nem numeração de itens\n"
        "- Escreva em parágrafos corridos, separados por quebra de linha\n"
        "- Cubra os pontos principais do documento de forma objetiva\n"
        "- O resumo deve ser claro e compreensível por si só\n\n"
        "Texto do PDF:\n"
        "==========\n"
        f"{text}\n"
        "==========\n\n"
        "Escreva o resumo agora, em português, sem introduções como "
        "'Aqui está o resumo' ou 'O documento trata de':"
    )
    return prompt


# ---------------------------------------------------------------------------
# 6. CALL ANTHROPIC API
# ---------------------------------------------------------------------------

def call_anthropic_api(prompt: str) -> str:
    """
    Envia o prompt à API da Anthropic e retorna o texto do resumo gerado.

    Lê a chave de API da variável de ambiente ANTHROPIC_API_KEY.
    Usa o modelo definido em ANTHROPIC_MODEL.

    Retorna a string com o resumo gerado pela API.
    Encerra com exit code 1 em caso de chave ausente ou falha na API.
    """
    # --- Verificação: chave de API presente ---
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if not api_key:
        print(f"Erro: variável de ambiente {API_KEY_ENV_VAR} não definida")
        sys.exit(1)

    # Instancia o cliente da Anthropic com a chave lida do ambiente
    client = anthropic.Anthropic(api_key=api_key)

    try:
        # Realiza a chamada à API usando a interface de mensagens
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
    except anthropic.APIError as exc:
        # Captura erros específicos da API da Anthropic (autenticação, rate limit, etc.)
        print(f"Erro na API Anthropic: {exc}")
        sys.exit(1)
    except Exception as exc:
        # Captura qualquer outra falha inesperada durante a chamada
        print(f"Erro na API Anthropic: {exc}")
        sys.exit(1)

    # Extrai somente o texto da resposta (primeiro bloco de conteúdo)
    summary = message.content[0].text
    return summary


# ---------------------------------------------------------------------------
# 7. PRINT SUMMARY
# ---------------------------------------------------------------------------

def print_summary(summary: str) -> None:
    """
    Imprime o resumo no terminal com separadores visuais definidos.

    Formato:
        ---
        {texto do resumo}
        ---
    """
    print(SEPARATOR)
    print(summary)
    print(SEPARATOR)


# ---------------------------------------------------------------------------
# 8. SAVE SUMMARY
# ---------------------------------------------------------------------------

def save_summary(summary: str, pdf_path: Path) -> Path:
    """
    Salva o resumo em um arquivo .txt no mesmo diretório do PDF.

    O nome do arquivo de saída é derivado do PDF:
        {nome_original}_resumo.txt
    Exemplo: relatorio.pdf → relatorio_resumo.txt

    Retorna o Path do arquivo salvo.
    Encerra com exit code 1 se não for possível gravar o arquivo.
    """
    # Deriva o nome do arquivo de saída removendo a extensão original
    output_filename = pdf_path.stem + OUTPUT_SUFFIX

    # Coloca o arquivo de saída no mesmo diretório do PDF
    output_path = pdf_path.parent / output_filename

    try:
        # Grava o resumo em UTF-8, sem nenhum caractere de formatação extra
        output_path.write_text(summary, encoding="utf-8")
    except (IOError, OSError) as exc:
        print(f"Erro ao salvar arquivo: {exc}")
        sys.exit(1)

    return output_path


# ---------------------------------------------------------------------------
# 9. MAIN — ORQUESTRAÇÃO
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Orquestra todas as etapas do pipeline de resumo:

      1. Lê o argumento da linha de comando
      2. Valida o arquivo PDF
      3. Extrai o texto bruto
      4. Trunca o texto se necessário
      5. Monta o prompt
      6. Chama a API da Anthropic
      7. Imprime o resumo no terminal
      8. Salva o resumo em arquivo .txt
      9. Confirma o caminho do arquivo salvo
    """
    # --- Etapa 1: leitura do argumento ---
    pdf_path_str = parse_arguments()

    # --- Etapa 2: validação do arquivo ---
    pdf_path = validate_pdf_file(pdf_path_str)

    # --- Etapa 3: extração do texto bruto ---
    raw_text = extract_text(pdf_path)

    # --- Etapa 4: truncamento do texto ---
    truncated_text = truncate_text(raw_text, MAX_CHARS)

    # --- Etapa 5: montagem do prompt ---
    prompt = build_prompt(truncated_text)

    # --- Etapa 6: chamada à API da Anthropic ---
    summary = call_anthropic_api(prompt)

    # --- Etapa 7: exibição do resumo no terminal ---
    print_summary(summary)

    # --- Etapa 8: gravação do arquivo de saída ---
    saved_path = save_summary(summary, pdf_path)

    # --- Etapa 9: confirmação ao usuário ---
    print(f"Resumo salvo em: {saved_path.resolve()}")


# ---------------------------------------------------------------------------
# PONTO DE ENTRADA
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
```