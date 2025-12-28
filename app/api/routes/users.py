from fastapi import APIRouter, Depends, HTTPException

from app.models.requests import UserCreate
from app.models.responses import UserResponse
from app.api.dependencies import get_database, get_lancedb
from app.services.database import Database
from app.services.lancedb_service import LanceDBService


router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    request: UserCreate,
    db: Database = Depends(get_database)
):
    """Register a new user."""
    user = await db.create_user(request.user_id)
    return UserResponse(
        user_id=user["user_id"],
        created_at=user["created_at"]
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: Database = Depends(get_database)
):
    """Get user information."""
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        user_id=user["user_id"],
        created_at=user["created_at"]
    )


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: Database = Depends(get_database),
    lancedb: LanceDBService = Depends(get_lancedb)
):
    """Delete user and all associated data."""
    # Check user exists
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete vector table
    await lancedb.delete_user_table(user_id)

    # Delete from database (cascades to notebooks, documents, queue)
    await db.delete_user(user_id)
