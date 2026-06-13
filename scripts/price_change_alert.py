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


def fetch_prices(currency: str) -> list[list[float]]:
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
    return prices


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
    notify_no_alert = get_env_bool("BTC_ALERT_NOTIFY_NO_ALERT", False)
    thresholds = {
        "5분": get_env_float("BTC_ALERT_THRESHOLD_5M", 1.5),
        "15분": get_env_float("BTC_ALERT_THRESHOLD_15M", 2.5),
        "1시간": get_env_float("BTC_ALERT_THRESHOLD_1H", 4.0),
    }
    windows_ms = {
        "5분": 5 * 60 * 1000,
        "15분": 15 * 60 * 1000,
        "1시간": 60 * 60 * 1000,
    }

    print("[price-change] started", flush=True)
    prices = fetch_prices(currency)
    latest_ts, latest_price = prices[-1]
    latest_price = float(latest_price)

    warnings = []
    for label, window_ms in windows_ms.items():
        old_price = price_before(prices, latest_ts - window_ms)
        change = percent_change(old_price, latest_price)
        print(f"[price-change] {label} change={change:.2f}%", flush=True)
        if abs(change) >= thresholds[label]:
            move = "급등" if change > 0 else "급락"
            warnings.append(f"{label} {change:+.2f}% {move}")

    price_text = f"{latest_price:,.2f} {currency.upper()}"
    if warnings:
        message = (
            "BTC 위험 경고\n\n"
            f"현재 가격:\n{price_text}\n\n"
            "현재 상황:\n"
            + "\n".join(f"- {line}" for line in warnings)
            + "\n\n주의 사항:\n"
            "- 충동 진입 금지\n"
            "- 높은 레버리지 진입 금지\n"
            "- 손절 계획 없는 물타기 금지\n\n"
            "이 알림은 매수/매도 신호가 아니라 리스크 관리 경고입니다."
        )
        send_telegram(message)
        print("[price-change] result=success alert_sent=true", flush=True)
        return 0

    print("[price-change] result=success alert_sent=false", flush=True)
    if notify_no_alert:
        send_telegram(
            "BTC 위험 관리 점검 완료\n\n"
            f"현재 가격: {price_text}\n"
            "현재 가격 급등락 기준을 넘지 않았습니다.\n\n"
            "이 메시지는 매수/매도 신호가 아닙니다."
        )
        print("[price-change] no_alert_message_sent=true", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
