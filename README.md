# Auth service

Owns account registration, email-code verification, password login and access/refresh JWTs. Built with FastAPI, SQLAlchemy, asyncpg, Redis and Alembic.

[Notifications](https://github.com/outfit-project/notifation-service) · [Run all services](https://github.com/outfit-project/api-gateway#run-all-repositories)

## Start this repository

Requirements: Docker with Compose 2.20+. Run these commands from this repository:

```bash
cp .env.example .env
docker network create vestis-services
docker compose up --build -d --wait --wait-timeout 120
```

PowerShell also supports `cp`. Copy the example only for initial setup; preserve an existing `.env` and reconcile it with the example. Create the shared network once; skip creation if it already exists. `VESTIS_NETWORK` selects another pre-created network. Example secrets are for local development; replace them for deployment.

Open `http://localhost:8001/docs`. This Compose project starts only auth, PostgreSQL and Redis, using persistent project-specific volumes. No parent files or other service checkouts are required. `docker compose down` stops only this project and preserves its volumes.

Auth queues verification mail without a notification worker. To receive codes, start the notification repository on the same network with `REDIS_URL=redis://vestis-auth-redis:6379/0`; open its Mailpit at `http://localhost:8025`. Auth, wardrobe and outfit must use the same `SECRET_KEY`. The shared network exposes auth as `outfit_auth_api:8000` and its outbox Redis as `vestis-auth-redis:6379`.

## Responsibilities and data

PostgreSQL stores verified users and password hashes. Redis stores pending registrations, resend cooldowns and the mail outbox. A user is created only after a valid verification code is submitted.

1. Registration validates input and checks existing accounts.
2. The password is hashed; pending data and an HMAC hash of the six-digit code are saved in Redis.
3. A `verify_code` event is appended to `mail:outbox` for the notification service.
4. Verification creates the user, removes pending data and issues tokens.

Pending registrations expire after 600 seconds. Resending requires a 60-second cooldown and replaces the code. Five wrong attempts invalidate the pending registration. These values are configurable.

## HTTP API

Paths below are available directly at `http://localhost:8001`, or through a separately started gateway at `http://localhost:8080`. Requests use JSON. Only `/auth/me` requires `Authorization: Bearer <access_token>`.

| Method | Path | Request | Success |
| --- | --- | --- | --- |
| POST | `/auth/register` | `email`, `username`, `password` | 202, `{message}` |
| POST | `/auth/verify` | `email`, six-digit string `code` | 200, token pair |
| POST | `/auth/resend-code` | `email` | 200, generic message |
| POST | `/auth/login` | `username`, `password` | 200, token pair |
| POST | `/auth/refresh` | `refresh_token` | 200, new token pair |
| GET | `/auth/me` | Bearer token | 200, `user_id`, `username`, `email` |

Registration requires a username of 3–128 characters and a password of 8–128 characters. The email local part before `@` must be ASCII; internationalized domains are supported. Login uses the username, not the email address.

Token responses contain `access_token`, `refresh_token` and `token_type: "bearer"`. Access tokens expire after 15 minutes and refresh tokens after 30 days by default. Refresh checks that the user still exists and is active. Issuing a new refresh token does **not** revoke an older one; there is no server-side logout/revocation endpoint. `/auth/me` reads JWT identity rather than querying the database.

Expected errors: 400 for an invalid/expired verification code, 401 for invalid credentials/tokens, 409 for an existing email/username, 422 for invalid input and 429 for the resend cooldown.

## Mail event contract

Redis stream fields, all strings:

```json
{"type": "verify_code", "email": "person@example.com", "code": "012345"}
```

The producer approximately caps the stream at 100,000 entries. Pending-registration records contain hashed codes, but the outbox contains the deliverable code and recipient. Auth queues mail; a successful registration response does not prove SMTP delivery.

## Configuration

Values below describe this repository's [docker-compose.yml](docker-compose.yml). Settings are defined in [app/core/config.py](app/core/config.py). Compose reads this repository's `.env` and passes the explicit environment to the container.

| Variable | Compose value / purpose |
| --- | --- |
| `DB_HOST`, `DB_PORT`, `DB_NAME` | `auth-db`, `5432`, `auth_db` |
| `DB_USER`, `DB_PASSWORD` | Local `.env`; database credentials |
| `REDIS_URL` | `redis://auth-redis:6379/0` |
| `SECRET_KEY`, `ALGORITHM` | Shared JWT secret; `HS256`; must match wardrobe/outfit |
| `ACCESS_EXPIRE_MIN`, `REFRESH_EXPIRE_DAYS` | `15`, `30` |
| `CODE_PEPPER` | Separate verification secret, at least 16 characters |
| `MAIL_STREAM` | `mail:outbox`; must match notification |
| `PENDING_REG_TTL_SEC` | Application default `600` |
| `REG_RESEND_COOLDOWN_SEC` | Application default `60` |
| `VERIFY_MAX_ATTEMPTS` | Application default `5` |
| `CORS_ORIGINS` | Defaults to localhost ports 3000, 5173 and 8080 |
| `DEBUG` | `false` in Compose |

`AUTH_PORT` changes the direct host port (default 8001). Internal database/Redis addresses are managed by Compose; native-development addresses in an old `.env` do not override them.

## Run and inspect

From this repository:

```bash
docker compose ps
docker compose logs -f auth
curl http://localhost:8001/health/ready
```

The container runs `alembic upgrade head` before Uvicorn on port 8000. `GET /health/live` checks the process; `/health/ready` checks PostgreSQL and Redis, not SMTP. The gateway exposes readiness as `/health/auth`. Direct `/docs` and `/openapi.json` belong to the internal API, not the gateway's root route.

For native development, supply service settings with reachable PostgreSQL/Redis addresses, then run `alembic upgrade head` and `uvicorn app.main:app --reload --port 8000` from this directory. Compose does not publish database/Redis ports to the host.

## Checks

Use an isolated Python 3.12 environment, from this repository:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app
```

Tests exercise registration/outbox events, verification/login/refresh, expiry units, cooldown/attempt limits and supported email addresses. For actual delivery, register through `/docs`, read the code in notification's Mailpit and call `/auth/verify`.
