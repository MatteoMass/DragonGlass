# Two stages, the same two steps: node builds the frontend, python serves it,
# and nothing of node survives into the image that ships.

FROM node:22-alpine AS frontend
WORKDIR /build
COPY src/frontend/package.json src/frontend/package-lock.json* ./
RUN npm ci || npm install
COPY src/frontend/ ./
RUN npm run build


FROM python:3.14-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DRAGONGLASS_HOLLOW_ROOT=/app/data/root \
    DRAGONGLASS_FRONTEND_DIST=/app/src/frontend/dist \
    DRAGONGLASS_HOST=0.0.0.0 \
    DRAGONGLASS_PORT=8017

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
        "fastapi>=0.141,<1.0" \
        "uvicorn[standard]>=0.52,<1.0" \
        "markdown>=3.10,<4.0" \
        "pyyaml>=6.0,<7.0" \
        "python-multipart>=0.0.32,<0.1"

COPY src/ ./src/
COPY dragonglass.yml ./dragonglass.yml
COPY --from=frontend /build/dist ./src/frontend/dist

RUN mkdir -p /app/data/root

EXPOSE 8017
CMD ["uvicorn", "backend:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8017"]
