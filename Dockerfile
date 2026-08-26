FROM python:3.14-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

COPY app ./app
COPY config.yaml ./config.yaml

# Deve corrispondere a storage.docker.root in config.yaml
VOLUME ["/app/data/root"]

EXPOSE 8123

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8123"]
