from langchain_ollama import OllamaLLM
from langchain.callbacks.manager import CallbackManager
import asyncio
from datetime import datetime
import logging
import json
from src.config.settings import settings
from src.monitoring.metrics import metrics_manager

logger = logging.getLogger(__name__)

class LLMWrapper:
    def __init__(self, max_retries: int = 3, timeout: float = 90.0):
        self.max_retries = max_retries 
        self.timeout = timeout
        self.model_name = settings.MODEL_NAME
        self._attempts = 0
        self._setup_llm()

    def _setup_llm(self):
        try:
            self.llm = OllamaLLM(
                model=self.model_name,
                base_url=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}",
                temperature=0.7,
                callback_manager=CallbackManager([]),  # Désactive les callbacks par défaut
                stop=["\n\n"],  # Arrêter la génération aux doubles sauts de ligne
                num_ctx=4096  # Augmente le contexte disponible
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise

    async def analyze_with_fallback(self, content: str, base_prompt: str) -> str:
        try:
            with metrics_manager.track_llm_request(self.model_name, "analyze"):
                response = await self._analyze_with_timeout(
                    f"{base_prompt}\n\nContext:\n{content}",
                    timeout=90
                )
                return response
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return await self._fallback_analysis(content)

    async def analyze_loki_logs(self, query_result: dict, query: str, base_prompt: str) -> str:
        try:
            context = self._prepare_log_context(query_result)
            full_prompt = self._build_analysis_prompt(base_prompt, query, context)
            
            with metrics_manager.track_llm_request(self.model_name, "analyze_logs"):
                response = await self._analyze_with_timeout(full_prompt)
                return response
        except Exception as e:
            logger.error(f"Error analyzing logs: {e}")
            return await self._handle_analysis_error(e)

    async def _analyze_with_timeout(self, prompt: str, timeout: int = 90) -> str:
        self._attempts += 1
        
        try:
            result = await asyncio.wait_for(
                self.llm.agenerate([prompt]),
                timeout=timeout
            )
            return result.generations[0][0].text
        except asyncio.TimeoutError:
            logger.warning(f"Attempt {self._attempts} timed out")
            if self._attempts >= self.max_retries:
                return "Analysis timed out after multiple attempts."
            return await self._analyze_with_timeout(prompt, timeout * 2)
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            if self._attempts >= self.max_retries:
                return "Analysis failed. Please try again later."
            return await self._analyze_with_timeout(prompt, timeout)

    async def _fallback_analysis(self, content: str) -> str:
        try:
            fallback_prompt = "Provide a brief summary of the key issues and metrics."
            with metrics_manager.track_llm_request(self.model_name, "fallback"):
                response = await self._analyze_with_timeout(
                    f"{fallback_prompt}\n\nContent:\n{content}",
                    timeout=30
                )
                return response
        except Exception as e:
            logger.error(f"Fallback analysis failed: {e}")
            return "Analysis unavailable. Please try again later."

    def _prepare_log_context(self, query_result: dict) -> str:
        try:
            logs = query_result.get('logs', [])
            if not logs and 'data' in query_result:
                logs = query_result['data'].get('result', [])

            max_logs = 50
            logs = logs[:max_logs]

            formatted_logs = [
                f"[{log.get('timestamp', '')}] {log.get('message', '')} (labels: {json.dumps(log.get('labels', {}))})"
                for log in logs if isinstance(log, dict)
            ]

            return "\n".join(formatted_logs)
        except Exception as e:
            logger.error(f"Error preparing log context: {e}")
            return str(query_result)

    def _build_analysis_prompt(self, base_prompt: str, query: str, context: str) -> str:
        return f"""{base_prompt}
Query: {query}

Log Context:
{context}

Provide a detailed analysis focusing on:
1. Key patterns and issues
2. Impact assessment
3. Specific recommendations
4. Priority actions"""

    async def _handle_analysis_error(self, error: Exception) -> str:
        error_str = str(error).lower()
        if "model not found" in error_str:
            return "Error: Required model not available. Please ensure the model is installed."
        elif "context length" in error_str:
            return "Error: Input too long. Please reduce the time window or number of logs."
        return f"Analysis error: {str(error)}. Please try again or contact support."