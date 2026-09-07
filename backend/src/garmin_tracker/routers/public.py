"""Unauthenticated read-only views via share token."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from garmin_tracker.models import ShareLink, User
from garmin_tracker.schemas import PublicShareMeta, WeekOut, WeeksListOut
from garmin_tracker.services.week_service import build_week, build_weeks_list
from garmin_tracker.store import repo

router = APIRouter(prefix="/api/public", tags=["public"])


def _resolve_share_user(token: str) -> tuple[ShareLink, User]:
    link = repo.get_share_by_token(token)
    if not link or link.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Share link not found or revoked")
    user = repo.get_user(link.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Share link not found or revoked")
    return link, user


def _owner_display(email: str) -> str:
    local = email.split("@", 1)[0]
    return local or "Athlete"


@router.get("/{token}", response_model=PublicShareMeta)
def public_meta(token: str) -> PublicShareMeta:
    link, user = _resolve_share_user(token)
    return PublicShareMeta(
        label=link.label,
        timezone=user.timezone or "America/Denver",
        owner_display=_owner_display(user.email),
    )


@router.get("/{token}/weeks", response_model=WeeksListOut)
def public_weeks(
    token: str,
    count: int = Query(default=52, ge=1, le=104),
) -> WeeksListOut:
    _link, user = _resolve_share_user(token)
    return build_weeks_list(user, count=count)


@router.get("/{token}/weeks/detail", response_model=WeekOut)
def public_week_detail(
    token: str,
    start: str | None = Query(default=None),
) -> WeekOut:
    _link, user = _resolve_share_user(token)
    return build_week(user, start)
