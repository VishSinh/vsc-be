ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential netcat-traditional gosu && rm -rf /var/lib/apt/lists/*
COPY Pipfile Pipfile.lock ./
RUN pip install --no-cache-dir pipenv && PIPENV_VENV_IN_PROJECT=0 pipenv install --deploy --system
COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN adduser --disabled-password --gecos "" --home "/nonexistent" --shell "/sbin/nologin" --no-create-home --uid 10001 appuser && mkdir -p /app/staticfiles /app/media && chown -R appuser:appuser /app && chmod +x /entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn","vsc_be.wsgi:application","--bind=0.0.0.0:8000"]
