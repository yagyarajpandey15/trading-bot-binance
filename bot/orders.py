from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from bot.client import BinanceFuturesClient
from bot.logging_config import get_logger

log = get_logger("orders")


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[int] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    orig_qty: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    price: Optional[str] = None
    stop_price: Optional[str] = None
    time_in_force: Optional[str] = None
    raw: dict = field(default_factory=dict)
    error: Optional[str] = None

    @classmethod
    def from_response(cls, data):
        return cls(
            success=True,
            order_id=data.get("orderId"),
            symbol=data.get("symbol"),
            side=data.get("side"),
            order_type=data.get("type"),
            status=data.get("status"),
            orig_qty=data.get("origQty"),
            executed_qty=data.get("executedQty"),
            avg_price=data.get("avgPrice") or data.get("price"),
            price=data.get("price"),
            stop_price=data.get("stopPrice"),
            time_in_force=data.get("timeInForce"),
            raw=data,
        )

    @classmethod
    def from_error(cls, msg):
        return cls(success=False, error=msg)

    def display_rows(self):
        """returns rows for the rich table in cli.py"""
        if not self.success:
            return [("Error", self.error or "unknown")]

        rows = [
            ("Order ID", str(self.order_id)),
            ("Symbol", self.symbol),
            ("Side", self.side),
            ("Type", self.order_type),
            ("Status", self.status),
            ("Qty", self.orig_qty),
            ("Executed", self.executed_qty),
        ]

        if self.order_type == "LIMIT":
            rows.append(("Limit Price", self.price))
            rows.append(("Avg Price", self.avg_price))
            rows.append(("TIF", self.time_in_force))
        elif self.order_type == "STOP_MARKET":
            rows.append(("Stop Price", self.stop_price))
        else:
            rows.append(("Avg Price", self.avg_price))

        return rows


class OrderService:
    def __init__(self, client: BinanceFuturesClient):
        self.client = client

    def place(self, symbol, side, order_type, quantity,
              price=None, stop_price=None, time_in_force="GTC"):

        # TODO: ideally fetch step size from exchangeInfo to format qty correctly
        qty_str = f"{quantity:.3f}"
        price_str = f"{price:.2f}" if price else None
        stop_str = f"{stop_price:.2f}" if stop_price else None

        log.info("order request: %s %s %s qty=%s", side, order_type, symbol, qty_str)

        try:
            raw = self.client.place_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=qty_str,
                price=price_str,
                stop_price=stop_str,
                time_in_force=time_in_force,
            )
            result = OrderResult.from_response(raw)
            log.info("done - orderId=%s status=%s", result.order_id, result.status)
            return result

        except Exception as e:
            log.error("order failed: %s", e, exc_info=True)
            return OrderResult.from_error(str(e))
