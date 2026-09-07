# Garmin Tracker

Multi-user web app to sync Garmin Connect activities, review/categorize workouts, and view a **Sunday → Saturday** weekly summary of **runs and hikes** (distance + elevation in **miles / feet**).

| Stack | |
|-------|--|
| Backend | Python 3.12, **FastAPI**, DynamoDB, **uv** |
| Frontend | **React + Vite + TypeScript** on S3 + CloudFront |
| Garmin | `garminconnect` (MFA supported) |
| Timezone | America/Denver |
| Backfill | 365 days |
| Deploy | Terraform → Lambda (container) + S3/CloudFront |

## Project layout

```
garmin-tracker/
├── backend/                 # uv + FastAPI
│   ├── src/garmin_tracker/
│   │   ├── main.py          # app entry
│   │   ├── store/           # DynamoDB single-table repo
│   │   ├── routers/
│   │   ├── services/
│   │   └── jobs/            # SQS sync worker
│   └── Dockerfile           # Lambda image
├── frontend/                # Vite React SPA
├── infra/                   # Terraform
└── README.md
```

## Prerequisites

- [mise](https://mise.jdx.dev/) — installs **Node**, **uv**, and **Terraform**
  ```bash
  curl https://mise.run | sh
  echo 'eval "$(~/.local/bin/mise activate zsh)"' >> ~/.zshrc && source ~/.zshrc
  ```
- Docker (DynamoDB Local for `mise start`)
- Python 3.12+ is pulled by **uv** as needed

## Setup (mise)

From the repo root:

```bash
mise trust          # once per clone
mise install        # Node + uv + terraform from mise.toml
mise run install    # uv sync + npm install (+ create backend/.env if missing)
mise run secrets    # optional: generate SECRET_KEY / TOKEN_ENCRYPTION_KEY
```

Copy `backend/.env.example` → `backend/.env` if install did not. Keep `DYNAMODB_ENDPOINT=http://127.0.0.1:8000` for local.

### Common tasks

| Task | What it does |
|------|----------------|
| `mise start` | DynamoDB Local + backend + frontend |
| `mise stop` | Stop local servers and DynamoDB container |
| `mise run dynamodb` | DynamoDB Local only (`:8000`) |
| `mise run backend` | FastAPI only (foreground) → http://127.0.0.1:8010 |
| `mise run frontend` | Vite only (foreground) → http://127.0.0.1:5180 |
| `mise run test` | Backend pytest (moto, no live AWS) |
| `mise run lint` | ruff + oxlint |
| `mise run build` | Frontend production build |
| `mise run check` | test + lint + build |
| `mise run docs` | Open OpenAPI docs in browser |
| `mise run secrets` | Print new env secrets |
| `mise run deploy` | Image + terraform apply + S3 sync + CloudFront invalidation |
| `mise tasks` | List all tasks |

API docs: http://127.0.0.1:8010/docs

App: http://127.0.0.1:5180

Vite proxies `/api` to the backend, so the SPA uses relative `/api` in both dev and production.

## What's implemented

- Multi-user **register / login** (JWT)
- DynamoDB single table: users, garmin sessions, activities, sync runs, share links, week aggregates
- Category model: `run` | `hike` | `stair` | `cardio` | `strength` | `uncategorized`
- Review queue + re-label + bulk-confirm APIs
- Week API (Sun–Sat, Denver) with **combined** mi/ft totals for confirmed runs + hikes + stair steppers
- React pages: login, register, week table, review, activity detail, charts, share views, settings
- **Real Garmin Connect login** (MFA supported), encrypted session tokens
- **Sync**: 365-day first backfill (chunked), then incremental; activities land in **Review**

## How to download your Garmin data

1. `mise start`
2. Register / log in to the app
3. **Settings → Connect Garmin** with your Garmin email/password
   - If MFA is required, enter the code when prompted
4. Initial sync starts automatically (last **365 days**)
5. Open **Review**, confirm or re-label each activity
6. Confirmed **runs / hikes / stairs** show on the **Week** table
7. Use **Sync now** anytime for incremental updates

Tokens are stored encrypted in DynamoDB — the Garmin password is not kept after login.

Existing SQLite data: `uv run python ../scripts/migrate_sqlite_to_ddb.py` from `backend/` after DynamoDB Local is up.

## AWS deploy

See [infra/README.md](infra/README.md). First apply is two-step (ECR → push image → full apply). All taggable resources get `repo=garmin-tracker` and `created-by=terraform`.

Idle cost is typically a few dollars a month (Lambda idle $0, DynamoDB on-demand cents, CloudFront pennies).

```bash
cd infra
terraform init
terraform apply -target=aws_ecr_repository.api
cd ..
mise run deploy:image
cd infra && terraform apply
mise run deploy   # later updates
```

`terraform destroy` tears it down. Empty the S3 buckets first if destroy complains.

## Product rules

- Garmin **walks → suggested hike**; **stair climbing / stepper → stair**
- Week grid: confirmed **runs + hikes + stairs**
- Totals: **combined** elevation + mileage
- Cardio/strength: duration + calories (Garmin “Calories” field)
- Units: store metric, display **miles / feet**

## API sketch

| Method | Path | Notes |
|--------|------|--------|
| POST | `/api/auth/register` | |
| POST | `/api/auth/login` | |
| GET | `/api/auth/me` | |
| GET/POST/DELETE | `/api/garmin/...` | connect status |
| POST/GET | `/api/sync`, `/api/sync/status` | |
| GET | `/api/weeks` | week grid data |
| GET/PATCH | `/api/activities/...` | review + re-label |

## License

Personal / local use.
