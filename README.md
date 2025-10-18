SmartBot — Deployment Guide (Render)

Backend (Web Service):
- Root: backend/
- Build: pip install -r requirements.txt
- Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
- Env:
  - DATABASE_URL, DATABASE_URL_SYNC
  - REDIS_URL
  - SECRET_KEY
  - ALLOWED_ORIGINS (e.g. https://your-frontend.onrender.com)
  - OPENAI_API_KEY, OPENAI_MODEL

Frontend (Static Site):
- Root: frontend/
- Build: npm ci && npm run build
- Publish dir: dist
- Env:
  - VITE_API_BASE=https://your-backend.onrender.com


