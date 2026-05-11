"""Live execution against Polymarket's CLOB API with Polygon signing.

Orders are signed using EIP-712 typed data and submitted via the REST
API.  Requires ``POLYBOT_PRIVATE_KEY`` environment variable.
"""

from __future__ import annotations

import os
import time
from typing import Any

from polybot.data.client import PolymarketClient
from polybot.execution.base import BaseExecutor
from polybot.telemetry import get_logger
from polybot.types import (
    Fill,
    Order,
    OrderStatus,
    Position,
    Side,
)

logger = get_logger(__name__)


class LiveExecutor(BaseExecutor):
    """Polymarket CLOB execution with EIP-712 Polygon signing.

    This executor signs limit orders using an Ethereum-compatible wallet
    and submits them to the Polymarket CLOB REST API.

    **Required environment:**

    - ``POLYBOT_PRIVATE_KEY``: Hex-encoded private key for the Polygon wallet

    **Dependencies:**

    - ``web3`` for Polygon RPC
    - ``eth_account`` for EIP-712 signing
    """

    def __init__(
        self,
        client: PolymarketClient,
        *,
        chain_id: int = 137,
        polygon_rpc_url: str = "https://polygon-rpc.com",
    ) -> None:
        super().__init__()
        self._client = client
        self._chain_id = chain_id
        self._rpc_url = polygon_rpc_url
        self._private_key: str = ""
        self._address: str = ""
        self._web3: Any = None
        self._account: Any = None

    async def __aenter__(self) -> "LiveExecutor":
        self._private_key = os.environ.get("POLYBOT_PRIVATE_KEY", "")
        if not self._private_key:
            raise RuntimeError(
                "POLYBOT_PRIVATE_KEY environment variable is required for live mode"
            )

        try:
            from eth_account import Account
            from web3 import Web3

            self._web3 = Web3(Web3.HTTPProvider(self._rpc_url))
            self._account = Account.from_key(self._private_key)
            self._address = self._account.address
            logger.info("live_executor_ready", address=self._address)
        except ImportError as exc:
            raise RuntimeError(
                "web3 and eth-account packages are required for live mode: "
                "pip install web3 eth-account"
            ) from exc

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        count = await self.cancel_all()
        if count:
            logger.info("shutdown_cancelled_orders", count=count)

    # ------------------------------------------------------------------
    # BaseExecutor interface
    # ------------------------------------------------------------------

    async def place_order(self, order: Order) -> Order:
        payload = self._build_order_payload(order)
        signed = self._sign_order(payload)

        try:
            result = await self._client.post_order(
                signed,
                headers=self._auth_headers(),
            )
            order.status = OrderStatus.OPEN
            logger.info(
                "live_order_placed",
                order_id=order.client_order_id,
                exchange_id=result.get("id"),
            )
        except Exception as exc:
            order.status = OrderStatus.REJECTED
            logger.error("live_order_failed", order_id=order.client_order_id, error=str(exc))

        self._emit_event("order_placed", {"order_id": order.client_order_id, "status": order.status.name})
        return order

    async def cancel_order(self, client_order_id: str) -> bool:
        return await self._client.cancel_order(
            client_order_id,
            headers=self._auth_headers(),
        )

    async def get_order(self, client_order_id: str) -> Order | None:
        try:
            data = await self._client.get_order(
                client_order_id,
                headers=self._auth_headers(),
            )
            return self._parse_order(data)
        except Exception:
            return None

    async def get_open_orders(self) -> list[Order]:
        data = await self._client.get_open_orders(headers=self._auth_headers())
        return [self._parse_order(o) for o in data]

    async def cancel_all(self) -> int:
        orders = await self.get_open_orders()
        cancelled = 0
        for order in orders:
            if await self.cancel_order(order.client_order_id):
                cancelled += 1
        return cancelled

    async def get_positions(self) -> list[Position]:
        # In production, query on-chain token balances via web3
        logger.debug("get_positions_not_fully_implemented")
        return []

    async def get_balance(self) -> float:
        """Query USDC balance on Polygon."""
        if self._web3 is None:
            return 0.0

        # USDC contract on Polygon mainnet
        usdc_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
        # Minimal ERC-20 ABI for balanceOf
        abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function",
            }
        ]

        try:
            contract = self._web3.eth.contract(
                address=self._web3.to_checksum_address(usdc_address),
                abi=abi,
            )
            raw_balance = contract.functions.balanceOf(self._address).call()
            return raw_balance / 1e6  # USDC has 6 decimals
        except Exception as exc:
            logger.error("balance_query_failed", error=str(exc))
            return 0.0

    # ------------------------------------------------------------------
    # EIP-712 signing
    # ------------------------------------------------------------------

    def _build_order_payload(self, order: Order) -> dict[str, Any]:
        """Convert an Order to the Polymarket CLOB API format."""
        return {
            "tokenID": order.token_id,
            "price": str(order.price),
            "size": str(order.size),
            "side": "BUY" if order.side == Side.BUY else "SELL",
            "feeRateBps": "0",
            "nonce": str(int(time.time() * 1000)),
            "expiration": "0",  # no expiration
        }

    def _sign_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sign the order payload using EIP-712 typed data.

        Polymarket uses a custom EIP-712 domain and order struct for
        on-chain settlement on the CTF Exchange contract.
        """
        if self._account is None:
            raise RuntimeError("Executor not initialised (missing __aenter__)")

        from eth_account.messages import encode_structured_data

        # EIP-712 domain for Polymarket CTF Exchange
        domain = {
            "name": "Polymarket CTF Exchange",
            "version": "1",
            "chainId": self._chain_id,
        }

        message = {
            "tokenId": payload["tokenID"],
            "price": payload["price"],
            "size": payload["size"],
            "side": payload["side"],
            "feeRateBps": payload["feeRateBps"],
            "nonce": payload["nonce"],
            "expiration": payload["expiration"],
            "maker": self._address,
        }

        structured_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                ],
                "Order": [
                    {"name": "tokenId", "type": "string"},
                    {"name": "price", "type": "string"},
                    {"name": "size", "type": "string"},
                    {"name": "side", "type": "string"},
                    {"name": "feeRateBps", "type": "string"},
                    {"name": "nonce", "type": "string"},
                    {"name": "expiration", "type": "string"},
                    {"name": "maker", "type": "address"},
                ],
            },
            "primaryType": "Order",
            "domain": domain,
            "message": message,
        }

        encoded = encode_structured_data(structured_data)
        signed = self._account.sign_message(encoded)

        return {
            "order": payload,
            "signature": signed.signature.hex(),
            "owner": self._address,
        }

    def _auth_headers(self) -> dict[str, str]:
        """Build authentication headers for the CLOB API."""
        return {
            "POLY_ADDRESS": self._address,
            "POLY_SIGNATURE": "",  # simplified; real impl uses API key auth
        }

    @staticmethod
    def _parse_order(data: dict[str, Any]) -> Order:
        """Parse a CLOB API order response into a domain Order."""
        status_map = {
            "ACTIVE": OrderStatus.OPEN,
            "FILLED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
        }
        return Order(
            client_order_id=data.get("id", ""),
            market_id=data.get("market", ""),
            token_id=data.get("tokenID", data.get("asset_id", "")),
            side=Side.BUY if data.get("side") == "BUY" else Side.SELL,
            price=float(data.get("price", 0)),
            size=float(data.get("size", data.get("original_size", 0))),
            status=status_map.get(data.get("status", ""), OrderStatus.PENDING),
        )
