#!/usr/bin/env python3
"""
Step 5: detect BTC price-change risk and send a Telegram warning.

This is not a trading bot and does not send buy/sell advice.
It only warns about rapid price movement for personal risk management.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


COINGECKO_MARKET_CHART_URL = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
TELEGRAM_SEND_MESSAGE_URL = "https://api.telegram.org/bot{token}/sendMessage"


WINDOWS = {
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
}


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def fetch_json(url: str, params: dict[str, str], timeout: int = 30) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": "btc-risk-alert-price-change/0.1",
        },
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.status
        body = response.read().decode("utf-8")

    if status != 200:
        raise RuntimeError(f"HTTP {status}: {body[:300]}")

    return json.loads(body)


def fetch_btc_market_data(currency: str) -> list[list[float]]:
    data = fetch_json(
        COINGECKO_MARKET_CHART_URL,
        {
            "vs_currency": currency.lower(),
            "days": "1",
        },
    )
    prices = data.get("prices", [])
    if len(prices) < 200:
        raise RuntimeError(f"Not enough price points: {len(prices)}")
    return prices


def find_price_at_or_before(prices: list[list[float]], target_ts: float) -> list[float]:
    selected = prices[0]
    for point in prices:
        if point[0] <= target_ts:
            selected = point
        else:
            break
    return selected


def percent_change(old: float, new: float) -> float:
    if old == 0:
        raise ValueError("Cannot calculate percent change from zero.")
    return ((new - old) / old) * 100


def format_price(price: float, currency: str) -> str:
    if currency.lower() == "usd":
        return f"{price:,.2f} USD"
    return f"{price:,.2f} {currency.upper()}"
