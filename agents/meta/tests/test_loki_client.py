# test_loki_client.py
import asyncio
from datetime import datetime, timedelta
import pytest
from src.embeddings.loki_client import LokiClient

@pytest.fixture
async def loki_client():
    async with LokiClient() as client:
        yield client

@pytest.mark.asyncio
async def test_connection(loki_client):
    """Test connection to Loki server"""
    is_connected = await loki_client.test_connection()
    assert is_connected, "Failed to connect to Loki server"

@pytest.mark.asyncio
async def test_log_query(loki_client):
    """Test basic log querying"""
    # Get logs from last hour
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    query = '{job="vector"}'
    results = await loki_client.search_logs(
        query=query,
        start_time=start_time,
        end_time=end_time,
        limit=100
    )
    
    assert "logs" in results
    assert "stats" in results
    assert isinstance(results["logs"], list)
    assert isinstance(results["stats"], dict)

@pytest.mark.asyncio
async def test_log_parsing(loki_client):
    """Test log parsing functionality"""
    # Sample log entry
    raw_log = {
        "data": {
            "result": [{
                "stream": {
                    "host": "test-host",
                    "source_type": "file"
                },
                "values": [
                    [str(int(datetime.now().timestamp())), 
                     '{"level":"INFO","message":"Test message"}']
                ]
            }]
        }
    }
    
    formatted_logs = await loki_client.format_logs(raw_log)
    assert len(formatted_logs) > 0
    
    log_entry = formatted_logs[0]
    assert "timestamp" in log_entry
    assert "level" in log_entry
    assert "message" in log_entry
    assert log_entry["level"] == "INFO"

@pytest.mark.asyncio
async def test_error_handling(loki_client):
    """Test error handling for invalid queries"""
    # Invalid timestamp
    with pytest.raises(Exception):
        await loki_client.query_logs(
            query='{job="vector"}',
            start="invalid",
            end="invalid"
        )
    
    # Invalid query
    with pytest.raises(Exception):
        await loki_client.query_logs(
            query="invalid{",
            start="0",
            end="1"
        )

@pytest.mark.asyncio
async def test_log_stats(loki_client):
    """Test log statistics generation"""
    sample_logs = [
        {
            "level": "INFO",
            "component": "vector",
            "host": "host1",
            "message": "test"
        },
        {
            "level": "ERROR",
            "component": "vector",
            "host": "host2",
            "message": "error"
        }
    ]
    
    stats = await loki_client.get_log_stats(sample_logs)
    
    assert "total_logs" in stats
    assert stats["total_logs"] == 2
    assert "error_rate" in stats
    assert stats["error_rate"] == 0.5
    assert "level_distribution" in stats
    assert "components" in stats
    assert "hosts" in stats

async def main():
    """Manual test runner"""
    print("Starting Loki client tests...")
    
    async with LokiClient() as client:
        # Test connection
        print("\nTesting connection...")
        is_connected = await client.test_connection()
        print(f"Connected to Loki: {is_connected}")
        
        if not is_connected:
            print("Failed to connect to Loki server. Exiting tests.")
            return
        
        # Test log query
        print("\nTesting log query...")
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        try:
            results = await client.search_logs(
                query='{job="vector"}',
                start_time=start_time,
                end_time=end_time,
                limit=100
            )
            
            print(f"\nFound {len(results['logs'])} logs")
            if results['stats']:
                print("\nLog Statistics:")
                for key, value in results['stats'].items():
                    print(f"{key}: {value}")
                    
        except Exception as e:
            print(f"Error during log query test: {str(e)}")
        
        print("\nTests completed.")

if __name__ == "__main__":
    asyncio.run(main())