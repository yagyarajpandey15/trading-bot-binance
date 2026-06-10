from decimal import Decimal, InvalidOperation

VALID_SIDES = {"BUY", "SELL"}
VALID_TYPES = {"MARKET", "LIMIT", "STOP", "STOP_MARKET", "TAKE_PROFIT_MARKET"}


def validate_symbol(symbol):
    if not symbol or not isinstance(symbol, str):
        raise ValueError("symbol can't be empty")
    cleaned = symbol.strip().upper()
    if not cleaned.isalnum():
        raise ValueError(f"symbol should be like BTCUSDT, got: {symbol!r}")
    return cleaned


def validate_side(side):
    val = side.strip().upper()
    if val not in VALID_SIDES:
        raise ValueError(f"side must be BUY or SELL, got: {side!r}")
    return val


def validate_order_type(order_type):
    val = order_type.strip().upper()
    if val not in VALID_TYPES:
        raise ValueError(f"type must be MARKET, LIMIT, STOP, STOP_MARKET, or TAKE_PROFIT_MARKET, got: {order_type!r}")
    return val


def validate_quantity(qty):
    try:
        val = Decimal(str(qty))
    except InvalidOperation:
        raise ValueError(f"quantity must be a number, got: {qty!r}")
    if val <= 0:
        raise ValueError("quantity must be greater than 0")
    if val < Decimal("0.001"):
        raise ValueError("quantity too small, minimum is 0.001")
    return val


def validate_price(price, order_type):
    if order_type == "MARKET":
        if price is not None:
            raise ValueError("don't pass a price for MARKET orders")
        return None

    if order_type in ("STOP_MARKET", "TAKE_PROFIT_MARKET"):
        # limit price doesn't apply here, stop_price is separate
        return None

    # LIMIT and STOP need a price
    if order_type in ("LIMIT", "STOP"):
        if price is None:
            raise ValueError(f"price is required for {order_type} orders")
        try:
            val = Decimal(str(price))
        except InvalidOperation:
            raise ValueError(f"price must be a number, got: {price!r}")
        if val <= 0:
            raise ValueError("price must be greater than 0")
        return val
    
    return None


def validate_stop_price(stop_price, order_type):
    if order_type not in ("STOP_MARKET", "STOP", "TAKE_PROFIT_MARKET"):
        return None
    if stop_price is None:
        raise ValueError(f"stop_price is required for {order_type} orders")
    try:
        val = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"stop_price must be a number, got: {stop_price!r}")
    if val <= 0:
        raise ValueError("stop_price must be greater than 0")
    return val


def validate_all(symbol, side, order_type, quantity, price=None, stop_price=None):
    """runs all checks and returns cleaned values as a dict"""
    otype = validate_order_type(order_type)
    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": otype,
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, otype),
        "stop_price": validate_stop_price(stop_price, otype),
    }
