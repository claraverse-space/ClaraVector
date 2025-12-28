# ClaraVector - AI Agent Integration Guide

This guide helps AI agents (LLMs, autonomous agents, chatbots) integrate ClaraVector as a knowledge retrieval backend.

---

## What ClaraVector Does

ClaraVector is a **document storage and semantic search API**. It:

1. Stores documents organized in notebooks per user
2. Chunks and embeds documents using NVIDIA NIM (1024-dim vectors)
3. Provides semantic search across documents

**Use Case**: Give your AI agent access to user-uploaded documents for RAG (Retrieval-Augmented Generation).

---

## Quick Integration

### 1. Setup User Context

Each user of your application gets a unique `user_id`:

```
POST /api/v1/users
{"user_id": "your-app-user-id"}
```

### 2. Create Knowledge Notebooks

Organize documents by topic/purpose:

```
POST /api/v1/users/{user_id}/notebooks
{"name": "Product Docs", "description": "Company product documentation"}
```

### 3. Ingest Documents

Upload documents (PDF, DOCX, TXT, MD, HTML, CSV, JSON, PPTX):

```
POST /api/v1/notebooks/{notebook_id}/documents
Content-Type: multipart/form-data
file: <document>
```

**Important**: Document processing is async. Poll status until `completed`:

```
GET /api/v1/documents/{document_id}/status
```

### 4. Query for Context

When your agent needs information, query relevant notebooks:

```
POST /api/v1/notebooks/{notebook_id}/query
{"query": "user's question or search terms", "top_k": 5}
```

Or search all user documents:

```
POST /api/v1/users/{user_id}/query
{"query": "search terms", "top_k": 5}
```

---

## Agent Tool Definition

### For OpenAI Function Calling / Tool Use

```json
{
  "name": "search_knowledge_base",
  "description": "Search the user's uploaded documents for relevant information. Use this when the user asks questions that might be answered by their documents.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The search query - use keywords and phrases relevant to the information needed"
      },
      "notebook_id": {
        "type": "string",
        "description": "Optional: specific notebook to search. If not provided, searches all user documents."
      },
      "top_k": {
        "type": "integer",
        "description": "Number of results to return (1-20)",
        "default": 5
      }
    },
    "required": ["query"]
  }
}
```

### For Claude Tool Use

```json
{
  "name": "search_knowledge_base",
  "description": "Search the user's uploaded documents for relevant information. Returns text chunks ranked by semantic similarity to the query.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query - keywords or natural language question"
      },
      "notebook_id": {
        "type": "string",
        "description": "Specific notebook ID to search (optional)"
      },
      "top_k": {
        "type": "integer",
        "description": "Number of results (1-20)",
        "default": 5
      }
    },
    "required": ["query"]
  }
}
```

### For LangChain

```python
from langchain.tools import Tool
import requests

CLARA_URL = "http://localhost:8000/api/v1"

def search_docs(query: str, user_id: str, top_k: int = 5) -> str:
    """Search user's documents for relevant information."""
    resp = requests.post(
        f"{CLARA_URL}/users/{user_id}/query",
        json={"query": query, "top_k": top_k}
    )
    results = resp.json()["results"]

    if not results:
        return "No relevant documents found."

    context = []
    for r in results:
        context.append(f"[Score: {r['score']:.2f}]\n{r['text']}")

    return "\n\n---\n\n".join(context)

knowledge_tool = Tool(
    name="search_knowledge_base",
    func=lambda q: search_docs(q, current_user_id, 5),
    description="Search user's uploaded documents for relevant information"
)
```

---

## Response Format

Query responses return ranked text chunks:

```json
{
  "query": "How does authentication work?",
  "results": [
    {
      "chunk_id": "doc123_5",
      "document_id": "doc123",
      "notebook_id": "nb456",
      "text": "Authentication uses JWT tokens. Users login with email/password and receive a token valid for 24 hours...",
      "score": 0.92
    },
    {
      "chunk_id": "doc123_6",
      "document_id": "doc123",
      "notebook_id": "nb456",
      "text": "To refresh tokens, call the /auth/refresh endpoint with the current token...",
      "score": 1.15
    }
  ],
  "result_count": 2,
  "search_time_ms": 45.2
}
```

**Score Interpretation**:
- Lower = more relevant (L2 distance)
- `< 1.0` = highly relevant
- `1.0 - 1.3` = relevant
- `> 1.5` = loosely related

---

## RAG Implementation Pattern

```python
import requests
from openai import OpenAI

CLARA_URL = "http://localhost:8000/api/v1"
client = OpenAI()

def rag_query(user_question: str, user_id: str) -> str:
    # 1. Retrieve relevant context
    search_resp = requests.post(
        f"{CLARA_URL}/users/{user_id}/query",
        json={"query": user_question, "top_k": 5}
    )
    results = search_resp.json()["results"]

    # 2. Build context from results
    if results:
        context = "\n\n".join([
            f"[From: {r['document_id']}]\n{r['text']}"
            for r in results
            if r["score"] < 1.5  # Filter low-relevance
        ])
    else:
        context = "No relevant documents found."

    # 3. Generate response with context
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": f"""Answer based on the provided context. If the context doesn't contain relevant information, say so.

Context from user's documents:
{context}"""
            },
            {"role": "user", "content": user_question}
        ]
    )

    return response.choices[0].message.content
```

