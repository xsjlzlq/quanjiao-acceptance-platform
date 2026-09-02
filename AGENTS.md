# AGENTS.md — 全椒县县级验收管理平台

## Stack
- **Backend:** Python 3.13 + FastAPI + Uvicorn, port `8081`
- **Frontend:** Vue 3 + Vant 4 + Vite, port `3000`
- **DB:** PostgreSQL (`quanjiao`), connection in `backend/database.py`
- **Word export:** `win32com.client` via `pythoncom` — requires **Windows + Microsoft Word**

## Running

```bash
# Backend (Windows)
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8081 --reload

# Frontend (any OS)
cd frontend
npm install
npm run dev
```

Default login: `admin` / `admin123`

## Architecture

| File | Role |
|---|---|
| `backend/main.py` | All API routes (~1435 lines), import this when tracing logic |
| `backend/models.py` | SQLAlchemy models; `DkxxShpAttr` only — rest are raw SQL |
| `backend/doc_exporter.py` | Attachments 1–9, 12, 13 Word generation via COM |
| `backend/doc_exporter_score.py` | Attachments 10/11 (score & rating) Word generation |
| `backend/score_service.py` | Township score aggregation, county = `qsdwdm='341124'` |
| `backend/data_importer.py` | MDB/SHP/XLS bulk import; called by `/api/import-data` |
| `backend/auth.py` | JWT auth + RBAC (20+ permission keys) |
| `frontend/src/router/index.js` | 7 page routes; login is `public` (no guard) |

## Word COM Gotchas

- Runs on Windows only. Never test export on Linux/macOS CI.
- Always call `word_app.Quit()` after export; orphaned WINWORD.exe processes will accumulate.
- Templates live in `附件/` — file names like `附件1.doc`, `附件6.doc`. New attachment = new template + new export function in `doc_exporter.py`.
- `pywin32` must be installed: `pip install pywin32` (not in `requirements.txt`; add if Word export is broken).

## Key Conventions

- Township codes: 10 towns — `襄河镇`, `古河镇`, `大墅镇`, `二郎口镇`, `武岗镇`, `马厂镇`, `石沛镇`, `十字镇`, `西王镇`, `六镇镇`. County = `341124`.
- No ORM for most queries — `sqlalchemy.text()` direct SQL is the norm. Don't add models where none exist; use `text()` unless a new table is created.
- Frontend serves `http://localhost:3000`; Vite proxies `/api` → `http://localhost:8081`.
- No linter, no formatter, no typecheck configured. Do not introduce them without asking.
- Test scripts (`test_*.py`, `patch*.py`, `fix*.py`) in root are ad-hoc debugging — ignore, not part of any test runner.
