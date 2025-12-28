# ClaraVector API Reference

Complete API documentation for integrating with ClaraVector.

**Base URL**: `http://your-host:8000/api/v1`

---

## Data Model

```
User (user_id)
  └── Notebook (notebook_id)
        └── Document (document_id)
              └── Chunks (embedded vectors)
```

**Flow**: User creates notebooks → uploads documents → documents are chunked and embedded → user queries notebooks or entire library.

---

## Authentication

Currently open. Add your auth middleware (JWT, API key) as needed.

---

## Endpoints

### Health Check

#### `GET /health`

Check API and service status.

**Response**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "nim_connected": true,
  "database_connected": true,
  "queue_depth": 0
}
```

---

### Users

#### `POST /users`

Register a new user.

**Request Body**
```json
{
  "user_id": "string (1-255 chars, required)"
}
```

**Response** `201 Created`
```json
{
  "user_id": "user123",
  "created_at": "2025-01-15T10:30:00"
}
```

**Errors**
- `400` - User already exists
- `422` - Invalid user_id format

---

#### `GET /users/{user_id}`

Get user details.

**Response** `200 OK`
```json
{
  "user_id": "user123",
  "created_at": "2025-01-15T10:30:00"
}
```

**Errors**
- `404` - User not found

---

#### `DELETE /users/{user_id}`

Delete user and all their data (notebooks, documents, vectors).

**Response** `200 OK`
```json
{
  "message": "User deleted successfully"
}
```

---

### Notebooks

#### `POST /users/{user_id}/notebooks`

Create a new notebook.

**Request Body**
```json
{
  "name": "string (1-255 chars, required)",
  "description": "string (max 1000 chars, optional)"
}
```

**Response** `201 Created`
```json
{
  "notebook_id": "uuid-string",
  "user_id": "user123",
  "name": "Research Papers",
  "description": "ML research collection",
  "document_count": 0,
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00"
}
```

---

#### `GET /users/{user_id}/notebooks`

List all notebooks for a user.

**Response** `200 OK`
```json
{
  "notebooks": [
    {
      "notebook_id": "uuid-string",
      "user_id": "user123",
      "name": "Research Papers",
      "description": "ML research collection",
      "document_count": 5,
      "created_at": "2025-01-15T10:30:00",
      "updated_at": "2025-01-15T10:30:00"
    }
  ],
  "count": 1
}
```

---

#### `GET /notebooks/{notebook_id}`

Get notebook details.

**Response** `200 OK`
```json
{
  "notebook_id": "uuid-string",
  "user_id": "user123",
  "name": "Research Papers",
  "description": "ML research collection",
  "document_count": 5,
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00"
}
```

---

#### `PUT /notebooks/{notebook_id}`

Update notebook name/description.

**Request Body**
```json
{
  "name": "string (optional)",
  "description": "string (optional)"
}
```

**Response** `200 OK`
```json
{
  "notebook_id": "uuid-string",
  "user_id": "user123",
  "name": "Updated Name",
  "description": "Updated description",
  "document_count": 5,
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T11:00:00"
}
```

---

#### `DELETE /notebooks/{notebook_id}`

Delete notebook and all its documents.

**Response** `200 OK`
```json
{
  "message": "Notebook deleted successfully"
}
```

---

### Documents

#### `POST /notebooks/{notebook_id}/documents`

Upload a document for processing.

**Request**: `multipart/form-data`
- `file`: The document file (required)

**Supported Formats**: PDF, DOCX, PPTX, TXT, MD, HTML, CSV, JSON

**Max Size**: 10MB (configurable)

**Response** `202 Accepted`
```json
{
  "document_id": "uuid-string",
  "filename": "paper.pdf",
  "file_type": "pdf",
  "file_size": 2215244,
  "status": "pending",
  "message": "Document uploaded and queued for processing"
}
```

**Processing Flow**:
1. Document uploaded → status: `pending`
2. Parsing & chunking → status: `processing`
3. Embedding generation (rate-limited) → status: `processing`
4. Complete → status: `completed` or `failed`

---

#### `GET /notebooks/{notebook_id}/documents`

List all documents in a notebook.

**Response** `200 OK`
```json
{
  "documents": [
    {
      "document_id": "uuid-string",
      "notebook_id": "uuid-string",
      "user_id": "user123",
      "filename": "paper.pdf",
      "file_type": "pdf",
      "file_size": 2215244,
      "chunk_count": 29,
      "processing_status": "completed",
      "error_message": null,
      "created_at": "2025-01-15T10:30:00",
      "processed_at": "2025-01-15T10:31:00"
    }
  ],
  "count": 1
}
```

---

#### `GET /documents/{document_id}`

Get document details.

**Response** `200 OK`
```json
{
  "document_id": "uuid-string",
  "notebook_id": "uuid-string",
  "user_id": "user123",
  "filename": "paper.pdf",
  "file_type": "pdf",
  "file_size": 2215244,
  "chunk_count": 29,
  "processing_status": "completed",
  "error_message": null,
  "created_at": "2025-01-15T10:30:00",
  "processed_at": "2025-01-15T10:31:00"
}
```

---

#### `GET /documents/{document_id}/status`

Get detailed processing status with queue information.

**Response** `200 OK`
```json
{
  "document_id": "uuid-string",
  "processing_status": "processing",
  "chunk_count": 29,
  "queue_status": {
    "total": 29,
    "pending": 10,
    "processing": 1,
    "completed": 18,
    "failed": 0
  },
  "error_message": null
}
```

---

#### `DELETE /documents/{document_id}`

Delete document and its vectors.

**Response** `200 OK`
```json
{
  "message": "Document deleted successfully"
}
```

---

### Search / Query

#### `POST /notebooks/{notebook_id}/query`

Search within a single notebook.

**Request Body**
```json
{
  "query": "string (1-2000 chars, required)",
  "top_k": 5
}
```

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `query` | string | required | 1-2000 | Search query |
| `top_k` | int | 5 | 1-20 | Number of results |

**Response** `200 OK`
```json
{
  "query": "What is self-attention?",
  "results": [
    {
      "chunk_id": "doc-uuid_3",
      "document_id": "doc-uuid",
      "notebook_id": "notebook-uuid",
      "text": "Self-attention, sometimes called intra-attention, is an attention mechanism relating different positions of a single sequence...",
      "score": 1.145
    }
  ],
  "result_count": 5,
  "search_time_ms": 537.17
}
```

**Score**: Lower is better (L2 distance). Typical range: 0.8-1.5 for relevant results.

---

#### `POST /users/{user_id}/query`

Search across all user's notebooks (entire library).

**Request Body**
```json
{
  "query": "string (1-2000 chars, required)",
  "top_k": 5
}
```

**Response**: Same format as notebook query.

---

### Queue Status

#### `GET /queue/status`

Get embedding queue statistics.

**Response** `200 OK`
```json
{
  "pending": 15,
  "processing": 1,
  "completed": 1250,
  "failed": 2,
  "estimated_wait_minutes": 0.4
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

| Status Code | Meaning |
|-------------|---------|
| `400` | Bad Request - Invalid input |
| `404` | Not Found - Resource doesn't exist |
| `413` | File too large |
| `415` | Unsupported file type |
| `422` | Validation error |
| `500` | Internal server error |

---

## Rate Limits

**Embedding API (NVIDIA NIM)**: 40 requests per minute

Documents are queued and processed in background. Query requests are prioritized but still rate-limited.

**Estimated Processing Time**:
- ~1.5 seconds per chunk
- 30-chunk document ≈ 45 seconds

---

## Webhook / Polling Pattern

ClaraVector doesn't support webhooks. Poll document status:

```python
import time
import requests

def wait_for_processing(doc_id, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{BASE_URL}/documents/{doc_id}/status")
        status = resp.json()

        if status["processing_status"] == "completed":
            return True
        if status["processing_status"] == "failed":
            raise Exception(status["error_message"])

        time.sleep(2)

    raise TimeoutError("Processing timed out")
```

---

## SDK Examples

### Python

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Create user
requests.post(f"{BASE_URL}/users", json={"user_id": "user123"})

# Create notebook
resp = requests.post(
    f"{BASE_URL}/users/user123/notebooks",
    json={"name": "Research", "description": "Papers"}
)
notebook_id = resp.json()["notebook_id"]

# Upload document
with open("paper.pdf", "rb") as f:
    resp = requests.post(
        f"{BASE_URL}/notebooks/{notebook_id}/documents",
        files={"file": f}
    )
doc_id = resp.json()["document_id"]

# Wait for processing
import time
while True:
    status = requests.get(f"{BASE_URL}/documents/{doc_id}/status").json()
    if status["processing_status"] == "completed":
        break
    time.sleep(2)

# Query
results = requests.post(
    f"{BASE_URL}/notebooks/{notebook_id}/query",
    json={"query": "machine learning", "top_k": 5}
).json()

for r in results["results"]:
    print(f"[{r['score']:.2f}] {r['text'][:100]}...")
```

### JavaScript/TypeScript

```typescript
const BASE_URL = "http://localhost:8000/api/v1";

// Create user
await fetch(`${BASE_URL}/users`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ user_id: "user123" })
});

// Create notebook
const notebookResp = await fetch(`${BASE_URL}/users/user123/notebooks`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name: "Research" })
});
const { notebook_id } = await notebookResp.json();

// Upload document
const formData = new FormData();
formData.append("file", fileInput.files[0]);
const uploadResp = await fetch(`${BASE_URL}/notebooks/${notebook_id}/documents`, {
  method: "POST",
  body: formData
});
const { document_id } = await uploadResp.json();

// Query
const queryResp = await fetch(`${BASE_URL}/notebooks/${notebook_id}/query`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ query: "machine learning", top_k: 5 })
});
const results = await queryResp.json();
```

### cURL

```bash
# Create user
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'

# Create notebook
curl -X POST http://localhost:8000/api/v1/users/user123/notebooks \
  -H "Content-Type: application/json" \
  -d '{"name": "Research"}'

# Upload document
curl -X POST http://localhost:8000/api/v1/notebooks/{notebook_id}/documents \
  -F "file=@paper.pdf"

# Check status
curl http://localhost:8000/api/v1/documents/{document_id}/status

# Query
curl -X POST http://localhost:8000/api/v1/notebooks/{notebook_id}/query \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "top_k": 5}'
```
