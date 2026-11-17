# Natives — Backend (Phase 1)

FastAPI backend for the **Natives** local marketplace for homemade goods and
services. Phase 1 covers customer discovery, seller storefronts & listings, and
administrator management, on top of Supabase (auth + Postgres + storage).

## Stack
- **FastAPI** + **Uvicorn**
- **SQLAlchemy 2.0** (sync, psycopg2) + **Alembic** migrations
- **Supabase**: authentication (JWT), Postgres database, file storage
- **PyJWT** for verifying Supabase access tokens

## Architecture
Authentication is handled entirely by Supabase. The backend **verifies** the
Supabase-issued JWT on each request and maps the token subject (`sub`, a uuid)
to a row in our `public.users` table, which stores role and profile data.
Data access is backend-mediated (the API connects to Postgres with a
privileged connection), so RLS policies are not required for phase 1.

```
app/
  main.py            FastAPI app + /health
  core/              config, database, security (JWT), supabase client
  models/            SQLAlchemy models (one shared Base.metadata)
  schemas/           Pydantic request/response models
  api/
    deps.py          auth / role / pagination dependencies
    router.py        aggregates all routers under /api/v1
    routes/          me, categories, listings, sellers, favorites,
                     follows, seller, admin
alembic/             migration environment + versions/
scripts/seed.py      seed categories + bootstrap admin
```

## Setup

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # then edit .env with your values
```

Fill in `.env`:
- `DATABASE_URL` — Supabase Postgres connection string, prefixed
  `postgresql+psycopg2://`. The default database name is `postgres`. If the
  direct `db.<ref>.supabase.co` host is not reachable on your network, use the
  Session-mode pooler string from the dashboard instead.
- `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` (`sb_publishable_…`),
  `SUPABASE_SECRET_KEY` (`sb_secret_…`, server-only).
- JWT: Supabase signs access tokens with asymmetric keys (ES256). The backend
  verifies them against the project JWKS endpoint, so no shared secret is
  needed (`JWT_ALGORITHM=ES256`). Legacy HS256 projects set `JWT_ALGORITHM=HS256`
  and `SUPABASE_JWT_SECRET`.
- `BOOTSTRAP_ADMIN_EMAIL` — the email to promote to admin via the seed script.

### Supabase storage
Create two public buckets in Supabase Storage: `listing-images` and `avatars`
(or change the names in `.env`). Clients request a signed upload URL from
`POST /api/v1/seller/uploads/signed-url`, upload the file directly to Supabase,
then save the returned `public_url` on the listing/profile.

## Deployment (real environment variables, no `.env` file)

Config is read via `pydantic-settings` (`app/core/config.py`), which already
treats **real process environment variables as higher priority than the
`.env` file** — and works correctly with no `.env` file present at all (it's
gitignored, so it never ships in a deployed image/artifact unless you copy it
yourself). So for any host that injects env vars into the running process
(Docker, Render, Railway, Fly.io, ECS, systemd `Environment=`, etc.), **no
code change is needed** — just set the same variable names from
`.env.example` directly on the host:

```
DATABASE_URL, SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, SUPABASE_SECRET_KEY,
JWT_ALGORITHM, JWT_AUDIENCE, JWT_VERIFY_ISSUER, SUPABASE_JWT_SECRET,
CORS_ORIGINS, LISTING_IMAGES_BUCKET, AVATARS_BUCKET, BOOTSTRAP_ADMIN_EMAIL
```

Names are case-insensitive. `.env` stays for local development only — don't
`COPY`/bake it into a production image.

## Database migrations

```bash
alembic upgrade head          # create all phase-1 tables
python -m scripts.seed        # seed starter categories + promote admin
```

To create a new migration after changing models:
```bash
alembic revision --autogenerate -m "describe change"
```

## Run

```bash
uvicorn app.main:app --reload
```

- Health check: `GET http://127.0.0.1:8000/health`
- Interactive API docs (Swagger): `http://127.0.0.1:8000/docs`

## Authenticating requests
All protected endpoints expect a Supabase user access token:

```
Authorization: Bearer <supabase_access_token>
```

Get a token during development by signing a user in with the Supabase client
(mobile/admin apps do this) and reading `session.access_token`. A Supabase
session alone isn't enough to use the API: `GET /me` 404s until the person
has called `POST /api/v1/me` once to choose a role (`customer` or `seller`),
which creates the matching `users` row — this is what drives the client's
role-selection screen.

## API overview (prefix `/api/v1`)

| Area      | Endpoints |
|-----------|-----------|
| Profile   | `GET/POST/PATCH /me` |
| Categories| `GET /categories/{products,services}/{major,sub}` |
| Discovery | `GET /listings`, `GET /listings/{id}`, `GET /listings/{id}/reviews` |
| Sellers   | `GET /sellers/{id}`, `/sellers/{id}/listings`, `/sellers/{id}/reviews` |
| Favorites | `GET /me/favorites`, `POST/DELETE /me/favorites/{listing_id}` |
| Follows   | `GET /me/follows`, `POST/DELETE /me/follows/{seller_id}` |
| Seller    | `POST /seller/register`, `GET/PATCH /seller/me`, listings CRUD, `GET /seller/reviews`, `POST /seller/uploads/signed-url` |
| Admin     | users, sellers (approve/reject), categories CRUD, listing moderation |

Roles: seller write-operations require an **approved** seller; admin routes
require `role=admin`.

## Scope note
Favourites, follows and a reviews table are included here because the phase-1
customer feature list requires them (add to favourites, follow sellers, see
reviews), even though the spec's table list named only users, seller details,
the four category tables and the listing table. Review **submission** is a
phase-2 feature; phase 1 exposes read-only review endpoints.
