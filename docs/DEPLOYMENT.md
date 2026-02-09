# HardwareGenius - Production Deployment Guide

**Version**: 1.0.0  
**Status**: Production-Ready  
**Date**: February 9, 2026

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis (optional, for caching)
- Node.js 18+ (for web UI)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/HardwareGenius.git
cd HardwareGenius

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python scripts/setup_database.py

# Run migrations
python ingestion/batch_ingestion.py

# Start web UI
cd web_ui
python app.py
```

Access at: `http://localhost:8000`

---

## 📋 System Architecture

### Components

1. **Core Engine** (`core/`)
   - Database layer
   - Models and schemas
   - Evidence management

2. **Template System** (`templates/`)
   - 12 production templates
   - Template loader and validator
   - Rule engine

3. **Subsystem Solvers** (`solver/subsystems/`)
   - 7 component category solvers
   - Deterministic filtering and ranking
   - Evidence-backed recommendations

4. **Architecture Synthesis** (`architecture/`)
   - Graph builder
   - Constraint compiler
   - BOM composer
   - Configuration generator
   - Export manager

5. **Web UI** (`web_ui/`)
   - FastAPI backend
   - Responsive frontend
   - Export functionality

---

## 🗄️ Database Setup

### PostgreSQL Configuration

```sql
-- Create database
CREATE DATABASE hardwaregenius;

-- Create user
CREATE USER hg_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE hardwaregenius TO hg_user;
```

### Environment Variables

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql://hg_user:your_password@localhost:5432/hardwaregenius

# OpenAI (optional, for LLM features)
OPENAI_API_KEY=your_openai_key

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Environment
ENVIRONMENT=production
DEBUG=false
```

### Run Migrations

```bash
# Create tables
python solver/subsystems/db_integration.py

# Ingest sample data
python ingestion/batch_ingestion.py
```

---

## 🌐 Web UI Deployment

### Development

```bash
cd web_ui
python app.py
```

### Production (with Gunicorn)

```bash
pip install gunicorn
gunicorn web_ui.app:app --workers 4 --bind 0.0.0.0:8000
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "web_ui.app:app", "--workers", "4", "--bind", "0.0.0.0:8000"]
```

```bash
# Build and run
docker build -t hardwaregenius .
docker run -p 8000:8000 --env-file .env hardwaregenius
```

### Docker Compose

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://hg_user:password@db:5432/hardwaregenius
    depends_on:
      - db
  
  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=hardwaregenius
      - POSTGRES_USER=hg_user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 📡 API Usage

### Parse Intent

```bash
curl -X POST http://localhost:8000/api/parse-intent \
  -H "Content-Type: application/json" \
  -d '{"input": "I want to build a CAN motor controller"}'
```

### List Templates

```bash
curl http://localhost:8000/api/templates
```

### Build Architecture

```bash
curl -X POST http://localhost:8000/api/build-architecture \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "can_motor_controller_v1",
    "answers": {
      "motor_type": "BLDC",
      "supply_voltage": "24"
    }
  }'
```

### Export Design

```bash
curl -X POST http://localhost:8000/api/export \
  -H "Content-Type: application/json" \
  -d '{
    "format": "kicad",
    "bom": [...],
    "project_name": "MyDesign"
  }'
```

---

## 🔧 Configuration

### Template Configuration

Templates are stored in `templates/` directory:

```
templates/
├── motor_controller/
│   └── can_motor_controller.yaml
├── sensor_node/
│   └── iot_sensor_node.yaml
└── ...
```

### Adding New Templates

1. Create new directory in `templates/`
2. Create YAML file following template schema
3. Validate with `TemplateValidator`
4. Restart application

### Subsystem Solver Configuration

Solvers are in `solver/subsystems/`:

- `multi_solver.py` - Power, Transceiver, Sensor
- `additional_solvers.py` - Memory, Display, Connector, Protection
- `db_integration.py` - Database-connected solvers

---

## 📊 Monitoring

### Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hardwaregenius.log'),
        logging.StreamHandler()
    ]
)
```

### Metrics

Key metrics to monitor:

- Request latency
- Template match accuracy
- BOM generation success rate
- Export success rate
- Database query performance

### Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "templates": len(template_loader.load_all_templates())
    }
```

---

## 🔒 Security

### Best Practices

1. **Environment Variables**: Never commit `.env` files
2. **Database**: Use strong passwords, enable SSL
3. **API**: Implement rate limiting
4. **Input Validation**: Sanitize all user inputs
5. **CORS**: Configure allowed origins

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/parse-intent")
@limiter.limit("10/minute")
async def parse_intent(request: Request):
    ...
```

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_phase2_system.py

# With coverage
pytest --cov=. tests/
```

### Test Categories

- Unit tests: Template system, solvers
- Integration tests: End-to-end pipeline
- API tests: Web UI endpoints

---

## 📦 Production Checklist

- [ ] Database configured and migrated
- [ ] Environment variables set
- [ ] Templates validated
- [ ] Component database populated (5K+ parts)
- [ ] Web UI tested
- [ ] API endpoints tested
- [ ] Exports tested (Eagle, KiCad, etc.)
- [ ] Logging configured
- [ ] Monitoring setup
- [ ] Backups configured
- [ ] SSL/TLS enabled
- [ ] Rate limiting enabled
- [ ] Documentation updated

---

## 🚀 Scaling

### Horizontal Scaling

- Use load balancer (nginx, HAProxy)
- Multiple web server instances
- Shared database
- Redis for session management

### Database Optimization

- Index frequently queried fields
- Use connection pooling
- Implement caching layer
- Regular VACUUM and ANALYZE

### Caching Strategy

```python
import redis

redis_client = redis.Redis(host='localhost', port=6379)

# Cache template matches
cache_key = f"matches:{user_input_hash}"
cached = redis_client.get(cache_key)
if cached:
    return json.loads(cached)
```

---

## 📞 Support

### Documentation
- API Docs: `http://localhost:8000/docs`
- Template Guide: `docs/template_authoring.md`
- Architecture: `docs/architecture.md`

### Troubleshooting

**Issue**: Database connection fails  
**Solution**: Check DATABASE_URL, ensure PostgreSQL is running

**Issue**: Templates not loading  
**Solution**: Validate YAML syntax, check file permissions

**Issue**: Export fails  
**Solution**: Ensure output directory exists and is writable

---

## 📄 License

MIT License - See LICENSE file

---

**HardwareGenius is production-ready and ready to scale!**
