from fastapi import APIRouter, Depends, HTTPException
import time

from app.models.requests import QueryRequest
from app.models.responses import QueryResponse, QueryResultItem
from app.api.dependencies import get_database, get_lancedb, get_nim_client
from app.services.database import Database
from app.services.lancedb_service import LanceDBService
from app.services.nim_client import NIMClient


router = APIRouter(tags=["Search"])


@router.post("/notebooks/{notebook_id}/query", response_model=QueryResponse)
async def query_notebook(
    notebook_id: str,
    request: QueryRequest,
    db: Database = Depends(get_database),
    lancedb: LanceDBService = Depends(get_lancedb),
    nim: NIMClient = Depends(get_nim_client)
):
    """Query documents within a specific notebook."""
    start_time = time.perf_counter()

    # Check notebook exists
    notebook = await db.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Get query embedding
    query_embedding = await nim.get_query_embedding(request.query)

    # Search in LanceDB
    results = await lancedb.search(
        user_id=notebook["user_id"],
        query_embedding=query_embedding,
        notebook_id=notebook_id,
        top_k=request.top_k
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return QueryResponse(
        query=request.query,
        results=[
            QueryResultItem(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                notebook_id=r["notebook_id"],
                text=r["text"],
                score=r["score"]
            )
            for r in results
        ],
        result_count=len(results),
        search_time_ms=round(elapsed_ms, 2)
    )


@router.post("/users/{user_id}/query", response_model=QueryResponse)
async def query_library(
    user_id: str,
    request: QueryRequest,
    db: Database = Depends(get_database),
    lancedb: LanceDBService = Depends(get_lancedb),
    nim: NIMClient = Depends(get_nim_client)
):
    """Query all documents across user's entire library."""
    start_time = time.perf_counter()

    # Check user exists
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get query embedding
    query_embedding = await nim.get_query_embedding(request.query)

    # Search in LanceDB (no notebook filter)
    results = await lancedb.search(
        user_id=user_id,
        query_embedding=query_embedding,
        notebook_id=None,  # Search all notebooks
        top_k=request.top_k
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return QueryResponse(
        query=request.query,
        results=[
            QueryResultItem(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                notebook_id=r["notebook_id"],
                text=r["text"],
                score=r["score"]
            )
            for r in results
        ],
        result_count=len(results),
        search_time_ms=round(elapsed_ms, 2)
    )
