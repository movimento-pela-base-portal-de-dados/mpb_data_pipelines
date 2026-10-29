# Imagem de execução dos flow runs: Prefect oficial com o pacote do repositório.
# O worker Docker do orquestrador a baixa do ECR.
FROM prefecthq/prefect:3.8.8-python3.11

WORKDIR /opt/prefect/mpb-data-pipelines

COPY pyproject.toml prefect.yaml ./
COPY src ./src
RUN pip install --no-cache-dir .
