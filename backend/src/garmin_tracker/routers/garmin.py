from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlmodel import Session, select

from garmin_tracker.db import engine
from garmin_tracker.deps import CurrentUser, SessionDep
from garmin_tracker.models import GarminSession, User, utcnow
from garmin_tracker.schemas import (
    GarminConnectRequest,
    GarminConnectResult,
    GarminMfaRequest,
    GarminStatusOut,
)
from garmin_tracker.services.crypto import encrypt_token
from garmin_tracker.services.garmin_client import (
    GarminClient,
    GarminClientError,
    GarminMfaRequired,
    pop_pending_mfa,
    store_pending_mfa,
)
from garmin_tracker.services.sync_service import SyncService

router = APIRouter(prefix="/api/garmin", tags=["garmin"])


def _status_out(row: GarminSession | None) -> GarminStatusOut:
    if not row:
        return GarminStatusOut(connected=False)
    return GarminStatusOut(
        connected=True,
        garmin_email=row.garmin_email,
        connected_at=row.connected_at,
        last_success_at=row.last_success_at,
        last_error=row.last_error,
    )


def _save_session(
    session: Session,
    user: User,
    email: str,
    token_blob: str,
) -> GarminSession:
    encrypted = encrypt_token(token_blob)
    row = session.exec(select(GarminSession).where(GarminSession.user_id == user.id)).first()
    if row:
        row.encrypted_token = encrypted
        row.garmin_email = email.lower()
        row.connected_at = utcnow()
        row.last_error = None
    else:
        row = GarminSession(
            user_id=user.id,
            encrypted_token=encrypted,
            garmin_email=email.lower(),
        )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _kick_off_sync(user_id: str) -> None:
    """Background first sync after connect."""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            return
        svc = SyncService(session, user)
        try:
            if not svc.is_running():
                svc.start_sync()
        except Exception:  # noqa: BLE001
            # Errors recorded on SyncRun / garmin.last_error
            pass


@router.get("/status", response_model=GarminStatusOut)
def garmin_status(session: SessionDep, user: CurrentUser) -> GarminStatusOut:
    row = session.exec(select(GarminSession).where(GarminSession.user_id == user.id)).first()
    return _status_out(row)


@router.post("/connect", response_model=GarminConnectResult)
def garmin_connect(
    body: GarminConnectRequest,
    session: SessionDep,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> GarminConnectResult:
    """Log in to Garmin Connect and store encrypted session tokens."""
    client = GarminClient(email=body.email, password=body.password)
    try:
        token_blob = client.login()
    except GarminMfaRequired as mfa:
        store_pending_mfa(user.id, mfa.client, mfa.email)
        return GarminConnectResult(
            connected=False,
            needs_mfa=True,
            garmin_email=body.email.lower(),
            message="Enter the multi-factor code from your email or authenticator app.",
        )
    except GarminClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    row = _save_session(session, user, body.email, token_blob)
    background_tasks.add_task(_kick_off_sync, user.id)
    return GarminConnectResult(
        connected=True,
        needs_mfa=False,
        garmin_email=row.garmin_email,
        connected_at=row.connected_at,
        last_success_at=row.last_success_at,
        last_error=row.last_error,
        message="Connected. Initial sync started in the background (up to 365 days).",
    )


@router.post("/mfa", response_model=GarminConnectResult)
def garmin_mfa(
    body: GarminMfaRequest,
    session: SessionDep,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> GarminConnectResult:
    pending = pop_pending_mfa(user.id)
    if not pending:
        raise HTTPException(
            status_code=400,
            detail="No pending MFA login. Start Connect again.",
        )
    garmin_obj, email = pending
    try:
        _wrapper, token_blob = GarminClient.complete_mfa(garmin_obj, body.code, email)
    except GarminClientError as exc:
        # Put back so user can retry the same code entry once? Better to require reconnect
        store_pending_mfa(user.id, garmin_obj, email)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    row = _save_session(session, user, email, token_blob)
    background_tasks.add_task(_kick_off_sync, user.id)
    return GarminConnectResult(
        connected=True,
        needs_mfa=False,
        garmin_email=row.garmin_email,
        connected_at=row.connected_at,
        last_success_at=row.last_success_at,
        last_error=None,
        message="Connected after MFA. Initial sync started in the background.",
    )


@router.delete("/connect", status_code=204)
def garmin_disconnect(session: SessionDep, user: CurrentUser) -> None:
    pop_pending_mfa(user.id)
    row = session.exec(select(GarminSession).where(GarminSession.user_id == user.id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="No Garmin connection")
    session.delete(row)
    session.commit()
