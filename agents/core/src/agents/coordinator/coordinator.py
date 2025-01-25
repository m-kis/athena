# agents/core/src/agents/coordinator/coordinator.py
from src.agents.base.base_agent import BaseAgent

class AgentCoordinator(BaseAgent):
    async def coordinate_analysis(self, query: str, time_window, agent_types=None):
        response = await self.analyze(query, time_window)
        return {"status": "success", "results": response}
