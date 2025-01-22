# Deployment Guide

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- PostgreSQL 13+
- Python 3.9+

## Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/m-kis/athena.git
cd athena
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Start services:
```bash
docker-compose up -d
```

4. Initialize database:
```bash
python src/scripts/create_tables.py
```

5. Start application:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Production Deployment

### Using Docker

```bash
# Build image
docker build -t athena-ai .

# Run container
docker run -d -p 8000:8000 athena-ai
```

### Manual Setup

1. Set up virtual environment
2. Install production dependencies
3. Configure Nginx/Apache
4. Set up SSL/TLS
5. Configure monitoring

## Environment Variables

Required environment variables:
- `DATABASE_URL`
- `REDIS_URL`
- `LOKI_URL`
- `CHROMA_URL`
- `SECRET_KEY`

## Monitoring

- Prometheus metrics at `/metrics`
- Grafana dashboards available
- Health check endpoint at `/health`

## Backup

1. Database backup:
```bash
pg_dump -U postgres athenadb > backup.sql
```

2. Vector store backup:
```bash
docker exec -it chroma ./backup.sh
```

## Security Considerations

- Use strong passwords
- Enable rate limiting
- Set up firewalls
- Monitor logs
- Regular updates
