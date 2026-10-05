FROM python:3.12-slim

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv PATH="/app/.venv/bin:${PATH}" \
    RADAR_DIRETORIO_DADOS=/app/data RADAR_CAMINHO_SQL=/app/extractions/sql/autorizacoes_semanais.sql \
    RADAR_DIRETORIO_CSV=/app/extractions/csv

RUN python -m venv ${VIRTUAL_ENV}

COPY requirements.lock ./

RUN pip install --no-cache-dir -r requirements.lock

COPY pyproject.toml ./

COPY src ./src

COPY extractions/sql ./extractions/sql

RUN pip install --no-cache-dir --no-deps .