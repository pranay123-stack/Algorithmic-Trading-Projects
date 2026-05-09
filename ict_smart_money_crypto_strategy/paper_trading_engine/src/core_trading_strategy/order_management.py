"""
Order Management Module
Handles order creation, validation, execution, and tracking
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class Order:
    """Order object"""

    def __init__(
        self,
        order_id: str,
        symbol: str,
        side: str,  # 'LONG' or 'SHORT'
        order_type: OrderType,
        size: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        take_profit_price: Optional[float] = None
    ):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        self.size = size
        self.price = price
        self.stop_price = stop_price
        self.take_profit_price = take_profit_price
        self.status = OrderStatus.PENDING
        self.filled_price = None
        self.filled_time = None
        self.commission = 0.0

    def to_dict(self) -> dict:
        """Convert order to dictionary"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side,
            'type': self.order_type.value,
            'size': self.size,
            'price': self.price,
            'stop_price': self.stop_price,
            'take_profit_price': self.take_profit_price,
            'status': self.status.value,
            'filled_price': self.filled_price,
            'filled_time': self.filled_time,
            'commission': self.commission
        }


class OrderManager:
    """
    Manages order lifecycle

    Features:
    - Order creation and validation
    - Simulated execution (paper trading)
    - Commission calculations
    - Order tracking and history
    """

    def __init__(
        self,
        commission_rate: float = 0.0004,  # 0.04% (Binance futures maker/taker avg)
        slippage_pct: float = 0.0005  # 0.05% slippage
    ):
        """
        Initialize order manager

        Args:
            commission_rate: Commission rate (0.0004 = 0.04%)
            slippage_pct: Slippage percentage (0.0005 = 0.05%)
        """
        self.commission_rate = commission_rate
        self.slippage_pct = slippage_pct
        self.orders = {}  # order_id -> Order
        self.order_counter = 0

    def create_order(
        self,
        symbol: str,
        side: str,
        size: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        take_profit_price: Optional[float] = None
    ) -> Order:
        """
        Create a new order

        Args:
            symbol: Trading symbol
            side: 'LONG' or 'SHORT'
            size: Order size in USD
            order_type: Order type
            price: Limit price (for limit orders)
            stop_price: Stop loss price
            take_profit_price: Take profit price

        Returns:
            Order object
        """
        # Validate inputs
        if size <= 0:
            raise ValueError(f"Invalid order size: {size}")

        if side not in ['LONG', 'SHORT']:
            raise ValueError(f"Invalid side: {side}")

        # Generate order ID
        self.order_counter += 1
        order_id = f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.order_counter}"

        # Create order
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            size=size,
            price=price,
            stop_price=stop_price,
            take_profit_price=take_profit_price
        )

        self.orders[order_id] = order
        logger.info(f"Order created: {order_id} - {side} {size} {symbol}")

        return order

    def execute_order(
        self,
        order: Order,
        current_price: float,
        timestamp: datetime = None
    ) -> bool:
        """
        Execute order (simulated for paper trading)

        Args:
            order: Order to execute
            current_price: Current market price
            timestamp: Execution timestamp

        Returns:
            True if executed, False otherwise
        """
        if order.status != OrderStatus.PENDING:
            logger.warning(f"Order {order.order_id} already {order.status.value}")
            return False

        # Apply slippage
        if order.side == 'LONG':
            execution_price = current_price * (1 + self.slippage_pct)
        else:  # SHORT
            execution_price = current_price * (1 - self.slippage_pct)

        # Calculate commission
        commission = order.size * self.commission_rate

        # Fill order
        order.status = OrderStatus.FILLED
        order.filled_price = execution_price
        order.filled_time = timestamp or datetime.now()
        order.commission = commission

        logger.info(
            f"Order executed: {order.order_id} - "
            f"{order.side} {order.size} @ {execution_price:.2f} "
            f"(commission: ${commission:.2f})"
        )

        return True

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled, False otherwise
        """
        if order_id not in self.orders:
            logger.warning(f"Order {order_id} not found")
            return False

        order = self.orders[order_id]

        if order.status != OrderStatus.PENDING:
            logger.warning(f"Cannot cancel order {order_id} - status: {order.status.value}")
            return False

        order.status = OrderStatus.CANCELLED
        logger.info(f"Order cancelled: {order_id}")

        return True

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)

    def get_pending_orders(self) -> list:
        """Get all pending orders"""
        return [o for o in self.orders.values() if o.status == OrderStatus.PENDING]

    def get_filled_orders(self) -> list:
        """Get all filled orders"""
        return [o for o in self.orders.values() if o.status == OrderStatus.FILLED]

    def get_order_history(self) -> list:
        """Get all orders (history)"""
        return [o.to_dict() for o in self.orders.values()]

    def calculate_total_commission(self) -> float:
        """Calculate total commission paid"""
        return sum(o.commission for o in self.orders.values() if o.status == OrderStatus.FILLED)

    def get_stats(self) -> dict:
        """Get order statistics"""
        filled_orders = self.get_filled_orders()

        return {
            'total_orders': len(self.orders),
            'pending_orders': len(self.get_pending_orders()),
            'filled_orders': len(filled_orders),
            'cancelled_orders': len([o for o in self.orders.values() if o.status == OrderStatus.CANCELLED]),
            'total_commission': self.calculate_total_commission(),
            'avg_commission_per_trade': self.calculate_total_commission() / len(filled_orders) if filled_orders else 0
        }
