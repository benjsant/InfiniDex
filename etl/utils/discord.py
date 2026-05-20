"""Discord webhook helper.

Single place for the constants and POST logic used by the Prefect watchers
to notify a Discord channel. Discord webhooks sit behind Cloudflare, which
403s requests carrying the default Python User-Agent (CF error 1010) — the
browser UA below gets through.
"""

from __future__ import annotations

import logging
import os

import requests

BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")


def post_message(content: str, *, logger: logging.Logger, label: str = "notification") -> None:
    """POST a content-only message to the Discord webhook.

    `label` is only used in log lines (e.g. "Discord <label> sent."). All
    failures (missing webhook, network error, non-2xx) are logged and
    swallowed — notification is best-effort.
    """
    if not WEBHOOK_URL:
        logger.info("DISCORD_WEBHOOK_URL not set — %s skipped.", label)
        return

    try:
        resp = requests.post(
            WEBHOOK_URL,
            json={"content": content},
            headers={"User-Agent": BROWSER_UA},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Discord %s sent.", label)
    except Exception as exc:
        logger.warning("Discord %s failed: %s", label, exc)
