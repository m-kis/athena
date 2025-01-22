::: mermaid
flowchart TB
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
