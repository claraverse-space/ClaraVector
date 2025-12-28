# ClaraVector

Lightweight vector document storage and semantic search API. Designed for edge deployment (Raspberry Pi, small VPS) with NVIDIA NIM embeddings.

## Features

- **Multi-user** - Isolated user data with notebooks
- **Any Document** - PDF, DOCX, PPTX, HTML, TXT, MD, CSV, JSON
- **Semantic Search** - Query by meaning, not keywords
- **Rate-Limited Queue** - Handles NIM's 40 RPM limit gracefully
- **Low Resource** - Runs on 2GB RAM, ~2GB storage for 100 users

## Quick Start

### Docker (Recommended)

```bash
# Clone and configure
git clone https://github.com/your-repo/ClaraVector.git
cd ClaraVector
cp .env.example .env

# Add your NVIDIA NIM API key to .env
# Get one at: https://build.nvidia.com/

# Run
docker compose up -d

# Verify
curl http://localhost:8000/api/v1/health
```

### Manual

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your NIM API key
python scripts/init_db.py
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Usage

```bash
# 1. Create user
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"user_id": "demo"}'

# 2. Create notebook
curl -X POST http://localhost:8000/api/v1/users/demo/notebooks \
  -H "Content-Type: application/json" \
  -d '{"name": "Research"}'
# Returns: {"notebook_id": "abc-123", ...}

# 3. Upload document
curl -X POST http://localhost:8000/api/v1/notebooks/abc-123/documents \
  -F "file=@paper.pdf"
# Returns: {"document_id": "xyz-789", "status": "pending", ...}

# 4. Check processing (poll until "completed")
curl http://localhost:8000/api/v1/documents/xyz-789/status

# 5. Search
curl -X POST http://localhost:8000/api/v1/notebooks/abc-123/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?", "top_k": 5}'
```

## Deploy

### Railway / Render / Fly.io

```bash
# Uses included Dockerfile
# Set environment variable: NIM_API_KEY=your-key
```

See [railway.json](railway.json) for Railway-specific config.

### Raspberry Pi

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Run
docker compose up -d
```

## Documentation

| Doc | Description |
|-----|-------------|
| [API Reference](docs/API.md) | Complete endpoint documentation |
| [Agent Integration](docs/AGENT_INTEGRATION.md) | Guide for AI/LLM integration |
| [Swagger UI](http://localhost:8000/docs) | Interactive API explorer |

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| API | FastAPI | Async, lightweight |
| Vectors | LanceDB | Embedded, no server needed |
| Metadata | SQLite | Zero config |
| Embeddings | NVIDIA NIM | 1024-dim, high quality |
| Parsing | PyMuPDF, python-docx | Robust extraction |

## Configuration

Environment variables (`.env`):

```bash
# Required
NIM_API_KEY=nvapi-xxx

# Optional (defaults shown)
NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NIM_MODEL=nvidia/nv-embedqa-e5-v5
NIM_RPM_LIMIT=40
HOST=0.0.0.0
PORT=8000
MAX_FILE_SIZE_MB=10
```

## Resource Usage

| Users | Docs | Vectors | Storage |
|-------|------|---------|---------|
| 10 | 100 | ~3K | ~200MB |
| 100 | 2000 | ~60K | ~2GB |
| 500 | 10000 | ~300K | ~8GB |

Memory: ~500MB idle, ~1GB under load

## License

MIT
