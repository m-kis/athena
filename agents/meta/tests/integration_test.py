import asyncio
import pytest
from datetime import datetime, timedelta
from src.embeddings.loki_client import LokiClient
from src.rag.processors.result_processor import EnhancedRAGProcessor
from src.agents.log_analysis.agent import LogAnalysisAgent
from src.agents.security.agent import SecurityAgent
from src.models.llm import LLMWrapper

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test the entire analysis pipeline"""
        # Initialize components
        loki_client = LokiClient()
        rag_processor = EnhancedRAGProcessor()
        log_agent = LogAnalysisAgent()
        security_agent = SecurityAgent()
        llm = LLMWrapper()
        
        # Test 1: Loki Connection
        print("\nTesting Loki connection...")
        assert await loki_client.test_connection(), "Loki connection failed"
        
        # Test 2: Query Logs
        print("\nQuerying logs...")
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        logs_response = await loki_client.query_logs(
            query='{job="vector"}',
            start_time=start_time,
            end_time=end_time
        )
        
        assert "logs" in logs_response, "Logs response invalid"
        print(f"Retrieved {len(logs_response['logs'])} logs")
        
        # Test 3: RAG Processing
        print("\nTesting RAG processing...")
        if logs_response['logs']:
            chunks_indexed, chunk_ids = await rag_processor.index_logs(logs_response['logs'])
            assert chunks_indexed > 0, "Log indexing failed"
            print(f"Indexed {chunks_indexed} chunks")
            
        # Test 4: Agent Analysis
        print("\nTesting agent analysis...")
        test_query = "Check for authentication failures and performance issues"
        
        log_analysis = await log_agent.analyze(test_query, timedelta(hours=1))
        assert "analysis" in log_analysis, "Log analysis failed"
        
        security_analysis = await security_agent.analyze(test_query, timedelta(hours=1))
        assert "security_analysis" in security_analysis, "Security analysis failed"
        
        print("\nAnalysis Results:")
        print(f"Log Analysis: {log_analysis.get('analysis', '')[:100]}...")
        print(f"Security Analysis: {security_analysis.get('security_analysis', '')[:100]}...")
        
        return True

if __name__ == "__main__":
    test = TestIntegration()
    asyncio.run(test.test_full_pipeline())