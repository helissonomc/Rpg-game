FROM python:3.12-slim

WORKDIR /project
RUN pip install --no-cache-dir poetry

COPY game/pyproject.toml game/poetry.lock* /project/
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

COPY . .

