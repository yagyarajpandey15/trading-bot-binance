import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

log = get_logger("client")

BASE_URL = "https://testnet.binancefuture.com"
TIMEOUT = 10


class BinanceAPIError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"Binance error {code}: {message}")


class BinanceFuturesClient:
    def __init__(self, api_key, api_secret, base_url=BASE_URL):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret are required")

        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")

        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

        log.debug("client ready, base_url=%s", self.base_url)

    def _sign(self, params):
        params["timestamp"] = int(time.time() * 1000)
        query = urlencode(params)
        sig = hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = sig
        return params

    def _get(self, path, params=None, signed=False):
        url = self.base_url + path
        params = dict(params or {})
        if signed:
            params = self._sign(params)

        log.debug("GET %s params=%s", path, {k: v for k, v in params.items() if k != "signature"})

        try:
            resp = self.session.get(url, params=params, timeout=TIMEOUT)
        except requests.ConnectionError as e:
            log.error("connection failed: %s", e)
            raise ConnectionError(f"can't reach testnet: {e}") from e
        except requests.Timeout:
            log.error("request timed out: GET %s", path)
            raise TimeoutError("request timed out")

        return self._parse(resp)

    def _post(self, path, params):
        url = self.base_url + path
        params = self._sign(dict(params))

        log.debug("POST %s params=%s", path, {k: v for k, v in params.items() if k != "signature"})

        try:
            resp = self.session.post(url, data=params, timeout=TIMEOUT)
        except requests.ConnectionError as e:
            log.error("connection failed: %s", e)
            raise ConnectionError(f"can't reach testnet: {e}") from e
        except requests.Timeout:
            log.error("request timed out: POST %s", path)
            raise TimeoutError("request timed out")

        return self._parse(resp)

    def _parse(self, resp):
        log.debug("response %d from %s", resp.status_code, resp.url)
        try:
            data = resp.json()
        except ValueError:
            log.error("non-json response: %s", resp.text[:200])
            resp.raise_for_status()
            raise

        if not resp.ok:
            code = data.get("code", resp.status_code)
            msg = data.get("msg", "unknown error")
            log.error("api error %s: %s", code, msg)
            raise BinanceAPIError(code, msg)

        return data

    def get_price(self, symbol):
        data = self._get("/fapi/v1/ticker/price", params={"symbol": symbol})
        log.info("price check %s = %s", symbol, data.get("price"))
        return data

    def get_account(self):
        return self._get("/fapi/v2/account", signed=True)

    def place_order(self, symbol, side, order_type, quantity,
                    price=None, stop_price=None, time_in_force="GTC"):
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            if not price:
                raise ValueError("price required for LIMIT")
            params["price"] = price
            params["timeInForce"] = time_in_force

        if order_type == "STOP":
            # STOP (STOP_LIMIT) requires both stopPrice and price
            if not stop_price:
                raise ValueError("stopPrice required for STOP")
            if not price:
                raise ValueError("price required for STOP")
            params["stopPrice"] = stop_price
            params["price"] = price
            params["timeInForce"] = time_in_force

        if order_type in ("STOP_MARKET", "TAKE_PROFIT_MARKET"):
            if not stop_price:
                raise ValueError(f"stopPrice required for {order_type}")
            params["stopPrice"] = stop_price
            params["closePosition"] = "false"

        log.info("placing %s %s %s qty=%s price=%s stop=%s",
                 side, order_type, symbol, quantity, price or "market", stop_price or "")

        resp = self._post("/fapi/v1/order", params)

        log.info("order placed - id=%s status=%s executedQty=%s",
                 resp.get("orderId"), resp.get("status"), resp.get("executedQty"))
        log.debug("full response: %s", resp)

        return resp
