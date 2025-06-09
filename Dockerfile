FROM python:3.11.8-slim-bookworm
LABEL authors="SCII5"
WORKDIR /app
COPY . .
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root
CMD ["python", "-m", "telegram_app.bot"]