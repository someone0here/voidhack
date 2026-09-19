from fastapi import FastAPI

app = FastAPI(
    title="Cyber Fraud Correlator API",
    description="Multi-source cyber fraud artifact correlation and risk scoring engine",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Health check endpoint confirming API service status."""
    return {"status": "ok", "phase": "Phase 1 - Scaffolding"}
