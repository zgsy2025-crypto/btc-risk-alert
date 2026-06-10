import os
import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")

BYBIT_BASE = "https://api.bybit.com"
STATE_FILE = "alert_state.json"

# GitHub Actions는 실행 후 종료되므로, 같은 실행 안에서만 중복 방지됩니다.
# 장기 쿨다운은 향후 GitHub artifact/cache 방식으로 개선 가능합니다.
COOLDOWN_SECONDS = 15 * 60

THRESHOLDS = {
    "move_5m_pct": 1.2,
    "move_15m_pct": 2.0,
    "move_60m_pct": 3.5,
    "volume_spike_mult": 2.5,
    "rsi_hot": 70,
    "rsi_cold": 30,
    "trend_risk_rsi": 45,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID가 비어 있습니다.")
        print(text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()


def bybit_kline(symbol: str, interval: str, limit: int = 200) -> List[Dict[str, float]]:
    """Bybit v5 public kline. Returns candles oldest -> newest."""
    url = f"{BYBIT_BASE}/v5/market/kline"
    params = {"category": "linear", "symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    if data.get("retCode") != 0:
        raise RuntimeError(f"Bybit error: {data}")

    rows = data["result"]["list"]
    candles = []
    for row in rows:
        candles.append({
            "ts": int(row[0]),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]),
            "turnover": float(row[6]),
        })
    return list(reversed(candles))


def pct_change(old: float, new: float) -> float:
    if old == 0:
        return 0.0
    return (new - old) / old * 100


def ema(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    result = sum(values[:period]) / period
    for v in values[period:]:
        result = v * k + result * (1 - k)
    return result


def rsi(values: List[float], period: int = 14) -> Optional[float]:
    if len(values) < period + 1:
        return None

    gains, losses = [], []
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = max(diff, 0)
        loss = abs(min(diff, 0))
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def fmt_price(x: float) -> str:
    return f"{x:,.1f}"


def make_alert(title: str, body: str, level: str = "⚠️") -> str:
    return (
        f"{level} <b>{title}</b>\n\n"
        f"{body}\n\n"
        f"시간: {now_utc()}\n"
        f"원칙: 이 알림은 진입 지시가 아니라 리스크 확인 신호입니다."
    )


def check_signals() -> List[tuple[str, str]]:
    candles_1m = bybit_kline(SYMBOL, "1", 120)
    candles_1h = bybit_kline(SYMBOL, "60", 220)

    closes_1m = [c["close"] for c in candles_1m]
    volumes_1m = [c["volume"] for c in candles_1m]
    closes_1h = [c["close"] for c in candles_1h]

    last = closes_1m[-1]
    alerts: List[tuple[str, str]] = []

    # 1) 급등락 감시
    windows = [(5, "move_5m_pct"), (15, "move_15m_pct"), (60, "move_60m_pct")]
    for minutes, key in windows:
        if len(closes_1m) > minutes:
            chg = pct_change(closes_1m[-minutes - 1], last)
            threshold = THRESHOLDS[key]
            if abs(chg) >= threshold:
                direction = "급등" if chg > 0 else "급락"
                title = f"BTC {minutes}분 {direction} 감지"
                body = (
                    f"현재가: <b>{fmt_price(last)} USDT</b>\n"
                    f"{minutes}분 변동률: <b>{chg:.2f}%</b>\n\n"
                    f"해석: 단기 변동성이 커졌습니다. 특히 선물 포지션은 손절가·청산가·포지션 크기를 먼저 확인하세요."
                )
                alerts.append((f"{key}_{'up' if chg > 0 else 'down'}", make_alert(title, body)))

    # 2) 거래량 폭증
    if len(volumes_1m) >= 25:
        avg20 = sum(volumes_1m[-21:-1]) / 20
        latest_vol = volumes_1m[-1]
        mult = latest_vol / avg20 if avg20 else 0
        if mult >= THRESHOLDS["volume_spike_mult"]:
            title = "BTC 1분봉 거래량 폭증"
            body = (
                f"현재가: <b>{fmt_price(last)} USDT</b>\n"
                f"최근 거래량: 평균 대비 <b>{mult:.1f}배</b>\n\n"
                f"해석: 큰 주문/청산/뉴스 반응 가능성이 있습니다. 방향 확정 전 추격 진입은 피하세요."
            )
            alerts.append(("volume_spike", make_alert(title, body)))

    # 3) RSI 과열/공포
    rsi_1h = rsi(closes_1h, 14)
    ema200_1h = ema(closes_1h, 200)

    if rsi_1h is not None:
        if rsi_1h >= THRESHOLDS["rsi_hot"]:
            title = "BTC 1시간 RSI 과열권"
            body = (
                f"현재가: <b>{fmt_price(last)} USDT</b>\n"
                f"1시간 RSI: <b>{rsi_1h:.1f}</b>\n\n"
                f"해석: 상승 추세가 강할 수 있지만, 신규 추격 매수는 손익비가 나빠질 수 있습니다."
            )
            alerts.append(("rsi_hot", make_alert(title, body, "🔥")))

        if rsi_1h <= THRESHOLDS["rsi_cold"]:
            title = "BTC 1시간 RSI 공포권 / 반등 관심"
            body = (
                f"현재가: <b>{fmt_price(last)} USDT</b>\n"
                f"1시간 RSI: <b>{rsi_1h:.1f}</b>\n\n"
                f"해석: 과매도권이지만 바로 매수 신호는 아닙니다. 거래량 회복과 지지 확인이 필요합니다."
            )
            alerts.append(("rsi_cold", make_alert(title, body, "🟡")))

    # 4) 1시간 EMA200 추세 위험
    if ema200_1h is not None and rsi_1h is not None:
        if last < ema200_1h and rsi_1h < THRESHOLDS["trend_risk_rsi"]:
            title = "BTC 중기 추세 위험 신호"
            body = (
                f"현재가: <b>{fmt_price(last)} USDT</b>\n"
                f"1시간 EMA200: <b>{fmt_price(ema200_1h)} USDT</b>\n"
                f"1시간 RSI: <b>{rsi_1h:.1f}</b>\n\n"
                f"해석: 가격이 중기 기준선 아래에 있고 모멘텀도 약합니다. 롱 포지션은 보수적으로 관리하세요."
            )
            alerts.append(("trend_risk", make_alert(title, body, "🚨")))

    return alerts


def main() -> None:
    print(f"Running BTC risk check for {SYMBOL}")

    try:
        send_telegram("✅ BTC Risk Alert 테스트 성공! GitHub Actions와 Telegram 연결 정상")
        
        alerts = check_signals()

        if not alerts:
            print("No alert signals.")
            return

        sent_keys = set()
        for key, msg in alerts:
            # 같은 실행 안에서 같은 key 중복만 방지
            if key in sent_keys:
                continue
            send_telegram(msg)
            sent_keys.add(key)
            print(f"Sent alert: {key}")

    except Exception as e:
        err = make_alert(
            "봇 오류 발생",
            f"오류 내용: <code>{str(e)}</code>",
            "⚠️"
        )
        print(err)
        try:
            send_telegram(err)
        except Exception:
            pass


if __name__ == "__main__":
    main()
