from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import router as connections_router

app = FastAPI(title="Open Data Insight Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", summary="Health check")
def health_check() -> dict[str, str]:
    """Simple endpoint to verify the service is running."""
    return {"status": "ok"}


app.include_router(connections_router)
