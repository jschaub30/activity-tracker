"""Single-table key helpers."""


def user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def email_pk(email: str) -> str:
    return f"EMAIL#{email.lower()}"


def share_pk(token: str) -> str:
    return f"SHARE#{token}"


def sk_profile() -> str:
    return "PROFILE"


def sk_garmin() -> str:
    return "GARMIN"


def sk_mfa() -> str:
    return "MFA"


def sk_act(start_iso: str, garmin_id: str) -> str:
    return f"ACT#{start_iso}#{garmin_id}"


def sk_gid(garmin_id: str) -> str:
    return f"GID#{garmin_id}"


def sk_aid(activity_id: str) -> str:
    return f"AID#{activity_id}"


def sk_week(sunday: str) -> str:
    return f"WEEK#{sunday}"


def sk_sync(started_iso: str, run_id: str) -> str:
    return f"SYNC#{started_iso}#{run_id}"


def sk_synid(run_id: str) -> str:
    return f"SYNID#{run_id}"


def sk_share(token: str) -> str:
    return f"SHARE#{token}"


def act_sk_prefix() -> str:
    return "ACT#"


def sync_sk_prefix() -> str:
    return "SYNC#"


def share_sk_prefix() -> str:
    return "SHARE#"
