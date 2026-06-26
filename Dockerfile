FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

ENV DB_PATH=/app/data/bot.db
VOLUME /app/data

CMD ["python", "src/local.py"]
