"""User preferences API — personal settings and notification config."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user

router = APIRouter(prefix="/preferences", tags=["preferences"])

# In-memory preferences store (production: store in DB)
_user_prefs: dict[str, dict] = {}

DEFAULT_PREFS = {
    "notifications": {
        "pipeline_started": True,
        "pipeline_completed": True,
        "stage_failed": True,
        "qa_p0_issues": True,
        "quotation_generated": True,
    },
    "display": {
        "language": "zh",
        "theme": "light",
        "stages_per_page": 12,
        "show_confidence": True,
        "show_execution_time": True,
    },
    "pipeline": {
        "auto_run_qa": True,
        "skip_stages": [],
        "preferred_model": "claude-sonnet-4-20250514",
        "cache_enabled": True,
    },
}


class UserPreferences(BaseModel):
    notifications: dict = {}
    display: dict = {}
    pipeline: dict = {}


@router.get("", response_model=UserPreferences)
async def get_preferences(user: dict = Depends(get_current_user)):
    """Get current user's preferences."""
    user_id = user["user_id"]
    prefs = _user_prefs.get(user_id, DEFAULT_PREFS.copy())
    return UserPreferences(**prefs)


@router.put("", response_model=UserPreferences)
async def update_preferences(
    data: UserPreferences,
    user: dict = Depends(get_current_user),
):
    """Update user preferences (partial update)."""
    user_id = user["user_id"]
    current = _user_prefs.get(user_id, DEFAULT_PREFS.copy())

    # Merge updates
    if data.notifications:
        current.setdefault("notifications", {}).update(data.notifications)
    if data.display:
        current.setdefault("display", {}).update(data.display)
    if data.pipeline:
        current.setdefault("pipeline", {}).update(data.pipeline)

    _user_prefs[user_id] = current
    return UserPreferences(**current)


@router.delete("")
async def reset_preferences(user: dict = Depends(get_current_user)):
    """Reset preferences to defaults."""
    user_id = user["user_id"]
    _user_prefs[user_id] = DEFAULT_PREFS.copy()
    return {"message": "Preferences reset to defaults"}
