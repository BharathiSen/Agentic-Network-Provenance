# services/provenance-store/src/pstore/main.py
from fastapi import FastAPI

app = FastAPI(title="Provenance Store")


@app.get("/health")
def health():
    return {"status": "ok", "service": "provenance-store"}