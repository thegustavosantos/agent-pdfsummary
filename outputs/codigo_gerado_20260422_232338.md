```python
# resumidor.py
#
# Decisões técnicas:
# 1. Uso de `sys.argv` para captura do argumento de linha de comando (sem argparse, mantendo simplicidade)
# 2. PyMuPDF (fitz) para extração de texto — robusto e rápido para PDFs nativos
# 3. Cliente Anthropic instanciado via `anthropic.Anthropic()` — lê ANTHROPIC_API_KEY do ambiente
# 4. Modelo claude-3-5-haiku — bom custo-benefício para tarefas de sumarização
# 5. Truncamento de texto feito antes do envio, respeitando o limite de 10.000 chars
# 6. Arquivo de saída salvo na mesma pasta do PDF, com sufixo `_resumo.txt`
# 7. Uso de `sys.exit(1)` em todos os casos de erro para sinalizar falha ao shell
# 8. Data de execução formatada como ISO 8601 para clareza e ordenação

import sys
import os
from datetime import datetime

import fitz  # PyMuPDF
import anthropic

# ──────────────────────────────────────────────
# Constantes de configuração
# ──────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024   # 20 MB
MAX_PAGES           = 50                  # páginas máximas processadas
MAX_CHARS           = 10_000             # limite de caracteres enviados à API


def validar_argumento() -> str:
    """
    Verifica se o caminho do PDF foi passado como argumento.
    Retorna o caminho informado ou encerra o script com instrução de uso.
    """
    if len(sys.argv) < 2:
        print("Uso: python resumidor.py <caminho_para_o_arquivo.pdf>")
        print("Exemplo: python resumidor.py relatorio.pdf")
        sys.exit(1)

    return sys.argv[1]


def validar_arquivo(caminho: str) -> None:
    """
    Valida existência, extensão e tamanho do arquivo recebido.
    Encerra o script com mensagem clara em caso de falha.
    """
    # Verifica se o arquivo existe
    if not os.path.isfile(caminho):
        print(f"Erro: arquivo '{caminho}' não encontrado.")
        sys.exit(1)

    # Verifica a extensão
    _, extensao = os.path.splitext(caminho)
    if extensao.lower() != ".pdf":
        print(f"Erro: o arquivo '{caminho}' não possui extensão .pdf.")
        sys.exit(1)

    # Verifica o tamanho máximo
    tamanho = os.path.getsize(caminho)
    if tamanho > MAX_FILE_SIZE_BYTES:
        tamanho_mb = tamanho / (1024 * 1024)
        print(f"Erro: o arquivo tem {tamanho_mb:.1f} MB, acima do limite de 20 MB.")
        sys.exit(1)


def extrair_texto(caminho: str) -> str:
    """
    Abre o PDF com PyMuPDF e extrai o texto das primeiras MAX_PAGES páginas.
    Retorna o texto concatenado ou encerra se o PDF não contiver texto extraível.
    """
    try:
        documento = fitz.open(caminho)
    except Exception as e:
        print(f"Erro ao abrir o PDF: {e}")
        sys.exit(1)

    total_paginas = len(documento)
    paginas_a_processar = min(total_paginas, MAX_PAGES)

    if total_paginas > MAX_PAGES:
        print(
            f"Aviso: o PDF possui {total_paginas} páginas; "
            f"apenas as primeiras {MAX_PAGES} serão processadas."
        )

    # Extrai e concatena o texto página a página
    partes = []
    for numero in range(paginas_a_processar):
        pagina = documento[numero]
        texto_pagina = pagina.get_text()          # retorna string (pode ser vazia)
        if texto_pagina.strip():
            partes.append(texto_pagina)

    documento.close()

    texto_completo = "\n".join(partes).strip()

    # PDF escaneado ou sem camada de texto
    if not texto_completo:
        print(
            "Erro: nenhum texto extraível foi encontrado no PDF. "
            "O arquivo pode ser um PDF escaneado sem OCR."
        )
        sys.exit(1)

    return texto_completo


def truncar_texto(texto: str) -> str:
    """
    Trunca o texto ao limite de MAX_CHARS caracteres, informando o usuário
    caso o conteúdo original seja maior.
    """
    if len(texto) > MAX_CHARS:
        print(
            f"Aviso: o texto extraído tem {len(texto):,} caracteres; "
            f"será truncado para os primeiros {MAX_CHARS:,} antes do envio à API."
        )
        return texto[:MAX_CHARS]
    return texto


def chamar_api_anthropic(texto: str) -> str:
    """
    Envia o texto à API da Anthropic e retorna o resumo gerado.
    Encerra o script (sem salvar arquivo) em caso de falha na chamada.
    """
    cliente = anthropic.Anthropic()          # lê ANTHROPIC_API_KEY do ambiente

    prompt = (
        "Você é um assistente especializado em análise e síntese de documentos. "
        "Leia o texto a seguir e produza um resumo claro, objetivo e bem estruturado, "
        "destacando os pontos principais, conclusões e informações mais relevantes. "
        "Escreva em português.\n\n"
        f"TEXTO DO DOCUMENTO:\n{texto}"
    )

    try:
        resposta = cliente.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
    except anthropic.APIConnectionError as e:
        print(f"Erro de conexão com a API da Anthropic: {e}")
        sys.exit(1)
    except anthropic.AuthenticationError as e:
        print(f"Erro de autenticação na API da Anthropic (verifique ANTHROPIC_API_KEY): {e}")
        sys.exit(1)
    except anthropic.RateLimitError as e:
        print(f"Limite de requisições atingido na API da Anthropic: {e}")
        sys.exit(1)
    except anthropic.APIStatusError as e:
        print(f"Erro retornado pela API da Anthropic (status {e.status_code}): {e.message}")
        sys.exit(1)

    # Extrai o conteúdo textual da resposta
    resumo = resposta.content[0].text
    return resumo


def salvar_resumo(caminho_pdf: str, resumo: str) -> str:
    """
    Salva o resumo em um arquivo .txt na mesma pasta do PDF.
    O arquivo inclui nome original, data de execução e o texto do resumo.
    Retorna o caminho do arquivo gerado.
    """
    pasta    = os.path.dirname(os.path.abspath(caminho_pdf))
    nome_pdf = os.path.basename(caminho_pdf)
    nome_base, _ = os.path.splitext(nome_pdf)

    nome_saida  = f"{nome_base}_resumo.txt"
    caminho_txt = os.path.join(pasta, nome_saida)

    data_execucao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conteudo = (
        f"Arquivo original : {nome_pdf}\n"
        f"Data de execução : {data_execucao}\n"
        f"{'─' * 60}\n\n"
        f"{resumo}\n"
    )

    with open(caminho_txt, "w", encoding="utf-8") as arquivo:
        arquivo.write(conteudo)

    return caminho_txt


# ──────────────────────────────────────────────
# Ponto de entrada principal
# ──────────────────────────────────────────────
def main() -> None:
    # 1. Valida argumento de linha de comando
    caminho_pdf = validar_argumento()

    # 2. Valida existência, extensão e tamanho do arquivo
    validar_arquivo(caminho_pdf)

    # 3. Extrai texto do PDF (máx. 50 páginas)
    print(f"Extraindo texto de '{caminho_pdf}'...")
    texto = extrair_texto(caminho_pdf)
    print(f"Texto extraído: {len(texto):,} caracteres.")

    # 4. Trunca o texto se necessário
    texto = truncar_texto(texto)

    # 5. Envia à API da Anthropic e obtém o resumo
    print("Gerando resumo via API da Anthropic...")
    resumo = chamar_api_anthropic(texto)

    # 6. Exibe o resumo no terminal
    print("\n" + "═" * 60)
    print("RESUMO DO DOCUMENTO")
    print("═" * 60)
    print(resumo)
    print("═" * 60 + "\n")

    # 7. Salva o resumo em arquivo .txt
    caminho_saida = salvar_resumo(caminho_pdf, resumo)
    print(f"Resumo salvo em: {caminho_saida}")


if __name__ == "__main__":
    main()


# ──────────────────────────────────────────────
# Exemplos de uso (terminal):
#
#   python resumidor.py relatorio_anual.pdf
#   python resumidor.py /home/user/docs/contrato.pdf
#   python resumidor.py "pasta com espaço/artigo cientifico.pdf"
#
# Pré-requisitos:
#   pip install pymupdf anthropic
#   export ANTHROPIC_API_KEY="sk-ant-..."   # Linux/macOS
#   set ANTHROPIC_API_KEY=sk-ant-...        # Windows CMD
# ──────────────────────────────────────────────
```