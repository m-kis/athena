from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from src.agents.coordinator import AgentCoordinator
from src.config.database import get_session
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class AnalysisRequest(BaseModel):
    query: str
    time_window_hours: int = 1
    analysis_types: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

# src/api/routers/analysis.py
@router.post("/analyze") 
async def analyze_logs(request: AnalysisRequest):
    if not request.query:
        raise HTTPException(400, "Query cannot be empty")
        
    coordinator = AgentCoordinator()
    try:
        results = await coordinator.coordinate_analysis(
            query=request.query,
            time_window=timedelta(hours=request.time_window_hours),
            agent_types=request.analysis_types
        )
        return {
            "status": "success", 
            "results": results
        }
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(500, f"Analysis failed: {str(e)}")

@router.post("/analyze/combined")
async def analyze_combined(request: AnalysisRequest):
    try:
        coordinator = AgentCoordinator()
        time_window = timedelta(hours=request.time_window_hours)
        
        # Use all agent types if none specified
        if not request.analysis_types:
            request.analysis_types = ["logs", "security", "performance"]
            
        results = await coordinator.coordinate_analysis(
            query=request.query,
            time_window=time_window,
            agent_types=request.analysis_types
        )
        
        return {
            "query": request.query,
            "time_window": f"{request.time_window_hours}h",
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Combined analysis failed: {str(e)}"
        )