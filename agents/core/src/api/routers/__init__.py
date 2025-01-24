from .analysis import router as analysis_router
from .enhanced_analysis import router as enhanced_analysis_router
from .history import router as history_router
from .recommendations import router as recommendations_router
from .metrics import router as metrics_router

__all__ = [
    'analysis_router',
    'enhanced_analysis_router',
    'history_router',
    'recommendations_router',
    'metrics_router'
]