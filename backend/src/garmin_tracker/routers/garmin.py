from fastapi import APIRouter, BackgroundTasks, HTTPException

from garmin_tracker.config import get_settings
from garmin_tracker.deps import CurrentUser
from garmin_tracker.models import GarminSession, User, new_id, utcnow
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
    deserialize_pending_mfa,
    serialize_pending_mfa,
)
from garmin_tracker.services.sync_service import SyncService, enqueue_sync, run_sync_job
from garmin_tracker.store import repo

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


def _save_session(user: User, email: str, token_blob: str) -> GarminSession:
    encrypted = encrypt_token(token_blob)
    row = repo.get_garmin(user.id)
    if row:
        row.encrypted_token = encrypted
        row.garmin_email = email.lower()
        row.connected_at = utcnow()
        row.last_error = None
    else:
        row = GarminSession(
            id=new_id(),
            user_id=user.id,
            encrypted_token=encrypted,
            garmin_email=email.lower(),
        )
    return repo.put_garmin(row)


def _kick_off_sync(user: User, background_tasks: BackgroundTasks) -> None:
    svc = SyncService(user)
    try:
        if not svc.is_running():
            run = svc.begin_sync()
            if (get_settings().sync_backend or "inline").lower() == "sqs":
                enqueue_sync(user.id, run.id)
            else:
                background_tasks.add_task(run_sync_job, user.id, run.id)
    except Exception:  # noqa: BLE001
        pass


@router.get("/status", response_model=GarminStatusOut)
def garmin_status(user: CurrentUser) -> GarminStatusOut:
    return _status_out(repo.get_garmin(user.id))


@router.post("/connect", response_model=GarminConnectResult)
def garmin_connect(
    body: GarminConnectRequest,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> GarminConnectResult:
    client = GarminClient(email=body.email, password=body.password)
    try:
        token_blob = client.login()
    except GarminMfaRequired as mfa:
        try:
            blob = serialize_pending_mfa(mfa.client, mfa.email)
        except GarminClientError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        repo.put_mfa(user.id, blob)
        return GarminConnectResult(
            connected=False,
            needs_mfa=True,
            garmin_email=body.email.lower(),
            message="Enter the multi-factor code from your email or authenticator app.",
        )
    except GarminClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    repo.delete_mfa(user.id)
    row = _save_session(user, body.email, token_blob)
    _kick_off_sync(user, background_tasks)
    return GarminConnectResult(
        connected=True,
        needs_mfa=False,
        garmin_email=row.garmin_email,
        connected_at=row.connected_at,
        last_success_at=row.last_success_at,
        last_error=row.last_error,
        message="Connected. Initial sync started in the background (full history).",
    )


@router.post("/mfa", response_model=GarminConnectResult)
def garmin_mfa(
    body: GarminMfaRequest,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> GarminConnectResult:
    blob = repo.get_mfa(user.id)
    if not blob:
        raise HTTPException(
            status_code=400,
            detail="No pending MFA login. Start Connect again.",
        )
    try:
        garmin_obj, email = deserialize_pending_mfa(blob)
        _wrapper, token_blob = GarminClient.complete_mfa(garmin_obj, body.code, email)
    except GarminClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    repo.delete_mfa(user.id)
    row = _save_session(user, email, token_blob)
    _kick_off_sync(user, background_tasks)
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
def garmin_disconnect(user: CurrentUser) -> None:
    repo.delete_mfa(user.id)
    row = repo.get_garmin(user.id)
    if not row:
        raise HTTPException(status_code=404, detail="No Garmin connection")
    repo.delete_garmin(user.id)
