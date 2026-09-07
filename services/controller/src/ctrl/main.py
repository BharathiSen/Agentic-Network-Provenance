# services/controller/src/ctrl/main.py
from fastapi import FastAPI

app = FastAPI(title="Network Controller")


@app.get("/health")
def health():
    return {"status": "ok", "service": "controller"}