# Agent notes

Human setup and product overview: [README.md](README.md). Prefer `mise run …` from the repo root.

## Commands

| Task | Notes |
|------|--------|
| `mise run test` | Backend pytest only (`backend/tests/`) |
| `mise run lint` | ruff (backend) + oxlint (frontend) |
| `mise run check` | test + lint + frontend build |
| `mise start` / `mise stop` | Local API `:8010` and Vite `:5180` |

Do not run `pytest` or `npm test` from the repo root. Frontend has no test script. Ports are **8010 / 5180**, not the FastAPI/Vite defaults.

## Invariants

- Weeks are **Sunday–Saturday** in **America/Denver** (`week_service.py`).
- Store metric (`distance_m`, `elevation_gain_m`); display **miles / feet**.
- Garmin walks suggest **hike**; stair climbing / stepper is **stair**.
- Week distance/elevation: confirmed **run + hike + stair** only (`WEEK_SUMMARY_CATEGORIES`).
- Calories sum **all** confirmed activities; cardio/strength show duration + calories.
- New Garmin activities land in **Review** (`pending`) until confirmed.
- Do not commit `backend/.env` or `backend/data/`.

## Layout

- API routers: `backend/src/garmin_tracker/routers/` (`/api/auth`, `garmin`, `sync`, `activities`, `weeks`, `share`, `public`, `account`)
- Domain: `services/`, `categorization.py`, `units.py`, `models.py`
- UI: `frontend/src/pages/` (week, review, charts, share `/s/:token`, settings)
- Frontend API client: `frontend/src/api/client.ts` (`VITE_API_URL` → `:8010` in dev)
