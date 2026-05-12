from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Kalshi
    KALSHI_BASE_URL = "https://api.kalshi.com/trade-api/v2"

    # Polymarket
    POLY_GAMMA_URL = "https://gamma-api.polymarket.com"
    POLY_CLOB_URL = "https://clob.polymarket.com"

    # Alerting
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")
    ALERT_CHANNELS: list[str] = [
        ch.strip()
        for ch in os.getenv("ALERT_CHANNELS", "telegram").split(",")
        if ch.strip()
    ]

    # Thresholds
    MIN_ARB_SPREAD: float = float(os.getenv("MIN_ARB_SPREAD", "1.0"))
    MATCH_THRESHOLD: float = float(os.getenv("MATCH_THRESHOLD", "0.82"))

    # Polling
    POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "30"))

    # Embedding model
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
