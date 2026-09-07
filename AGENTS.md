# Agent notes

Human setup and product overview: [README.md](README.md). Prefer `mise run …` from the repo root.

## Commands

| Task | Notes |
|------|--------|
| `mise run test` | Backend pytest only (`backend/tests/`, moto DynamoDB) |
| `mise run lint` | ruff (backend) + oxlint (frontend) |
| `mise run check` | test + lint + frontend build |
| `mise start` / `mise stop` | DynamoDB Local `:8000`, API `:8010`, Vite `:5180` |
| `mise run dynamodb` | Docker DynamoDB Local only |
| `mise run deploy` | SPA + Lambda image + terraform apply + CloudFront invalidation |

Do not run `pytest` or `npm test` from the repo root. Frontend has no test script. Ports are **8010 / 5180**, not the FastAPI/Vite defaults. Tests must not hit live AWS (conftest uses moto).

## Invariants

- Weeks are **Sunday–Saturday** in **America/Denver** (`week_service.py`).
- Store metric (`distance_m`, `elevation_gain_m`); display **miles / feet**.
- Garmin walks suggest **hike**; stair climbing / stepper is **stair**.
- Week distance/elevation: confirmed **run + hike + stair** only (`WEEK_SUMMARY_CATEGORIES`).
- Calories sum **all** activities; cardio/strength show duration + calories.
- Synced activities are auto-accepted (confirmed) with the suggested category.
- Persistence is **DynamoDB** (single table). Local uses DynamoDB Local; do not default the API at `mise start` to a real AWS table.
- Do not commit `backend/.env`, `*.tfstate`, `*.tfvars`, or `backend/data/`.

## AWS / Terraform

- All taggable resources use provider `default_tags`: `repo=garmin-tracker`, `created-by=terraform`.
- First apply needs ECR then an image (`mise run deploy:image`) then full apply. See `infra/README.md`.
- Production SPA is same-origin: CloudFront `/*` → S3, `/api/*` → Lambda Function URL. Leave `VITE_API_URL` unset for production builds.

## Layout

- API routers: `backend/src/garmin_tracker/routers/`
- Domain: `services/`, `store/`, `categorization.py`, `units.py`, `models.py`
- Jobs: `jobs/sync_worker.py` (SQS); local `SYNC_BACKEND=inline`
- UI: `frontend/src/pages/` (week, charts, share `/s/:token`, settings)
- Frontend API client: `frontend/src/api/client.ts` (relative `/api`; Vite proxies in dev)
- Infra: `infra/`
