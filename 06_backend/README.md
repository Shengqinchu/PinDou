# PinDou Backend

Phase 2 FastAPI backend scaffold.

## Local Run

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn pindou.main:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```
