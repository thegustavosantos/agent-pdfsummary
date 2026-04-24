import anthropic
from config import MODELO_AGENTES

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Você é um Product Owner com escopo MUITO limitado.
Você define requisitos APENAS para scripts Python simples de linha de comando (CLI).

PROIBIDO mencionar qualquer um destes itens — se aparecer no output, você falhou:
- React, Next.js, Vue, Angular ou qualquer frontend
- FastAPI, Flask, Django ou qualquer servidor web
- AWS, S3, GCP, Azure ou qualquer serviço de nuvem
- Redis, Celery, filas ou processamento assíncrono
- Docker, containers ou infraestrutura
- Banco de dados de qualquer tipo
- Autenticação ou login
- Interface gráfica ou browser

O produto é SEMPRE: um único arquivo .py rodado no terminal. Nada mais."""

def executar(ideia: str) -> str:
    """Recebe uma ideia de produto e retorna os requisitos estruturados."""

    prompt = f"""A ideia do produto é: "{ideia}"

ATENÇÃO: o produto é um script Python CLI simples. Um único arquivo .py.
Exemplo de uso: python resumidor.py relatorio.pdf

Bibliotecas disponíveis: apenas PyMuPDF (fitz) e anthropic. Nada mais.

Escreva SOMENTE:
1. Até 5 requisitos funcionais (o que o script faz no terminal)
2. Limites técnicos (tamanho máximo do arquivo, número de páginas)
3. Como tratar erros (arquivo inválido, texto vazio, falha na API)
4. Formato da saída (imprime no terminal, salva em .txt, etc)

Cada item em uma linha curta. Sem subtópicos. Sem stack tecnológica. Sem arquitetura."""

    resposta = client.messages.create(
        model=MODELO_AGENTES,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return resposta.content[0].text.strip()
