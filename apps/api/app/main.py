from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Kenya Data Rights API",
    version="0.1.0-alpha.1",
    description="Local-first personal-data rights and regulatory intelligence API for Kenya.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Kenya Data Rights", "status": "alpha", "docs": "/docs"}
