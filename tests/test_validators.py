import pytest
from decimal import Decimal
from bot.validators import (
    validate_symbol, validate_side, validate_order_type,
    validate_quantity, validate_price, validate_stop_price, validate_all
)


# symbol tests

def test_symbol_uppercased():
    assert validate_symbol("btcusdt") == "BTCUSDT"

def test_symbol_strips_spaces():
    assert validate_symbol("  ETHUSDT  ") == "ETHUSDT"

def test_symbol_empty_raises():
    with pytest.raises(ValueError):
        validate_symbol("")

def test_symbol_with_slash_raises():
    with pytest.raises(ValueError):
        validate_symbol("BTC/USDT")

def test_symbol_none_raises():
    with pytest.raises((ValueError, AttributeError)):
        validate_symbol(None)


# side tests

def test_side_buy():
    assert validate_side("BUY") == "BUY"

def test_side_sell():
    assert validate_side("sell") == "SELL"

def test_side_invalid():
    with pytest.raises(ValueError, match="BUY or SELL"):
        validate_side("LONG")

def test_side_empty():
    with pytest.raises(ValueError):
        validate_side("")


# order type tests

def test_type_market():
    assert validate_order_type("market") == "MARKET"

def test_type_limit():
    assert validate_order_type("LIMIT") == "LIMIT"

def test_type_stop_market():
    assert validate_order_type("stop_market") == "STOP_MARKET"

def test_type_invalid():
    with pytest.raises(ValueError):
        validate_order_type("OCO")


# quantity tests

def test_qty_valid():
    assert validate_quantity("0.01") == Decimal("0.01")

def test_qty_zero_raises():
    with pytest.raises(ValueError, match="greater than 0"):
        validate_quantity("0")

def test_qty_negative_raises():
    with pytest.raises(ValueError):
        validate_quantity("-5")

def test_qty_too_small_raises():
    with pytest.raises(ValueError, match="0.001"):
        validate_quantity("0.0001")

def test_qty_string_raises():
    with pytest.raises(ValueError):
        validate_quantity("abc")


# price tests

def test_price_not_needed_for_market():
    assert validate_price(None, "MARKET") is None

def test_price_given_for_market_raises():
    with pytest.raises(ValueError):
        validate_price("50000", "MARKET")

def test_price_required_for_limit():
    with pytest.raises(ValueError, match="required for LIMIT"):
        validate_price(None, "LIMIT")

def test_price_valid_for_limit():
    assert validate_price("50000", "LIMIT") == Decimal("50000")

def test_price_zero_raises():
    with pytest.raises(ValueError):
        validate_price("0", "LIMIT")

def test_stop_market_ignores_price():
    # stop_market doesn't use limit price
    assert validate_price(None, "STOP_MARKET") is None


# stop price tests

def test_stop_price_ignored_for_market():
    assert validate_stop_price("90000", "MARKET") is None

def test_stop_price_ignored_for_limit():
    assert validate_stop_price("90000", "LIMIT") is None

def test_stop_price_required_for_stop_market():
    with pytest.raises(ValueError, match="required"):
        validate_stop_price(None, "STOP_MARKET")

def test_stop_price_valid():
    assert validate_stop_price("95000", "STOP_MARKET") == Decimal("95000")

def test_stop_price_zero_raises():
    with pytest.raises(ValueError):
        validate_stop_price("0", "STOP_MARKET")


# validate_all integration tests

def test_validate_all_market():
    result = validate_all(
        symbol="btcusdt", side="buy",
        order_type="market", quantity="0.01"
    )
    assert result["symbol"] == "BTCUSDT"
    assert result["side"] == "BUY"
    assert result["order_type"] == "MARKET"
    assert result["price"] is None
    assert result["stop_price"] is None

def test_validate_all_limit():
    result = validate_all(
        symbol="ETHUSDT", side="SELL",
        order_type="LIMIT", quantity="1.0", price="3500"
    )
    assert result["price"] == Decimal("3500")

def test_validate_all_stop_market():
    result = validate_all(
        symbol="BTCUSDT", side="SELL",
        order_type="STOP_MARKET", quantity="0.01", stop_price="95000"
    )
    assert result["stop_price"] == Decimal("95000")

def test_validate_all_limit_no_price_raises():
    with pytest.raises(ValueError):
        validate_all(
            symbol="BTCUSDT", side="BUY",
            order_type="LIMIT", quantity="0.01"
        )
