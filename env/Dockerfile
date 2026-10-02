FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml .
COPY learnos_env ./learnos_env
RUN pip install --no-cache-dir -e .
EXPOSE 8000
CMD ["uvicorn", "learnos_env.server:app", "--host", "0.0.0.0", "--port", "8000"]
