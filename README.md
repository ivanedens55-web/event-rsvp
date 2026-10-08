# Event RSVP

A host creates an event and shares one public link. Guests reply yes, maybe or no
without an account. The host gets a private dashboard with the guest list and live counts.

The point of the project is **public and private access side by side**: anyone with the
link can RSVP, but only the host who owns the event can see who's coming.

- Live app: `https://<your-app>.vercel.app` (add after deploy)
- API: `https://<your-api>.onrender.com/health`

## Features

- Host accounts (email + password, JWT access tokens)
- Create, edit, close/reopen and delete events
- Unguessable public link per event (`/e/<random-slug>`)
- Guest RSVP with no account: answer, party size, optional note
- Capacity limits counted in people, not replies; "only 2 spots left" messages
- One reply per email per event (case-insensitive)
- Host dashboard: people coming vs capacity, yes/maybe/no counts, guest list
- Safe under load: two guests can't both take the last spot

## Screenshots

| Guest RSVP (mobile) | Reply saved |
|---|---|
| ![RSVP form](docs/screenshots/rsvp-form-mobile.png) | ![Confirmed](docs/screenshots/rsvp-confirmed-mobile.png) |

| Host dashboard | Host's events |
|---|---|
| ![Event dashboard](docs/screenshots/host-event-dashboard.png) | ![Events list](docs/screenshots/host-events-list.png) |

## Tech stack

- **Backend:** Python 3.12, FastAPI, Pydantic, psycopg 3 (connection pool), Argon2 (argon2-cffi), PyJWT
- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, plain CSS
- **Database:** PostgreSQL on Supabase (shared project, tables prefixed `rsvp_`)
- **Hosting:** Render (backend, Frankfurt), Vercel (frontend)
- **Testing:** pytest against a real Postgres, GitHub Actions CI

## Architecture

```mermaid
flowchart LR
    G[Guest browser] -->|HTTPS JSON<br/>no token| FE
    H[Host browser] -->|HTTPS JSON<br/>Bearer JWT| FE
    FE[Next.js on Vercel<br/>display + interaction only] -->|fetch over HTTPS| API
    API[FastAPI on Render<br/>validation, auth, ownership,<br/>RSVP rules] -->|SQL as rsvp_app<br/>Session pooler| DB[(Supabase Postgres<br/>rsvp_hosts<br/>rsvp_events<br/>rsvp_responses)]
```

The browser never talks to the database. The frontend calls the API; the API is the
only thing that holds database credentials.

### Data model

- `rsvp_hosts` 1 → many `rsvp_events` 1 → many `rsvp_responses`
- Deleting an event deletes its RSVPs (`ON DELETE CASCADE`).

### How each architecture rule is applied

