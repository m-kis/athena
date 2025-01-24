from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import timedelta
from typing import List, Optional
from src.agents.recommendation_agent import RecommendationAgent

router = APIRouter()

class RecommendationRequest(BaseModel):
    query: str
    time_window_hours: int = 1
    context_type: Optional[str] = None

class ExecuteRequest(BaseModel):
    recommendation_id: str
    command: str
    
@router.post("/recommendations")
async def get_recommendations(request: RecommendationRequest):
    agent = RecommendationAgent()
    results = await agent.analyze(
        request.query,
        timedelta(hours=request.time_window_hours)
    )
    return results
@router.post("/recommendations/execute")
async def execute_recommendation(request: ExecuteRequest):
    # Validate and execute command
    try:
        # Add security validation here
        if request.command.startswith(('rm', 'sudo', 'wget')):
            raise HTTPException(400, "Unsafe command")
            
        # Execute command
        result = {'status': 'success', 'message': 'Command executed'}
        
        return result
    except Exception as e:
        raise HTTPException(500, f"Execution failed: {str(e)}")
    