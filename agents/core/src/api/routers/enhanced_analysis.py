from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
try:
    from src.agents.enhanced_coordinator import EnhancedCoordinator
except ModuleNotFoundError as e:
    raise ImportError("Required dependencies not installed. Please run 'pip install torch plotly'") from e

router = APIRouter()

class EnhancedAnalysisRequest(BaseModel):
    query: str
    time_window_hours: int = 1
    analysis_types: Optional[List[str]] = None
    context_type: Optional[str] = None

@router.post("/analyze/enhanced")
async def enhanced_analysis(request: EnhancedAnalysisRequest):
    try:
        coordinator = EnhancedCoordinator()
        results = await coordinator.process_query(
            query=request.query,
            time_window=timedelta(hours=request.time_window_hours),
            agent_types=request.analysis_types
        )
        
        return {
            "query": request.query,
            "timestamp": datetime.now().isoformat(),
            "analysis": results,
            "metadata": {
                "processed_by": "enhanced_coordinator",
                "version": "2.0"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@router.get("/intents")
async def list_intents():
    """Liste tous les types d'intentions supportés"""
    coordinator = EnhancedCoordinator()
    return {
        "intents": coordinator.nlu.get_intent_labels(),
        "timestamp": datetime.now().isoformat()
    }