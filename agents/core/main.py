from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from prometheus_client import make_asgi_app
from contextlib import asynccontextmanager
import uvicorn
import logging

from src.api.routers import analysis, history, recommendations, enhanced_analysis, metrics
from src.monitoring.metrics import MetricsMiddleware, metrics_manager
from src.models.database import Base
from src.config.database import engine
from src.middleware.rate_limit import RateLimitMiddleware
from src.middleware.cache import cache
from src.error_handling.handlers import ServiceError, ErrorHandler

app = FastAPI(title="Athena Core API")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)