from fastapi import APIRouter, Depends, HTTPException

from app.models.requests import NotebookCreate, NotebookUpdate
from app.models.responses import NotebookResponse, NotebookListResponse
from app.api.dependencies import get_database, get_lancedb
from app.services.database import Database
from app.services.lancedb_service import LanceDBService


router = APIRouter(tags=["Notebooks"])


@router.post("/users/{user_id}/notebooks", response_model=NotebookResponse, status_code=201)
async def create_notebook(
    user_id: str,
    request: NotebookCreate,
    db: Database = Depends(get_database)
):
    """Create a new notebook for a user."""
    # Check user exists
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    notebook = await db.create_notebook(
        user_id=user_id,
        name=request.name,
        description=request.description
    )

    return NotebookResponse(
        notebook_id=notebook["notebook_id"],
        user_id=notebook["user_id"],
        name=notebook["name"],
        description=notebook["description"],
        document_count=notebook["document_count"],
        created_at=notebook["created_at"],
        updated_at=notebook["updated_at"]
    )


@router.get("/users/{user_id}/notebooks", response_model=NotebookListResponse)
async def list_notebooks(
    user_id: str,
    db: Database = Depends(get_database)
):
    """List all notebooks for a user."""
    # Check user exists
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    notebooks = await db.get_user_notebooks(user_id)

    return NotebookListResponse(
        notebooks=[
            NotebookResponse(
                notebook_id=n["notebook_id"],
                user_id=n["user_id"],
                name=n["name"],
                description=n["description"],
                document_count=n["document_count"],
                created_at=n["created_at"],
                updated_at=n["updated_at"]
            )
            for n in notebooks
        ],
        count=len(notebooks)
    )


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(
    notebook_id: str,
    db: Database = Depends(get_database)
):
    """Get notebook details."""
    notebook = await db.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    return NotebookResponse(
        notebook_id=notebook["notebook_id"],
        user_id=notebook["user_id"],
        name=notebook["name"],
        description=notebook["description"],
        document_count=notebook["document_count"],
        created_at=notebook["created_at"],
        updated_at=notebook["updated_at"]
    )


@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(
    notebook_id: str,
    request: NotebookUpdate,
    db: Database = Depends(get_database)
):
    """Update notebook details."""
    notebook = await db.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    updated = await db.update_notebook(
        notebook_id=notebook_id,
        name=request.name,
        description=request.description
    )

    return NotebookResponse(
        notebook_id=updated["notebook_id"],
        user_id=updated["user_id"],
        name=updated["name"],
        description=updated["description"],
        document_count=updated["document_count"],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"]
    )


@router.delete("/notebooks/{notebook_id}", status_code=204)
async def delete_notebook(
    notebook_id: str,
    db: Database = Depends(get_database),
    lancedb: LanceDBService = Depends(get_lancedb)
):
    """Delete a notebook and all its documents."""
    notebook = await db.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Delete vectors
    await lancedb.delete_notebook_vectors(notebook["user_id"], notebook_id)

    # Delete from database (cascades to documents and queue)
    await db.delete_notebook(notebook_id)
