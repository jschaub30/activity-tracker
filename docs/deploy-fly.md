# Deploy Garmin Tracker on Fly.io

Single machine: FastAPI serves the API **and** the built React app. SQLite lives on a Fly **volume**.

## Prerequisites

1. [Fly account](https://fly.io/app/sign-up)
2. [flyctl](https://fly.io/docs/flyctl/install/)

```bash
curl -L https://fly.io/install.sh | sh
fly auth login    # browser login once
```

## One-time setup

From the **repo root**:

```bash
# 1) Create app (unique name; already done if you created garmin-activity-tracker)
fly apps create garmin-activity-tracker

# 2) fly.toml [app] should match the app name

# 3) Volume + secrets
fly volumes create garmin_data --region dfw --size 1 -a garmin-activity-tracker
# generate keys (from repo root, after local `mise run install`):
#   mise run secrets
fly secrets set \
  SECRET_KEY='...' \
  TOKEN_ENCRYPTION_KEY='...' \
  -a garmin-activity-tracker
```

Keep a backup of `TOKEN_ENCRYPTION_KEY`. Changing it invalidates stored Garmin sessions.

## Deploy

```bash
fly deploy -a garmin-activity-tracker --remote-only --no-cache
# or, with cached layers:
# fly deploy -a garmin-activity-tracker --remote-only
```

Open / health:

```bash
fly open -a garmin-activity-tracker
curl -fsS https://garmin-activity-tracker.fly.dev/api/health
```

## After deploy

1. Register an account on the site  
2. **Settings → Connect Garmin** (MFA if prompted)  
3. Wait for sync; use **Review** then **Week** / **Charts**

## Ops

```bash
fly status -a garmin-activity-tracker
fly logs -a garmin-activity-tracker
fly ssh console -a garmin-activity-tracker
fly secrets list -a garmin-activity-tracker
fly volumes list -a garmin-activity-tracker
fly releases -a garmin-activity-tracker
# SQLite path on volume: /data/garmin_tracker.db
```

### Scale / region

```bash
fly scale memory 1024 -a garmin-activity-tracker   # if sync is tight on 512MB
fly platform regions
```

Stay on **1 machine** and **1 uvicorn worker** — Garmin MFA state is in-process memory.

### Custom domain

```bash
fly certs add your.domain.com -a garmin-activity-tracker
# Point DNS as Fly instructs
fly secrets set CORS_ORIGINS=https://your.domain.com -a garmin-activity-tracker
```

## Local Docker smoke test

```bash
docker build -t garmin-tracker .
docker run --rm -p 8000:8000 \
  -e SECRET_KEY=dev-secret-change-me \
  -e TOKEN_ENCRYPTION_KEY="$(cd backend && uv run python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  -v garmin_data:/data \
  garmin-tracker
# http://127.0.0.1:8000
```

## Notes

- **Unofficial Garmin API** — personal use; can break if Garmin changes SSO.
- **Volume backups** — export `/data/garmin_tracker.db` periodically via `fly sftp` or SSH.
- **auto_stop is off** and `min_machines_running = 1` so MFA + long syncs are not killed mid-request.
