"""Wrapper around python-garminconnect for login, MFA, and activity fetch."""

from __future__ import annotations

import json
import logging
import pickle
from datetime import date
from typing import Any

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

logger = logging.getLogger(__name__)


class GarminClientError(Exception):
    """User-facing Garmin errors."""


class GarminMfaRequired(GarminClientError):
    """Login requires an MFA code; client is held in memory for resume."""

    def __init__(self, client: Garmin, email: str):
        super().__init__("Multi-factor authentication required")
        self.client = client
        self.email = email


class GarminClient:
    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        session_data: str | None = None,
    ):
        self.email = email
        self.password = password
        self.session_data = session_data
        self._client: Garmin | None = None

    @property
    def client(self) -> Garmin:
        if self._client is None:
            raise GarminClientError("Not logged in")
        return self._client

    def login(self) -> str:
        """Authenticate with email/password. Returns serializable token JSON.

        Raises GarminMfaRequired if MFA is needed (hold the client and call
        complete_mfa later).
        """
        if not self.email or not self.password:
            raise GarminClientError("Email and password are required")

        try:
            g = Garmin(
                email=self.email,
                password=self.password,
                return_on_mfa=True,
            )
            result = g.login()
            # return_on_mfa: ("needs_mfa", ...) or (None, None)
            if result and result[0] == "needs_mfa":
                raise GarminMfaRequired(g, self.email)

            self._client = g
            return self.dump_session()
        except GarminMfaRequired:
            raise
        except GarminConnectAuthenticationError as exc:
            raise GarminClientError(
                str(exc) or "Invalid Garmin email or password"
            ) from exc
        except GarminConnectTooManyRequestsError as exc:
            raise GarminClientError(
                "Garmin rate limit — wait a few minutes and try again"
            ) from exc
        except GarminConnectConnectionError as exc:
            raise GarminClientError(f"Could not reach Garmin: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 — surface cleanly to API
            logger.exception("Unexpected Garmin login error")
            raise GarminClientError(f"Garmin login failed: {exc}") from exc

    @classmethod
    def complete_mfa(
        cls, pending: Garmin, mfa_code: str, email: str
    ) -> tuple[GarminClient, str]:
        """Finish MFA on a client that raised GarminMfaRequired."""
        code = mfa_code.strip()
        if not code:
            raise GarminClientError("MFA code is required")
        try:
            pending.resume_login({}, code)
            wrapper = cls(email=email)
            wrapper._client = pending
            return wrapper, wrapper.dump_session()
        except GarminConnectAuthenticationError as exc:
            raise GarminClientError(str(exc) or "Invalid MFA code") from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("MFA completion failed")
            raise GarminClientError(f"MFA failed: {exc}") from exc

    def load_session(self, session_data: str) -> None:
        """Restore from dumps() JSON string (di_token / refresh tokens)."""
        try:
            g = Garmin(email=self.email)
            # Load the JSON blob directly — login(tokenstore=) treats short
            # strings as filesystem paths.
            # because short strings are treated as filesystem paths.
            g.client.loads(session_data)
            if g.client.di_refresh_token and g.client._token_expires_soon():  # noqa: SLF001
                try:
                    g.client._refresh_session()  # noqa: SLF001
                except Exception:  # noqa: BLE001
                    logger.debug("Token refresh failed", exc_info=True)
            try:
                g._load_profile_and_settings()  # noqa: SLF001
            except GarminConnectAuthenticationError:
                raise
            except Exception:  # noqa: BLE001
                logger.debug("Profile load after token restore failed", exc_info=True)
            self._client = g
        except GarminConnectAuthenticationError as exc:
            raise GarminClientError(
                "Garmin session expired — reconnect in Settings"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to restore Garmin session")
            raise GarminClientError(f"Could not restore Garmin session: {exc}") from exc

    def dump_session(self) -> str:
        return self.client.client.dumps()

    def get_activities(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch all activities in [start, end] inclusive (YYYY-MM-DD)."""
        try:
            activities = self.client.get_activities_by_date(
                start.isoformat(),
                end.isoformat(),
            )
            return list(activities or [])
        except GarminConnectAuthenticationError as exc:
            raise GarminClientError(
                "Garmin session expired — reconnect in Settings"
            ) from exc
        except GarminConnectTooManyRequestsError as exc:
            raise GarminClientError(
                "Garmin rate limit while fetching activities — try again later"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("Activity fetch failed")
            raise GarminClientError(f"Failed to fetch activities: {exc}") from exc


def serialize_pending_mfa(client: Garmin, email: str) -> str:
    """Persist a mid-MFA Garmin client so MFA can resume on another request."""
    try:
        dumped = pickle.dumps(client, protocol=pickle.HIGHEST_PROTOCOL)
        return json.dumps({"kind": "pickle", "email": email, "blob": dumped.hex()})
    except Exception:  # noqa: BLE001
        logger.debug("pickle of mid-MFA client failed", exc_info=True)
    try:
        session = client.client.dumps()
        if session:
            return json.dumps({"kind": "garth", "email": email, "session": session})
    except Exception:  # noqa: BLE001
        logger.debug("garth dumps() unavailable for mid-MFA client", exc_info=True)
    raise GarminClientError("Could not serialize pending MFA session — retry Connect")


def deserialize_pending_mfa(payload: str) -> tuple[Garmin, str]:
    data = json.loads(payload)
    email = data["email"]
    kind = data.get("kind")
    if kind == "garth":
        g = Garmin(email=email)
        g.client.loads(data["session"])
        return g, email
    if kind == "pickle":
        client = pickle.loads(bytes.fromhex(data["blob"]))
        return client, email
    raise GarminClientError("Unrecognized pending MFA payload")

