from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(title="Scientific Spaces AI Learning OS")
app.include_router(health_router)