---

## Best Practices

### Query Formulation

**Good queries**:
- Use specific keywords: `"JWT token authentication flow"`
- Include domain terms: `"kubernetes pod scaling policy"`
- Ask natural questions: `"How do I configure SSL certificates?"`

**Avoid**:
- Single words: `"auth"` (too broad)
- Very long queries: Keep under 200 words
- Unrelated terms: Don't mix topics

### Handling Results

1. **Check result count**: If 0, inform user no docs found
2. **Filter by score**: Ignore results with score > 1.5
3. **Cite sources**: Include document_id in responses
4. **Combine chunks**: Related chunks may be from same document

### Error Handling

```python
def safe_search(query: str, user_id: str) -> dict:
    try:
        resp = requests.post(
            f"{CLARA_URL}/users/{user_id}/query",
            json={"query": query, "top_k": 5},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {"error": "Search timed out", "results": []}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "results": []}
```

---

## Document Management for Agents

### List Available Notebooks

```
GET /api/v1/users/{user_id}/notebooks
```

Use this to show users what knowledge bases are available or to let agents choose which notebook to search.

### Check Document Status

Before querying newly uploaded documents:

```python
def is_document_ready(doc_id: str) -> bool:
    resp = requests.get(f"{CLARA_URL}/documents/{doc_id}/status")
    return resp.json()["processing_status"] == "completed"
```

### Get Document Metadata

```
GET /api/v1/documents/{document_id}
```

Returns filename, type, chunk count - useful for citations.

---

## Multi-Tenant Architecture

ClaraVector is designed for multi-user applications:

```
Your App
   │
   ├── User A (user_id: "user_a")
   │     ├── Notebook: "Work Projects"
   │     │     └── project_spec.pdf, requirements.docx
   │     └── Notebook: "Research"
   │           └── papers/*.pdf
   │
   └── User B (user_id: "user_b")
         └── Notebook: "Personal Notes"
               └── notes.md, journal.txt
```

**Data Isolation**: Users can only access their own notebooks and documents. Queries automatically filter by user context.

---

## Performance Considerations

| Operation | Typical Latency |
|-----------|-----------------|
| Query (5 results) | 200-600ms |
| Document upload | < 1s |
| Document processing | ~1.5s per chunk |
| Health check | < 50ms |

**Rate Limits**:
- Embedding API: 40 RPM (affects document processing)
- Query API: No hard limit, but embeddings needed

**Recommendations**:
- Cache frequent queries at application level
- Batch document uploads during off-peak
- Use `top_k=3-5` for most use cases

---

## Example: Full Agent Integration

```python
"""
Complete example: AI assistant with document knowledge base
"""
import requests
from anthropic import Anthropic

CLARA_URL = "http://localhost:8000/api/v1"
client = Anthropic()

# Tool definition
tools = [{
    "name": "search_documents",
    "description": "Search the user's uploaded documents for information",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"]
    }
}]

def handle_tool_call(tool_name: str, tool_input: dict, user_id: str) -> str:
    if tool_name == "search_documents":
        resp = requests.post(
            f"{CLARA_URL}/users/{user_id}/query",
            json={"query": tool_input["query"], "top_k": 5}
        )
        results = resp.json()["results"]

        if not results:
            return "No relevant documents found for this query."

        return "\n\n".join([
            f"**Source**: {r['document_id']}\n{r['text']}"
            for r in results
        ])

    return "Unknown tool"

def chat(user_message: str, user_id: str, history: list) -> str:
    history.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system="You are a helpful assistant with access to the user's documents. Use the search_documents tool to find relevant information when needed.",
        tools=tools,
        messages=history
    )

    # Handle tool use
    while response.stop_reason == "tool_use":
        tool_use = next(b for b in response.content if b.type == "tool_use")

        tool_result = handle_tool_call(
            tool_use.name,
            tool_use.input,
            user_id
        )

        history.append({"role": "assistant", "content": response.content})
        history.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": tool_result
            }]
        })

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system="You are a helpful assistant with access to the user's documents.",
            tools=tools,
            messages=history
        )

    assistant_message = response.content[0].text
    history.append({"role": "assistant", "content": assistant_message})

    return assistant_message

# Usage
history = []
user_id = "user123"

print(chat("What does our security policy say about passwords?", user_id, history))
```

---

## Troubleshooting

**No results returned**
- Check document processing completed
- Verify notebook has documents
- Try broader search terms

**Slow queries**
- Reduce `top_k`
- Check server health endpoint
- Consider query caching

**Document processing stuck**
- Check queue status: `GET /queue/status`
- Verify NIM API connectivity: `GET /health`
- Check for failed chunks in document status

---

## API Reference

Full API documentation: [API.md](./API.md)

Interactive docs: `http://your-host:8000/docs`
