# auth-service

Authentication microservice: email + code verification via Redis, then the
user is created in Postgres and issued a JWT access/refresh pair.

## Flow

```
POST /auth/register   -> creates pending:reg:{email} in Redis (TTL 10 min),
                         enqueues verification email to Redis Stream
mail-worker           -> reads the stream, delivers SMTP email
POST /auth/verify     -> validates code, creates the user in Postgres,
                         returns access + refresh tokens
POST /auth/login      -> username + password -> tokens
POST /auth/refresh    -> refresh token -> new token pair
GET  /auth/me         -> requires Bearer access token
GET  /health/live     -> process liveness
GET  /health/ready    -> Postgres + Redis readiness
```

## Quick start

```bash
docker compose up --build
```

Services:

- `auth`        — FastAPI on http://localhost:8001
- `mail-worker` — consumes Redis Stream `mail:outbox`
- `postgres`    — localhost:5432 (admin/admin, db `auth_db`)
- `redis`       — localhost:6379
- `mailhog`     — SMTP on 1025, Web UI on http://localhost:8025

In `DEBUG=true` mode tables are auto-created via `Base.metadata.create_all`.
For production use Alembic migrations.

## Test the full flow

```bash
# 1. Register
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"a@b.com","username":"alice","password":"supersecret"}'

# 2. Open http://localhost:8025 (MailHog UI) and copy the 6-digit code.

# 3. Verify and receive tokens
curl -X POST http://localhost:8001/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"email":"a@b.com","code":"123456"}'

# 4. Login later
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"supersecret"}'

# 5. Check /me
curl http://localhost:8001/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# 6. Refresh
curl -X POST http://localhost:8001/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<REFRESH>"}'
```

## Redis keys used

| Key                          | Purpose                            | TTL                         |
|------------------------------|------------------------------------|-----------------------------|
| `pending:reg:{email}`        | draft registration payload         | `PENDING_REG_TTL_SEC`       |
| `rate:reg:resend:{email}`    | cooldown between code sends        | `REG_RESEND_COOLDOWN_SEC`   |
| stream `mail:outbox`         | outgoing email tasks               | capped at 100k entries      |
| stream `mail:outbox:dlq`     | dead-letter queue for failed mails | capped at 10k entries       |

The verification code is stored only as `HMAC-SHA256(code, CODE_PEPPER)`,
never in plaintext.
