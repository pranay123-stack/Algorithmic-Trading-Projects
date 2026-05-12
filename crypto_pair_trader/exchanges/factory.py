"""Factory for exchange client creation."""

from config import Config
from .base import ExchangeClient


def create_exchange(cfg: Config | None = None) -> ExchangeClient:
    if cfg is None:
        cfg = Config.load()
    return ExchangeClient(cfg)