| Rule | Where |
|---|---|
| Separation of layers | `frontend/lib/api.ts` is the only network code in the UI and only calls the API. The API only returns JSON. Only `backend/` has a `DATABASE_URL`. |
| API-first | `docs/openapi.yaml` was written first. `backend/tests/test_contract.py` fails if the app's paths, methods or success codes drift from it. |
| Single source of truth | Counts, spots left, "accepting RSVPs" and every rule live in `backend/app/rsvp_logic.py` and SQL. The frontend just displays `counts` and `accepting_rsvps`. |
| Schema design | `db/schema.sql`: foreign keys, `NOT NULL`, `UNIQUE (event_id, email)`, `CHECK`s on lengths, answers, party size and capacity. Each index is explained in a comment. |
| Validation at the boundary | `backend/app/schemas.py` (Pydantic, unknown fields rejected, strings trimmed, timezone-aware future dates). Path params are validated too (`event_id ≥ 1`, slug pattern). `backend/app/repo.py` uses parameterised queries only, including a fixed-text `UPDATE` for partial edits. |
| Stateless auth | `backend/app/security.py`: Argon2id hashes, HS256 JWT with 30-minute expiry, sent in the `Authorization` header. |
| Least privilege | App connects as `rsvp_app`, which can only read/write rows in its three tables (`tests/test_db_privileges.py` proves it can't DROP, ALTER, TRUNCATE or CREATE). Every host query includes `host_id = <current host>`; other hosts' events return 404. Secrets only in env vars. |
| Graceful errors | `backend/app/errors.py`: one `{"error": {"code", "message"}}` shape, friendly messages, full stack traces logged server-side only. |
| CORS + headers | `backend/app/main.py`: CORS from `CORS_ORIGINS` (refuses `*` at startup), `nosniff`, `X-Frame-Options`, `frame-ancestors`, `Referrer-Policy`, HSTS in production. `frontend/next.config.ts` sets a CSP that only allows the API as a fetch target. |

### Token storage trade-off

The JWT is kept in `localStorage`. That's simple and works when the frontend (Vercel) and
API (Render) are on different domains. The downside: any script running on the page
could read it, so an XSS bug would leak the token. Mitigations here: 30-minute expiry,
a strict Content-Security-Policy, and React escaping all rendered text. The safer
alternative is an `httpOnly`, `Secure`, `SameSite` cookie, which scripts can't read, but
across two domains it needs a custom domain or proxy plus CSRF protection. That's listed
under future improvements.

### Concurrency: the last spot

When a guest RSVPs, the API locks that event's row (`SELECT … FOR UPDATE`), counts the
people already coming, checks the rule, inserts, then commits. A second guest racing for
the same spot waits for the lock and then sees the updated count.
`test_last_spot_goes_to_exactly_one_guest` fires 10 parallel RSVPs at a 1-spot event and
expects exactly one success.

## Project structure

```
event-rsvp/
├── backend/
│   ├── app/
│   │   ├── main.py          # app setup: CORS, security headers, routers
│   │   ├── config.py        # settings from environment variables
│   │   ├── db.py            # connection pool
│   │   ├── errors.py        # one JSON error format
│   │   ├── security.py      # Argon2 hashing, JWT
│   │   ├── deps.py          # "who is logged in" dependency
│   │   ├── schemas.py       # Pydantic request/response models
│   │   ├── rsvp_logic.py    # business rules (pure functions)
│   │   ├── repo.py          # all SQL
│   │   └── routers/         # auth.py, events.py (private), public.py (guests)
│   ├── tests/               # logic, validation, contract, auth, events, public, privileges
│   ├── requirements.txt / requirements-dev.txt
│   └── .env.example
├── frontend/
│   ├── app/                 # pages: /, /login, /register, /dashboard, /dashboard/events/[id], /e/[slug]
│   ├── components/          # AuthForm, EventForm, HostTopbar
│   ├── lib/                 # api.ts (the only backend client), auth.ts, format.ts, types.ts
│   ├── next.config.ts       # CSP and security headers
│   └── .env.example
├── db/schema.sql            # tables, constraints, indexes, rsvp_app role, RLS
├── docs/openapi.yaml        # API contract
├── docs/screenshots/
├── render.yaml              # Render blueprint (backend)
└── .github/workflows/ci.yml
```

## Setup (Windows, PowerShell)

### 1. Database (Supabase)

1. Supabase → SQL Editor → paste and run `db/schema.sql`.
2. In the SQL Editor, set the app role's password (use your own long random value):
   `ALTER ROLE rsvp_app WITH PASSWORD 'your-long-random-password';`
3. Project Settings → Database → **Session pooler** connection string. Replace the user with
   `rsvp_app.<project-ref>` and the password with the one from step 2.
4. Keep the Data API off. RLS is enabled by the schema.

### 2. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env   # then fill in DATABASE_URL and JWT_SECRET
uvicorn app.main:app --reload
```

Check `http://localhost:8000/health` returns `{"status":"ok"}`. Interactive docs: `http://localhost:8000/docs`.

### 3. Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

### 4. Tests

Logic, validation and contract tests run with no database:

```powershell
cd backend
.venv\Scripts\Activate.ps1
pytest
```

Database tests need a **throwaway** local Postgres (they wipe the tables, so never point
them at Supabase). With Docker Desktop:

```powershell
docker run --name rsvp-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=rsvp_test -p 5432:5432 -d postgres:16
$env:TEST_ADMIN_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/rsvp_test"
$env:TEST_DATABASE_URL = "postgresql://rsvp_app:test@localhost:5432/rsvp_test"
pytest
```

The test setup applies `db/schema.sql` and sets `rsvp_app`'s password from `TEST_DATABASE_URL`.
CI runs the full suite against Postgres 16 on every push.

## Deployment

**Backend (Render):** New → Blueprint → pick this repo (uses `render.yaml`, Frankfurt).
Set `DATABASE_URL` (Session pooler, `rsvp_app` user) and `CORS_ORIGINS` (your Vercel URL,
no trailing slash). `JWT_SECRET` is generated by Render.

**Frontend (Vercel):** import the repo, Root Directory `frontend`, env var
`NEXT_PUBLIC_API_URL=https://<your-api>.onrender.com`. Then put the Vercel URL into
`CORS_ORIGINS` on Render.

## Limitations

- **No rate limiting** on the public RSVP endpoint, so a script could fill an event with fake replies.
- **Emails aren't verified.** Anyone can reply with any email; one reply per email is a light guard, not identity.
- **Guests can't change their reply.** A second reply from the same email is refused; they have to ask the host.
- **Anyone with the link can RSVP.** The slug is unguessable, but a shared link is access.
- **Token in localStorage** (see trade-off above). No refresh tokens: hosts log in again after 30 minutes.
- **Render free tier sleeps.** The first request after idle can take up to a minute; the UI says so.
- Times are shown in the viewer's browser timezone.

## Future improvements

- Rate limiting and a CAPTCHA on public RSVPs
- Guest "edit my reply" link sent by email (signed, single-purpose token)
- httpOnly cookie auth behind a shared domain, with CSRF protection
- CSV export of the guest list
- Waitlist when an event is full
- Calendar (.ics) download for guests

## License

MIT, see [LICENSE](LICENSE).
