from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import timedelta

class BaseRetriever(ABC):
    """Abstract base class for context retrievers"""
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        time_window: Optional[timedelta] = None,
        k: int = 5,
        min_relevance: float = 0.7,
        **kwargs
    ) -> List[Dict]:
        """
        Retrieve relevant context based on query
        
        Args:
            query: Search query
            time_window: Optional time window to limit search
            k: Number of results to return
            min_relevance: Minimum relevance score threshold
            **kwargs: Additional retriever-specific parameters
            
        Returns:
            List of context items with metadata and relevance scores
        """
        pass
    
    @abstractmethod    
    async def get_metadata(self) -> Dict:
        """Get retriever metadata like index stats"""
        pass
        
    @abstractmethod
    async def refresh(self) -> None:
        """Refresh/reload the retriever's data"""
        pass