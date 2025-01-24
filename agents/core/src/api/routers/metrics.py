from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from src.agents.metrics.metrics_agent import MetricAgent

import logging
logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic Models
class MetricAnalysisRequest(BaseModel):
    query: str
    time_window_hours: int = 1
    metrics: Optional[List[str]] = None

class MetricTrainingRequest(BaseModel):
    metric_name: str
    training_data: List[dict]

class PredictionRequest(BaseModel):
    hours_ahead: int = 24
    include_components: bool = True

class MetricResponse(BaseModel):
    summary: str
    current_status: Dict[str, Any]
    key_findings: List[str]
    action_items: List[Dict[str, Any]]
    context: Dict[str, Any]

# Endpoints
@router.post("/metrics/analyze", response_model=MetricResponse)
async def analyze_metrics(request: MetricAnalysisRequest):
    """Analyze system metrics based on query with detailed insights"""
    logger.info(f"Received metric analysis request: {request}")
    try:
        agent = MetricAgent()
        results = await agent.analyze(
            query=request.query,
            time_window=timedelta(hours=request.time_window_hours)
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "analysis": results
        }
    except Exception as e:
        logger.error(f"Error in metric analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/system")
async def get_system_metrics():
    """Get current system metrics snapshot"""
    try:
        agent = MetricAgent()
        metrics = await agent.metrics_collector.get_performance_metrics()
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system metrics: {str(e)}"
        )

@router.get("/metrics/available")
async def get_available_metrics():
    """Get list of available metrics with metadata"""
    try:
        agent = MetricAgent()
        metrics = await agent.get_available_metrics()
        return {
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting available metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve available metrics: {str(e)}"
        )

@router.get("/metrics/{metric_name}")
async def get_metric_info(metric_name: str):
    """Get detailed information about a specific metric"""
    try:
        agent = MetricAgent()
        info = await agent.trainer.model_registry.get_model_info(metric_name)
        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"Metric {metric_name} not found"
            )
        return info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metric info: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving metric info: {str(e)}"
        )

@router.post("/metrics/{metric_name}/predict")
async def predict_metric(
    metric_name: str,
    request: PredictionRequest
):
    """Generate predictions for a specific metric"""
    try:
        agent = MetricAgent()
        model = await agent.trainer.model_registry.load_model(metric_name)
        if not model:
            raise HTTPException(
                status_code=404,
                detail=f"No model found for metric {metric_name}"
            )
        
        predictions = model.predict(
            periods=request.hours_ahead,
            return_components=request.include_components
        )
        
        return {
            "metric": metric_name,
            "predictions": predictions,
            "generated_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating predictions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating predictions: {str(e)}"
        )

@router.post("/metrics/train")
async def train_metric_model(request: MetricTrainingRequest):
    """Train or update a metric model with new data"""
    try:
        agent = MetricAgent()
        results = await agent.trainer.train_models(
            training_data=request.training_data,
            metrics=[request.metric_name]
        )
        
        return {
            "status": "success",
            "training_results": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error training model: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Model training failed: {str(e)}"
        )

@router.delete("/metrics/{metric_name}")
async def delete_metric_model(metric_name: str):
    """Delete a metric model and its associated data"""
    try:
        agent = MetricAgent()
        success = await agent.trainer.model_registry.delete_model(metric_name)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Model {metric_name} not found"
            )
        return {
            "status": "success",
            "message": f"Model {metric_name} deleted successfully",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting model: {str(e)}"
        )