# Worker Docker com acesso ao ECR pela role da instância EC2.
FROM prefecthq/prefect:3.8.8-python3.11

RUN apt-get update \
    && apt-get install -y --no-install-recommends amazon-ecr-credential-helper \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir prefect-docker==0.7.4

COPY docker-config.json /root/.docker/config.json
