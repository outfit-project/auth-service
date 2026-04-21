import asyncio
import logging
from email.message import EmailMessage

import aiosmtplib
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.core.config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s mail-worker %(message)s",
)
logger = logging.getLogger("mail-worker")

VERIFY_SUBJECT = "Your verification code"
VERIFY_TEMPLATE = (
    "Hi!\n\n"
    "Your verification code is: {code}\n"
    "It will expire in {ttl_min} minutes.\n\n"
    "If you did not request this, just ignore the email."
)

BLOCK_MS = 5_000
MAX_DELIVERY_RETRIES = 5
RETRY_BASE_DELAY_SEC = 2


async def _ensure_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(
            name=settings.MAIL_STREAM,
            groupname=settings.MAIL_GROUP,
            id="$",
            mkstream=True,
        )
        logger.info("Consumer group created")
    except ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            logger.debug("Consumer group already exists")
        else:
            raise


async def _send_smtp(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER or None,
        password=settings.SMTP_PASSWORD or None,
        use_tls=settings.SMTP_TLS,
        start_tls=False if settings.SMTP_TLS else None,
        timeout=15,
    )


async def _process(fields: dict) -> None:
    msg_type = fields.get("type")
    if msg_type == "verify_code":
        email = fields["email"]
        code = fields["code"]
        body = VERIFY_TEMPLATE.format(
            code=code,
            ttl_min=settings.PENDING_REG_TTL_SEC // 60,
        )
        logger.info("Delivering verification code to %s", email)
        await _send_smtp(email, VERIFY_SUBJECT, body)
    else:
        logger.warning("Unknown message type: %s", msg_type)


async def _handle_entry(redis: Redis, entry_id: str, fields: dict) -> None:
    delay = RETRY_BASE_DELAY_SEC
    for attempt in range(1, MAX_DELIVERY_RETRIES + 1):
        try:
            await _process(fields)
            await redis.xack(
                settings.MAIL_STREAM, settings.MAIL_GROUP, entry_id
            )
            logger.info("ACK %s", entry_id)
            return
        except Exception as exc:
            logger.warning(
                "Delivery attempt %d/%d failed for %s: %s",
                attempt,
                MAX_DELIVERY_RETRIES,
                entry_id,
                exc,
            )
            if attempt == MAX_DELIVERY_RETRIES:
                logger.error(
                    "Giving up on %s after %d attempts; moving to DLQ",
                    entry_id,
                    MAX_DELIVERY_RETRIES,
                )
                await redis.xadd(
                    f"{settings.MAIL_STREAM}:dlq",
                    {**fields, "failed_from": entry_id, "error": str(exc)},
                    maxlen=10_000,
                    approximate=True,
                )
                await redis.xack(
                    settings.MAIL_STREAM, settings.MAIL_GROUP, entry_id
                )
                return
            await asyncio.sleep(delay)
            delay *= 2


async def run() -> None:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    await _ensure_group(redis)
    logger.info(
        "Started consumer %s of group %s on stream %s",
        settings.MAIL_CONSUMER,
        settings.MAIL_GROUP,
        settings.MAIL_STREAM,
    )

    try:
        while True:
            try:
                resp = await redis.xreadgroup(
                    groupname=settings.MAIL_GROUP,
                    consumername=settings.MAIL_CONSUMER,
                    streams={settings.MAIL_STREAM: ">"},
                    count=10,
                    block=BLOCK_MS,
                )
            except Exception as exc:
                logger.error("Redis read error: %s; retrying in 2s", exc)
                await asyncio.sleep(2)
                continue

            if not resp:
                continue

            for _stream, entries in resp:
                for entry_id, fields in entries:
                    await _handle_entry(redis, entry_id, fields)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run())
