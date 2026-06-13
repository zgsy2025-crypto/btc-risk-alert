#!/usr/bin/env python3
"""
BTC price and volume risk alert.

This is not a trading bot. It only sends risk-management warnings.
"""

import json
import os
import urllib.parse
import urllib.request


COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"


def env_float(name, default):
    value = os.getenv(name)
    return default if value in (None, "") else float(value)


def env_bool(name, default=False):
    value = os.getenv(name)
    return default if value is None else value.lower() == "true"


def fetch_market_data(currency):
    query = urllib.parse.urlencode({"vs_currency": currency, "days": "1"})
    request = urllib.request.Request(
        f"{COINGECKO_URL}?{query}",
        headers={"User-Agent": "btc-risk-alert"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    prices = data.get("prices", [])
    volumes = data.get("total_volumes", [])
    if len(prices) < 20:
        raise RuntimeError(f"Not enough price data: {len(prices)}")
    if len(volumes) < 20:
        raise RuntimeError(f"Not enough volume data: {len(volumes)}")
    return prices, volumes


def price_before(prices, target_timestamp):
    selected_price = prices[0][1]
    for timestamp, price in prices:
        if timestamp <= target_timestamp:
            selected_price = price
        else:
            break
    return float(selected_price)


def percent_change(old_price, new_price):
    return ((new_price - old_price) / old_price) * 100


def latest_volume_ratio(volumes):
    latest_volume = float(volumes[-1][1])
    recent_volumes = [float(point[1]) for point in volumes[-13:-1]]
    average_volume = sum(recent_volumes) / len(recent_volumes)
    return latest_volume / average_volume


def calculate_rsi(prices, period=14):
    close_prices = [float(point[1]) for point in prices]
    if len(close_prices) <= period:
        raise RuntimeError(f"Not enough price data for RSI: {len(close_prices)}")

    changes = [
        close_prices[index] - close_prices[index - 1]
        for index in range(len(close_prices) - period, len(close_prices))
    ]
    gains = [change for change in changes if change > 0]
    losses = [-change for change in changes if change < 0]
    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def calculate_ema(prices, period=200):
    close_prices = [float(point[1]) for point in prices]
    if len(close_prices) < period:
        raise RuntimeError(f"Not enough price data for EMA{period}: {len(close_prices)}")

    ema = sum(close_prices[:period]) / period
    multiplier = 2 / (period + 1)
    for price in close_prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    if not chat_id:
        raise RuntimeError("Missing TELEGRAM_CHAT_ID")

    body = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = urllib.request.Request(
        TELEGRAM_URL.format(token=token),
        data=body,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("ok") is not True:
        raise RuntimeError(f"Telegram send failed: {result}")


def main():
    print("[price-change] started", flush=True)

    currency = os.getenv("BTC_ALERT_CURRENCY", "usd")
    notify_no_alert = env_bool("BTC_ALERT_NOTIFY_NO_ALERT", False)
    volume_threshold = env_float("BTC_ALERT_VOLUME_MULTIPLIER", 3.0)
    rsi_overbought = env_float("BTC_ALERT_RSI_OVERBOUGHT", 70.0)
    rsi_oversold = env_float("BTC_ALERT_RSI_OVERSOLD", 30.0)
    thresholds = {
        "5분": env_float("BTC_ALERT_THRESHOLD_5M", 1.5),
        "15분": env_float("BTC_ALERT_THRESHOLD_15M", 2.5),
        "1시간": env_float("BTC_ALERT_THRESHOLD_1H", 4.0),
    }
    windows = {"5분": 5 * 60 * 1000, "15분": 15 * 60 * 1000, "1시간": 60 * 60 * 1000}

    prices, volumes = fetch_market_data(currency)
    latest_timestamp, latest_price = prices[-1]
    latest_price = float(latest_price)

    risk_lines = []
    status_lines = []
    for label, window in windows.items():
        old_price = price_before(prices, latest_timestamp - window)
        change = percent_change(old_price, latest_price)
        print(f"[price-change] {label} change={change:.2f}%", flush=True)
        if abs(change) >= thresholds[label]:
            move = "급등" if change > 0 else "급락"
            line = f"{label} {change:+.2f}% {move}"
            risk_lines.append(line)
            status_lines.append(line)

    volume_ratio = latest_volume_ratio(volumes)
    print(f"[price-change] volume_ratio={volume_ratio:.2f}x", flush=True)
    volume_line = f"거래량 점검: 최근 평균 대비 {volume_ratio:.2f}배 (기준 {volume_threshold:.2f}배)"
    if volume_ratio >= volume_threshold:
        risk_lines.append(f"{volume_line} - 이상 증가 감지")
        status_lines.append(f"{volume_line} - 이상 증가 감지")
    else:
        status_lines.append(f"{volume_line} - 기준 미만")

    rsi = calculate_rsi(prices)
    print(f"[price-change] rsi14={rsi:.2f}", flush=True)
    rsi_line = f"RSI 14 점검: {rsi:.2f} (주의 기준 {rsi_oversold:.0f} 이하 또는 {rsi_overbought:.0f} 이상)"
    if rsi >= rsi_overbought:
        risk_lines.append(f"{rsi_line} - 과열 구간 주의")
        status_lines.append(f"{rsi_line} - 과열 구간 주의")
    elif rsi <= rsi_oversold:
        risk_lines.append(f"{rsi_line} - 급격한 약세/공포 구간 주의")
        status_lines.append(f"{rsi_line} - 급격한 약세/공포 구간 주의")
    else:
        status_lines.append(f"{rsi_line} - 기준 범위")

    ema200 = calculate_ema(prices)
    print(f"[price-change] ema200={ema200:.2f}", flush=True)
    ema_line = f"EMA200 점검: {ema200:,.2f} {currency.upper()}"
    if latest_price < ema200:
        risk_lines.append(f"{ema_line} - 현재가가 EMA200 아래")
        status_lines.append(f"{ema_line} - 현재가가 EMA200 아래")
    else:
        status_lines.append(f"{ema_line} - 현재가가 EMA200 위")

    if not status_lines:
        status_lines.append("가격 급등락 기준 초과 없음")

    price_text = f"{latest_price:,.2f} {currency.upper()}"
    title = "BTC 위험 경고" if risk_lines else "BTC 위험 관리 점검 완료"
    message = (
        f"{title}\n\n"
        f"현재 가격:\n{price_text}\n\n"
        "현재 상황:\n"
        + "\n".join(f"- {line}" for line in status_lines)
        + "\n\n주의 사항:\n"
        "- 충동 진입 금지\n"
        "- 높은 레버리지 진입 금지\n"
        "- 손절 계획 없는 물타기 금지\n\n"
        "이 알림은 매수/매도 신호가 아니라 리스크 관리 경고입니다."
    )

    if risk_lines or notify_no_alert:
        send_telegram(message)
        print("[price-change] telegram_sent=true", flush=True)
    else:
        print("[price-change] telegram_sent=false", flush=True)

    print("[price-change] result=success", flush=True)


if __name__ == "__main__":
    main()
