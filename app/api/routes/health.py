from fastapi import APIRouter, Depends

from app.models.responses import HealthResponse
from app.api.dependencies import get_database, get_nim_client
from app.services.database import Database
from app.services.nim_client import NIMClient


router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check(
    db: Database = Depends(get_database),
    nim: NIMClient = Depends(get_nim_client)
):
    """Check system health status."""
    # Check database
    db_ok = True
    try:
        await db.get_user("__health_check__")
    except Exception:
        db_ok = False

    # Check NIM API
    nim_ok = await nim.health_check()

    # Get queue depth
    queue_stats = await db.get_queue_stats()
    queue_depth = queue_stats.get("pending", 0) + queue_stats.get("processing", 0)

    status = "healthy" if db_ok and nim_ok else "degraded"

    return HealthResponse(
        status=status,
        nim_connected=nim_ok,
        database_connected=db_ok,
        queue_depth=queue_depth
    )
