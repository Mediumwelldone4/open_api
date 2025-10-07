from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import router as connections_router
from .settings import get_settings

settings = get_settings()

app = FastAPI(title="Open Data Insight Platform API")

cors_origins = settings.allowed_origins or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", summary="Health check")
def health_check() -> dict[str, str]:
    """Simple endpoint to verify the service is running."""
    return {"status": "ok"}


app.include_router(connections_router)
