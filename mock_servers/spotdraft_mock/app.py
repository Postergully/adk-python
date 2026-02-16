"""Spotdraft mock server — FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import contracts, documents, onboarding, parties

app = FastAPI(
    title="Spotdraft Mock API",
    version="0.1.0",
    description="Mock implementation of the Spotdraft API for P2P ShareChat agent development.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check (no auth required).
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "spotdraft-mock"}


# Auth verification endpoint referenced in agent_plan.
@app.post("/auth/verify")
async def auth_verify() -> dict:
    return {"valid": True}


app.include_router(parties.router)
app.include_router(contracts.router)
app.include_router(documents.router)
app.include_router(onboarding.router)
