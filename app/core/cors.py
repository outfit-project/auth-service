import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DEFAULT_ORIGINS = (
    "http://192.168.0.213,http://localhost:5173,http://localhost:3000"
)


def setup_cors(app: FastAPI, origins: str | None = None) -> None:
    raw = origins or os.getenv("CORS_ORIGINS", DEFAULT_ORIGINS)
    allow_origins = [o.strip() for o in raw.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
