import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from bot.client import BinanceAPIError
from bot.orders import OrderResult, OrderService


MARKET_RESP = {
    "orderId": 123456,
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "status": "FILLED",
    "origQty": "0.010",
    "executedQty": "0.010",
    "avgPrice": "104823.50",
    "price": "0",
    "timeInForce": "GTC",
    "reduceOnly": False,
}

LIMIT_RESP = {
    "orderId": 789012,
    "symbol": "BTCUSDT",
    "side": "SELL",
    "type": "LIMIT",
    "status": "NEW",
    "origQty": "0.010",
    "executedQty": "0.000",
    "avgPrice": "0",
    "price": "120000.00",
    "timeInForce": "GTC",
    "reduceOnly": False,
}

STOP_RESP = {
    "orderId": 345678,
    "symbol": "BTCUSDT",
    "side": "SELL",
    "type": "STOP_MARKET",
    "status": "NEW",
    "origQty": "0.010",
    "executedQty": "0.000",
    "avgPrice": "0",
    "stopPrice": "95000.00",
    "reduceOnly": False,
}


def make_service(mock_resp):
    client = MagicMock()
    client.place_order.return_value = mock_resp
    return OrderService(client), client


# OrderResult tests

def test_result_from_market_response():
    r = OrderResult.from_response(MARKET_RESP)
    assert r.success is True
    assert r.order_id == 123456
    assert r.status == "FILLED"
    assert r.side == "BUY"

def test_result_from_limit_response():
    r = OrderResult.from_response(LIMIT_RESP)
    assert r.order_type == "LIMIT"
    assert r.price == "120000.00"

def test_result_from_stop_response():
    r = OrderResult.from_response(STOP_RESP)
    assert r.stop_price == "95000.00"

def test_result_from_error():
    r = OrderResult.from_error("something broke")
    assert r.success is False
    assert r.error == "something broke"
    assert r.order_id is None

def test_display_rows_has_order_id():
    r = OrderResult.from_response(MARKET_RESP)
    labels = [row[0] for row in r.display_rows()]
    assert "Order ID" in labels
    assert "Status" in labels

def test_display_rows_error():
    r = OrderResult.from_error("network error")
    rows = r.display_rows()
    assert rows[0][0] == "Error"


# OrderService tests

def test_market_order_calls_client_correctly():
    service, client = make_service(MARKET_RESP)
    result = service.place(
        symbol="BTCUSDT", side="BUY",
        order_type="MARKET", quantity=Decimal("0.01")
    )
    assert result.success is True
    assert result.order_id == 123456
    client.place_order.assert_called_once_with(
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        quantity="0.010",
        price=None,
        stop_price=None,
        time_in_force="GTC",
    )

def test_limit_order_passes_price():
    service, client = make_service(LIMIT_RESP)
    service.place(
        symbol="BTCUSDT", side="SELL",
        order_type="LIMIT", quantity=Decimal("0.01"),
        price=Decimal("120000")
    )
    _, kwargs = client.place_order.call_args
    assert kwargs["price"] == "120000.00"

def test_stop_market_passes_stop_price():
    service, client = make_service(STOP_RESP)
    service.place(
        symbol="BTCUSDT", side="SELL",
        order_type="STOP_MARKET", quantity=Decimal("0.01"),
        stop_price=Decimal("95000")
    )
    _, kwargs = client.place_order.call_args
    assert kwargs["stop_price"] == "95000.00"

def test_api_error_returns_failed_result():
    client = MagicMock()
    client.place_order.side_effect = BinanceAPIError(-2010, "insufficient balance")
    service = OrderService(client)
    result = service.place(
        symbol="BTCUSDT", side="BUY",
        order_type="MARKET", quantity=Decimal("0.01")
    )
    assert result.success is False
    assert "insufficient balance" in result.error

def test_connection_error_returns_failed_result():
    client = MagicMock()
    client.place_order.side_effect = ConnectionError("can't reach testnet")
    service = OrderService(client)
    result = service.place(
        symbol="BTCUSDT", side="BUY",
        order_type="MARKET", quantity=Decimal("0.01")
    )
    assert result.success is False
    assert "testnet" in result.error
