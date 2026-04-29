# CAT Exam App

Simple local CAT exam-taking app with a FastAPI backend and React frontend.

## Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.
