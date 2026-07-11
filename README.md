# Garmin Tracker

Multi-user web app to sync Garmin Connect activities, review/categorize workouts, and view a **Sunday → Saturday** weekly summary of **runs and hikes** (distance + elevation in **miles / feet**).

| Stack | |
|-------|--|
| Backend | Python 3.12, **FastAPI**, SQLModel, SQLite, **uv** |
| Frontend | **React + Vite + TypeScript** |
| Garmin | `garminconnect` (wired in Phase 3) |
| Timezone | America/Denver |
| Backfill | 365 days |

## Project layout

```
garmin-tracker/
├── backend/                 # uv + FastAPI
│   ├── src/garmin_tracker/
│   │   ├── main.py          # app entry
│   │   ├── models.py
│   │   ├── routers/         # auth, garmin, sync, activities, weeks
│   │   └── services/        # sync, week, garmin client stubs
│   ├── data/                # SQLite DB (created at runtime)
│   └── pyproject.toml
├── frontend/                # Vite React SPA
└── README.md
```

## Prerequisites

- [mise](https://mise.jdx.dev/) — installs **Node**, **uv**, and runs project tasks  
  ```bash
  curl https://mise.run | sh
  # add to shell (zsh):
  echo 'eval "$(~/.local/bin/mise activate zsh)"' >> ~/.zshrc && source ~/.zshrc
  ```
- Python 3.12+ is pulled by **uv** as needed

## Setup (mise)

From the repo root:

```bash
mise trust          # once per clone
mise install        # install Node + uv from mise.toml
mise run install    # uv sync + npm install (+ create backend/.env if missing)
mise run secrets    # optional: generate SECRET_KEY / TOKEN_ENCRYPTION_KEY
```

### Common tasks

| Task | What it does |
|------|----------------|
| `mise run backend` | FastAPI with reload → http://127.0.0.1:8000 |
| `mise run frontend` | Vite dev server → http://127.0.0.1:5173 |
| `mise run dev` | Backend **and** frontend in parallel |
| `mise run test` | Backend pytest |
| `mise run lint` | ruff + oxlint |
| `mise run build` | Frontend production build |
| `mise run check` | test + lint + build |
| `mise run docs` | Open OpenAPI docs in browser |
| `mise run secrets` | Print new env secrets |
| `mise tasks` | List all tasks |

API docs: http://127.0.0.1:8000/docs  

App: http://127.0.0.1:5173

## What's implemented (scaffold)

- Multi-user **register / login** (JWT)
- SQLite models: users, garmin sessions, activities, sync runs
- Category model: `run` | `hike` | `stair` | `cardio` | `strength` | `uncategorized`
- Review queue + re-label + bulk-confirm APIs
- Week API (Sun–Sat, Denver) with **combined** mi/ft totals for confirmed runs + hikes + stair steppers
- React pages: login, register, week table, review, activity detail, settings
- **Real Garmin Connect login** (MFA supported), encrypted session tokens  
- **Sync**: 365-day first backfill, then incremental; activities land in **Review**  

## How to download your Garmin data

1. `mise run dev` (or backend + frontend separately)
2. Register / log in to the app
3. **Settings → Connect Garmin** with your Garmin email/password  
   - If MFA is required, enter the code when prompted  
4. Initial sync starts automatically (last **365 days**)  
5. Open **Review**, confirm or re-label each activity  
6. Confirmed **runs / hikes / stairs** show on the **Week** table  
7. Use **Sync now** anytime for incremental updates  

Tokens are stored encrypted in SQLite — password is not kept after login.

## Not yet (later)

1. Daily scheduled sync (cron / APScheduler)  
2. Seed/demo data without Garmin

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
| GET | `/api/weeks?start=YYYY-MM-DD` | week grid data |
| GET/PATCH | `/api/activities/...` | review + re-label |

## License

Personal / local use.
