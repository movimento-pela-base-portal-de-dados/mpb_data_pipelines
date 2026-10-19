"""Flow mínimo usado pelas verificações antes e depois do deploy.

Uma execução concluída prova que o worker baixa a imagem, que o container
alcança a API e que o work pool está ativo.
"""

from prefect import flow


@flow(name="healthcheck")
def healthcheck() -> str:
    return "ok"
