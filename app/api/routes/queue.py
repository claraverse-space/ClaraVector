from fastapi import APIRouter, Depends

from app.models.responses import QueueStatusResponse
from app.api.dependencies import get_database
from app.services.database import Database
from app.config import get_settings


router = APIRouter(prefix="/queue", tags=["Queue"])


@router.get("/status", response_model=QueueStatusResponse)
async def get_queue_status(
    db: Database = Depends(get_database)
):
    """Get embedding queue status."""
    settings = get_settings()
    stats = await db.get_queue_stats()

    # Estimate wait time based on RPM limit
    pending = stats.get("pending", 0) + stats.get("processing", 0)
    rpm = settings.nim_rpm_limit

    # Minutes to process remaining items
    estimated_minutes = (pending / rpm) if pending > 0 else None

    return QueueStatusResponse(
        pending=stats.get("pending", 0),
        processing=stats.get("processing", 0),
        completed=stats.get("completed", 0),
        failed=stats.get("failed", 0),
        estimated_wait_minutes=round(estimated_minutes, 1) if estimated_minutes else None
    )
