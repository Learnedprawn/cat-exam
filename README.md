# CAT Exam App

CAT exam-taking app with a FastAPI backend and React frontend.

## Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.

Set `CORS_ORIGINS` if you want to allow non-local frontend origins:

```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:3000 .venv/bin/uvicorn app.main:app --reload
```

## Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend runs on `http://localhost:5173`.

Set `VITE_API_BASE_URL` in `frontend/.env` when the backend is not running on `http://localhost:8000/api`.

## Deploy

### Backend on Render

The repo includes [render.yaml](/home/learnedprawn/Work/Ideas/cat-exam/render.yaml) for a web service rooted at `backend/`.
The backend is pinned to Python `3.11.9` to avoid `pydantic-core` falling back to a source build on unsupported newer runtimes.

Required settings:

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Root Directory: backend
```

If an existing Render service is still building with Python `3.14`, it is not using the repo pin yet. Re-sync the Blueprint or set the service environment variable `PYTHON_VERSION=3.11.9`, then trigger a fresh deploy.

Required environment variables:

```text
CORS_ORIGINS=https://your-frontend-domain.vercel.app
```

After deployment, verify:

```text
https://<your-render-service>.onrender.com/api/health
```

### Frontend on Vercel

The frontend includes [vercel.json](/home/learnedprawn/Work/Ideas/cat-exam/frontend/vercel.json:1) for a Vite build once the Vercel project root is set to `frontend`.

Required environment variables:

```text
VITE_API_BASE_URL=https://<your-render-service>.onrender.com/api
```

Recommended project settings:

```text
Framework Preset: Vite
Root Directory: frontend
```

### Deploy order

1. Deploy the backend to Render.
2. Copy the Render backend URL.
3. Set `VITE_API_BASE_URL` in Vercel using that URL with `/api`.
4. Set `CORS_ORIGINS` in Render to your Vercel frontend domain.
5. Redeploy both if needed, then confirm the app loads papers and can submit answers.
