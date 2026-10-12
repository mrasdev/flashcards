from fastapi import FastAPI

app = FastAPI(title="Lernkartei")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
