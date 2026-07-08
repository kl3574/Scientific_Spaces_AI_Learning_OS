from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.articles import router as articles_router
from app.api.health import router as health_router
from app.api.learning import router as learning_router
from app.api.rag import router as rag_router

app = FastAPI(title="Scientific Spaces AI Learning OS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(articles_router)
app.include_router(rag_router)
app.include_router(learning_router)
