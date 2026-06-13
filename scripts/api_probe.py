#!/usr/bin/env python3
"""
Step 2 probe: verify that GitHub Actions can access BTC market data.

This is not a trading bot and does not send buy/sell advice.
It only checks whether a data provider returns enough BTC data for risk alerts.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


COINGECKO_MARKET_CHART_URL = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"


def fetch_json(url: str, params: dict[str, str], timeout: int = 30) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": "btc-risk-alert-api-probe/0.1",
        },
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.status
        body = response.read().decode("utf-8")

    if status != 200:
        raise RuntimeError(f"HTTP {status}: {body[:300]}")

    return json.loads(body)


def percent_change(old: float, new: float) -> float:
    if old == 0:
        raise ValueError("Cannot calculate percent change from zero.")
    return ((new - old) / old) * 100


def main() -> int:
    started = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    print(f"[probe] started_at={started}")
    print("[probe] provider=CoinGecko")
    print("[probe] endpoint=/coins/bitcoin/market_chart?vs_currency=usd&days=1")

    try:
        data = fetch_json(
            COINGECKO_MARKET_CHART_URL,
            {
                "vs_currency": "usd",
                "days": "1",
            },
        )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        print(f"[probe] result=fail http_status={exc.code}")
        print(f"[probe] response={body}")
        return 1
    except Exception as exc:
        print(f"[probe] result=fail error={exc}")
        return 1

    prices = data.get("prices", [])
    volumes = data.get("total_volumes", [])

    if len(prices) < 200:
        print(f"[probe] result=fail reason=not_enough_price_points count={len(prices)}")
        return 1
    if len(volumes) < 20:
        print(f"[probe] result=fail reason=not_enough_volume_points count={len(volumes)}")
        return 1

    latest_ts, latest_price = prices[-1]
    first_ts, first_price = prices[0]
    latest_volume = volumes[-1][1]
    day_change = percent_change(float(first_price), float(latest_price))

    print("[probe] result=success")
    print(f"[probe] price_points={len(prices)}")
    print(f"[probe] volume_points={len(volumes)}")
    print(f"[probe] first_timestamp_ms={first_ts}")
    print(f"[probe] latest_timestamp_ms={latest_ts}")
    print(f"[probe] latest_btc_usd={float(latest_price):,.2f}")
    print(f"[probe] latest_total_volume_usd={float(latest_volume):,.2f}")
    print(f"[probe] approx_24h_change_percent={day_change:.2f}")
    print("[probe] next_gate=If this succeeds in GitHub Actions, continue to Telegram test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
