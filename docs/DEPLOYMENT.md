# Silicon-Pilot Deployment Guide

## Overview
This guide covers deploying Silicon-Pilot in production using Docker.

---

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 13+ (or use Docker Compose)
- 4GB RAM minimum
- 20GB disk space

---

## Quick Start (Docker Compose)

### 1. Environment Setup

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql://postgres:your_password@db:5432/siliconpilot
POSTGRES_PASSWORD=your_password

# API
API_HOST=0.0.0.0
API_PORT=8000

# Optional: OpenAI for LLM features
OPENAI_API_KEY=sk-...
```

### 2. Start Services

```bash
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Check health
curl http://localhost:8000/health
```

### 3. Initialize Database

```bash
# Run schema migrations
docker-compose exec api python scripts/init_db.py

# Populate firmware stacks
docker-compose exec api python scripts/populate_firmware_stacks.py

# Populate reference designs
docker-compose exec api python scripts/populate_reference_designs.py
```

### 4. Access Application

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:8000/

---

## Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run server
CMD ["python", "server.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:17
    environment:
      POSTGRES_DB: siliconpilot
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: .
    environment:
      DATABASE_URL: ${DATABASE_URL}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./datasheets:/app/datasheets
      - ./logs:/app/logs
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## Production Deployment

### 1. Cloud Deployment (AWS/GCP/Azure)

#### AWS ECS

```bash
# Build and push image
docker build -t siliconpilot:latest .
docker tag siliconpilot:latest <your-ecr-repo>:latest
docker push <your-ecr-repo>:latest

# Deploy using ECS task definition
aws ecs create-service \\
    --cluster siliconpilot-cluster \\
    --service-name siliconpilot-api \\
    --task-definition siliconpilot:1 \\
    --desired-count 2 \\
    --launch-type FARGATE
```

#### Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/siliconpilot
gcloud run deploy siliconpilot \\
    --image gcr.io/PROJECT_ID/siliconpilot \\
    --platform managed \\
    --region us-central1 \\
    --allow-unauthenticated
```

### 2. Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: siliconpilot-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: siliconpilot-api
  template:
    metadata:
      labels:
        app: siliconpilot-api
    spec:
      containers:
      - name: api
        image: siliconpilot:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: siliconpilot-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: siliconpilot-api
spec:
  selector:
    app: siliconpilot-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## Monitoring & Logging

### 1. Application Logs

```bash
# Docker Compose
docker-compose logs -f api

# Kubernetes
kubectl logs -f deployment/siliconpilot-api
```

### 2. Metrics (Prometheus)

Add to `server.py`:

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
request_count = Counter('api_requests_total', 'Total API requests')
request_duration = Histogram('api_request_duration_seconds', 'Request duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### 3. Health Monitoring

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  "stats": {
    "total_parts": 1234,
    "total_mcus": 567
  }
}
```

---

## Scaling

### Horizontal Scaling

```bash
# Docker Compose
docker-compose up -d --scale api=3

# Kubernetes
kubectl scale deployment siliconpilot-api --replicas=5
```

### Database Scaling

- Use managed PostgreSQL (AWS RDS, Google Cloud SQL)
- Enable read replicas for search queries
- Use connection pooling (PgBouncer)

---

## Backup & Recovery

### Database Backup

```bash
# Backup
docker-compose exec db pg_dump -U postgres siliconpilot > backup.sql

# Restore
docker-compose exec -T db psql -U postgres siliconpilot < backup.sql
```

### Automated Backups

```bash
# Cron job (daily at 2 AM)
0 2 * * * docker-compose exec db pg_dump -U postgres siliconpilot | gzip > /backups/siliconpilot_$(date +\%Y\%m\%d).sql.gz
```

---

## Security

### 1. API Authentication

Add to `server.py`:

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Verify JWT token
    if credentials.credentials != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials
```

### 2. HTTPS/TLS

Use reverse proxy (Nginx, Traefik):

```nginx
server {
    listen 443 ssl http2;
    server_name api.siliconpilot.com;

    ssl_certificate /etc/ssl/certs/siliconpilot.crt;
    ssl_certificate_key /etc/ssl/private/siliconpilot.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/v1/search")
@limiter.limit("100/hour")
async def search(request: Request):
    ...
```

---

## Performance Optimization

### 1. Database Indexing

```sql
-- Already created in schemas
CREATE INDEX idx_parts_mpn ON parts(mpn);
CREATE INDEX idx_parts_manufacturer ON parts(manufacturer);
CREATE INDEX idx_mcu_specs_flash ON mcu_specs(flash_kb);
```

### 2. Caching (Redis)

```python
import redis.asyncio as redis

cache = redis.Redis(host='localhost', port=6379)

@app.get("/api/v1/parts/{part_id}")
async def get_part(part_id: str):
    # Check cache
    cached = await cache.get(f"part:{part_id}")
    if cached:
        return json.loads(cached)
    
    # Fetch from DB
    part = await db.get_part(part_id)
    
    # Cache for 1 hour
    await cache.setex(f"part:{part_id}", 3600, json.dumps(part))
    return part
```

---

## Troubleshooting

### Common Issues

**1. Database Connection Failed**
```bash
# Check database is running
docker-compose ps db

# Check connection string
echo $DATABASE_URL

# Test connection
docker-compose exec db psql -U postgres -c "SELECT 1"
```

**2. API Not Responding**
```bash
# Check logs
docker-compose logs api

# Check health
curl http://localhost:8000/health

# Restart service
docker-compose restart api
```

**3. Out of Memory**
```bash
# Check memory usage
docker stats

# Increase limits in docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G
```

---

## CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t siliconpilot:${{ github.sha }} .
      
      - name: Run tests
        run: docker run siliconpilot:${{ github.sha }} python -m pytest
      
      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push siliconpilot:${{ github.sha }}
      
      - name: Deploy to production
        run: |
          # Deploy to your cloud provider
          kubectl set image deployment/siliconpilot-api api=siliconpilot:${{ github.sha }}
```

---

## Maintenance

### Regular Tasks

1. **Weekly**: Review logs, check error rates
2. **Monthly**: Update dependencies, security patches
3. **Quarterly**: Database vacuum, backup verification

### Update Procedure

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild images
docker-compose build

# 3. Run migrations
docker-compose exec api python scripts/migrate.py

# 4. Restart services (zero-downtime)
docker-compose up -d --no-deps --build api

# 5. Verify health
curl http://localhost:8000/health
```

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/siliconpilot/issues
- Documentation: https://docs.siliconpilot.com
- Email: support@siliconpilot.com
