# ---------- 1. збірка веб-клієнта (Vue 3 + Vite) ----------
FROM node:20-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# ---------- 2. сервер FastAPI, який роздає і API, і зібраний SPA ----------
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    CLOUDFOLDER_DATA=/app/data
WORKDIR /app
COPY pyproject.toml ./
# лише серверні залежності з pyproject.toml, без десктоп-клієнта (PySide6) і тестів
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" \
        > /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt
COPY cloudfolder/__init__.py cloudfolder/__init__.py
COPY cloudfolder/core cloudfolder/core
COPY cloudfolder/server cloudfolder/server
COPY --from=web /web/dist web/dist
EXPOSE 8000
# Render передає порт у змінній PORT
CMD ["sh", "-c", "python -m cloudfolder.server --host 0.0.0.0 --port ${PORT:-8000}"]
