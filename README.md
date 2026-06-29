# KnowledgeHub AI RAG System

A full-stack Retrieval-Augmented Generation (RAG) web application.

## Project structure
- **backend/**: FastAPI + Celery app, database models (SQLAlchemy) and Alembic migrations.
- **frontend/**: React + Vite UI.
- **docker-compose.yml**: Local multi-service setup.

## Setup (local development)

### 1) Backend
1. Create a virtual environment (recommended).
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Copy environment variables:
   - `backend/.env.example` -> `backend/.env`
4. Run the backend (example):
   ```bash
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### 2) Frontend
1. Install dependencies:
   ```bash
   cd frontend
   npm ci
   ```
2. Start dev server:
   ```bash
   npm run dev
   ```

### 3) Database migrations
If using Alembic migrations:
```bash
alembic upgrade head
```

## Notes
- `backend/.env` and `backend/uploads/` are excluded from GitHub via `.gitignore`.
- To run the full system (including workers/DB) use `docker-compose.yml`.

