# Athena AI Platform

Plateforme modulaire d'agents IA pour l'analyse et la surveillance de systèmes.

## Agents

- **Core**: Gestion centralisée, API et configurations
- **Log**: Analyse de logs avec RAG et détection de patterns
- **Metrics**: Analyse de métriques et prédictions avec Prophet
- **Security**: Détection d'anomalies et analyse de sécurité
- **Meta**: Orchestration et coordination inter-agents

## Architecture
- Basé sur FastAPI et Langchain
- RAG avec ChromaDB
- LLM via Ollama/Mistral
- Stockage PostgreSQL
- Cache Redis

## Démarrage rapide
```bash
git clone https://github.com/user/athena-monorepo
cd athena-monorepo/agents/core
docker-compose up
