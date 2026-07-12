"""Authenticated share-link management."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from garmin_tracker.deps import CurrentUser, SessionDep
from garmin_tracker.models import ShareLink, utcnow
from garmin_tracker.schemas import ShareLinkCreate, ShareLinkOut

router = APIRouter(prefix="/api/share", tags=["share"])


def _to_out(link: ShareLink) -> ShareLinkOut:
    return ShareLinkOut(
        id=link.id,
        token=link.token,
        label=link.label,
        created_at=link.created_at,
        revoked_at=link.revoked_at,
        path=f"/s/{link.token}",
    )


@router.get("", response_model=list[ShareLinkOut])
def list_share_links(session: SessionDep, user: CurrentUser) -> list[ShareLinkOut]:
    rows = session.exec(
        select(ShareLink)
        .where(ShareLink.user_id == user.id)
        .order_by(ShareLink.created_at.desc())  # type: ignore[attr-defined]
    ).all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=ShareLinkOut, status_code=201)
def create_share_link(
    body: ShareLinkCreate,
    session: SessionDep,
    user: CurrentUser,
) -> ShareLinkOut:
    token = secrets.token_urlsafe(24)
    link = ShareLink(
        user_id=user.id,
        token=token,
        label=(body.label.strip() if body.label else None) or None,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return _to_out(link)


@router.delete("/{link_id}", status_code=204)
def revoke_share_link(
    link_id: str,
    session: SessionDep,
    user: CurrentUser,
) -> None:
    link = session.get(ShareLink, link_id)
    if not link or link.user_id != user.id:
        raise HTTPException(status_code=404, detail="Share link not found")
    if link.revoked_at is None:
        link.revoked_at = utcnow()
        session.add(link)
        session.commit()
