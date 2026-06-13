
수정했는데 메시지 안오네
오전 1:40

31s 동안 작업
좋아요. 지금은 당황할 필요 없고, 새로 고치기 전에 “이번에 실행된 결과”부터 확인해야 합니다.

메시지가 안 온 이유는 보통 이 셋 중 하나예요.

수정은 했지만 Commit changes를 안 눌렀다.
수정 후 Price Change Alert를 다시 실행하지 않았다.
다시 실행했지만 아직도 price_change_alert.py 내용이 제대로 안 들어갔다.
지금 할 일은 이것입니다.

상단 Actions 클릭
왼쪽 Price Change Alert 클릭
가운데 목록에서 가장 위에 있는 최신 실행 클릭
예: Price Change Alert #5 또는 #6
들어가서 왼쪽/가운데의 price-change-alert 클릭
가운데 로그에서 Check BTC price-change risk 클릭
그 안의 Run python scripts/price_change_alert.py 앞 삼각형을 눌러 펼치기
거기에 아래 문장들이 보여야 정상입니다:

[price-change] started
[price-change] provider=CoinGecko
[price-change] result=success
만약 또 이것만 보이고 끝나면:

python scripts/price_change_alert.py
env:
...
BTC_ALERT_NOTIFY_NO_ALERT: true
그러면 아직도 price_change_alert.py 안에 실제 코드가 제대로 안 들어간 겁니다.

지금은 최신 실행 로그 화면을 보여주세요.
특히 Run python scripts/price_change_alert.py 펼친 부분이 보이게요. 그 화면을 보면 바로 다음 조치를 정확히 말해줄 수 있습니다.

오전 1:40
Appshot 첨부
화면을 보면 원인이 보입니다.

지금 프로그램은 실행됐는데, 안쪽 내용이 실제로 작동하지 않았습니다.
정상이라면 로그에 이런 문장이 보여야 해요:

[price-change] started
[price-change] provider=CoinGecko
그런데 지금은 이것만 보입니다:

python scripts/price_change_alert.py
뜻은 간단히 말하면:

price_change_alert.py 파일 안에 실행 시작 코드가 빠졌거나, 내용이 제대로 안 들어갔습니다.

지금 해야 할 일은 이것입니다.

상단 Code 클릭
scripts 폴더 클릭
price_change_alert.py 클릭
맨 아래까지 내려가기
파일 맨 마지막에 아래 두 줄이 있는지 확인
if __name__ == "__main__":
    raise SystemExit(main())
없으면 맨 아래에 그대로 추가하세요.

그다음:

Commit changes
Actions
Price Change Alert
Run workflow
이 두 줄은 “이 파일을 실행하면 실제로 프로그램을 시작해라”라는 뜻입니다. 이게 빠지면 GitHub는 파일을 실행했다고 나오지만, 안쪽 기능은 아무것도 안 하고 조용히 끝납니다.

오전 1:41
Appshot 첨부

47s 동안 작업
지금 화면 상태는 아직 틀렸습니다.
맨 아래 두 줄은 맞는데, 그 위에 있어야 할 코드 절반이 빠져 있어요. 그래서 파일 전체를 다시 넣는 게 제일 쉽습니다.

지금 GitHub 편집 화면에서 이렇게 하세요:

코드 입력창 아무 곳이나 클릭
키보드에서 Command + A 누르기
전체 선택입니다.
Delete 누르기
기존 내용 전부 삭제
아래 파일 내용을 통째로 붙여넣기
새 price_change_alert.py

위쪽 초록색 Commit changes... 클릭
작은 창이 뜨면 Commit changes 클릭
다시 Actions → Price Change Alert → Run workflow
붙여넣은 뒤 파일 맨 아래가 이렇게 끝나야 합니다:

if __name__ == "__main__":
    raise SystemExit(main())
그리고 그 위에 def main()이라는 부분도 반드시 있어야 합니다. 지금 화면에는 def main()이 빠져 있어서 작동을 못 한 겁니다.

오전 1:43
Appshot 첨부
지금 화면을 보면 아직 수정이 안 된 상태입니다.

증거는 여기예요:

파일이 99 lines로 끝남
맨 아래가 format_price 함수에서 끝남
아래 코드가 없음
def main():
즉, 이 파일은 아직 “실행할 본문”이 빠져 있습니다. 그래서 GitHub Actions는 성공처럼 끝나지만 실제로는 아무 일도 안 합니다.

지금 해야 할 일:

화면 오른쪽 위에 있는 연필 아이콘 클릭
Raw 버튼 근처에 있습니다.

편집 화면이 열리면 코드 안 아무 곳이나 클릭

Command + A 누르기
전체 선택입니다.

Delete 누르기

아래 파일 내용을 다시 통째로 붙여넣기:

새 price_change_alert.py

붙여넣은 뒤 맨 아래가 반드시 이렇게 끝나는지 확인:
if __name__ == "__main__":
    raise SystemExit(main())
위쪽 초록색 Commit changes... 클릭

작은 창이 뜨면 Commit changes 클릭

그다음 다시:

Actions → Price Change Alert → Run workflow

이번에는 로그에 이런 줄이 나와야 정상입니다:

[price-change] started
[price-change] result=success
지금은 파일 내용이 중간에서 끊긴 상태라서, “부분 수정” 말고 전체 삭제 후 전체 붙여넣기가 제일 안전합니다.

오전 1:45



new-chat
outputs
btc-risk-alert-api-probe
scripts
price_change_alert.py
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
