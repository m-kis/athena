# agents/core/src/agents/base/base_agent.py
from datetime import timedelta
from typing import Dict, List, Optional
from src.models.llm import LLMWrapper

class BaseAgent:
    def __init__(self):
        self.llm = LLMWrapper()

    async def analyze(
        self,
        query: str,
        time_window: timedelta,
        context: Optional[List[Dict]] = None
    ) -> Dict:
        return await self._analyze_impl(query, context, time_window)

    async def _analyze_impl(self, query: str, context: List[Dict], time_window: timedelta) -> Dict:
        raise NotImplementedError
