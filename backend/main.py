"""FastAPI application entry point."""

from fastapi import FastAPI

from backend.routes.health import router as health_router
from backend.routes.jobs import router as jobs_router

app = FastAPI(title="DepthWizard API")
app.include_router(health_router)
app.include_router(jobs_router)
