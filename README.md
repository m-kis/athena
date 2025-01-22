# Athena AI - Intelligent Log Analysis System
```mermaid
graph TD
    User[User/Client] --> API[FastAPI Endpoints]
    API --> MetaAgent[Meta Agent Orchestrator]
    
    subgraph Agents
        MetaAgent --> LogAgent[Log Analysis Agent]
        MetaAgent --> SecurityAgent[Security Agent]
        MetaAgent --> MetricsAgent[Metrics Agent]
        MetaAgent --> CoreAgent[Core Services]
    end
    
    subgraph Data Sources
        LogAgent --> Loki[Loki Logs]
        MetricsAgent --> Prometheus[Prometheus Metrics]
        SecurityAgent --> SecurityLogs[Security Events]
    end
    
    subgraph Storage
        CoreAgent --> ChromaDB[Vector Store]
        CoreAgent --> PostgreSQL[PostgreSQL]
        CoreAgent --> Redis[Redis Cache]
    end
    
    subgraph ML Services
        LogAgent --> NLP[NLP Models]
        SecurityAgent --> AnomalyDetection[Anomaly Detection]
        MetricsAgent --> Forecasting[Time Series Forecasting]
    end
```

## Project Structure

- `agents/core`: Core functionality and shared components
- `agents/log`: Log analysis agent
- `agents/meta`: Meta agent for orchestration
- `agents/metrics`: Metrics and monitoring agent
- `agents/security`: Security analysis agent

## Installation

```bash
pip install -r requirements.txt
```

## Usage

[Documentation à venir]

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
