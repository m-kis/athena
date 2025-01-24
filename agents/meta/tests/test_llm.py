import asyncio
import sys
sys.path.append('.')  # Ajoute le répertoire courant au path

from src.models.llm import LLMWrapper

# Reste du code identique
async def test_llm():
    llm = LLMWrapper()
    
    # Sample logs
    test_logs = """
    2024-03-10 10:15:23 Failed login attempt for user admin from IP 192.168.1.100
    2024-03-10 10:15:25 Failed login attempt for user admin from IP 192.168.1.100
    2024-03-10 10:15:27 Failed login attempt for user admin from IP 192.168.1.100
    2024-03-10 10:16:00 Successful login for user admin from IP 192.168.1.100
    """
    
    print("Testing log analysis...")
    result = await llm.analyze_logs(test_logs)
    print(f"Analysis result:\n{result}")

if __name__ == "__main__":
    asyncio.run(test_llm())