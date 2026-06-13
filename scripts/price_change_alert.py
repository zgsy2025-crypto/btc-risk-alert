#!/usr/bin/env python3
"""
Step 5: BTC price-change risk alert.

This is not a trading bot. It only sends risk-management warnings.
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request


COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"


def get_env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def fetch_market_data(currency: str) -> tuple[list[list[float]], list[list[float]]]:
    query = urllib.parse.urlencode({"vs_currency": currency, "days": "1"})
    request = urllib.request.Request(
        f"{COINGECKO_URL}?{query}",
        headers={"User-Agent": "btc-risk-alert/price-change"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    prices = data.get("prices", [])
    if len(prices) < 20:
        raise RuntimeError(f"Not enough price data: {len(prices)}")
    volumes = data.get("total_volumes", [])
    if len(volumes) < 20:
        raise RuntimeError(f"Not enough volume data: {len(volumes)}")
    return prices, volumes


def price_before(prices: list[list[float]], target_ms: float) -> float:
    selected = prices[0][1]
    for timestamp_ms, price in prices:
        if timestamp_ms <= target_ms:
            selected = price
        else:
            break
    return float(selected)


def percent_change(old: float, new: float) -> float:
    return ((new - old) / old) * 100


def volume_ratio(volumes: list[list[float]], lookback_points: int = 12) -> float:
    if len(volumes) <= lookback_points:
        raise RuntimeError(f"Not enough volume points: {len(volumes)}")

    latest_volume = float(volumes[-1][1])
    previous_volumes = [float(point[1]) for point in volumes[-lookback_points - 1 : -1]]
    average_volume = sum(previous_volumes) / len(previous_volumes)
    if average_volume == 0:
        raise RuntimeError("Average volume is zero.")
    return latest_volume / average_volume


def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    if not chat_id:
        raise RuntimeError("Missing TELEGRAM_CHAT_ID")

    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        TELEGRAM_URL.format(token=token),
        data=body,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("ok") is not True:
        raise RuntimeError(f"Telegram send failed: {result}")


def main() -> int:
    currency = os.getenv("BTC_ALERT_CURRENCY", "usd")
