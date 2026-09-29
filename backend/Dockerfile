FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.lock backend/pyproject.toml ./backend/
RUN pip install --no-cache-dir -r backend/requirements.lock
COPY backend ./backend
COPY configs ./configs
RUN pip install --no-cache-dir -e "backend"
WORKDIR /app/backend
CMD ["uvicorn", "taqpso.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
