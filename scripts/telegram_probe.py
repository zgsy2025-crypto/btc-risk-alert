#!/usr/bin/env python3
"""
Step 4 probe: verify Telegram message delivery from GitHub Actions.

This is not a trading bot and does not send buy/sell advice.
It only sends a risk-management test notification.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


TELEGRAM_SEND_MESSAGE_URL = "https://api.telegram.org/bot{token}/sendMessage"


def require_secret(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"[telegram-probe] result=fail missing_secret={name}")
        raise SystemExit(1)
    return value


def send_telegram_message(token: str, chat_id: str, text: str) -> dict:
    body = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        TELEGRAM_SEND_MESSAGE_URL.format(token=token),
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "btc-risk-alert-telegram-probe/0.1",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def main() -> int:
    token = require_secret("TELEGRAM_BOT_TOKEN")
    chat_id = require_secret("TELEGRAM_CHAT_ID")

    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    message = (
        "BTC 위험 관리 알림 시스템 테스트\n\n"
        f"테스트 시간: {now}\n\n"
        "이 메시지는 Telegram 연동 확인용입니다.\n"
        "매수/매도 신호가 아니며, 자동매매 기능도 아닙니다.\n"
        "목적: 감정적 진입과 과도한 레버리지 방지를 위한 위험 경고 시스템 검증"
    )

    print("[telegram-probe] started")
    print("[telegram-probe] provider=Telegram Bot API")

    try:
        result = send_telegram_message(token, chat_id, message)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        print(f"[telegram-probe] result=fail http_status={exc.code}")
        print(f"[telegram-probe] response={body}")
        return 1
    except Exception as exc:
        print(f"[telegram-probe] result=fail error={exc}")
        return 1

    if result.get("ok") is not True:
        print(f"[telegram-probe] result=fail response={result}")
        return 1

    print("[telegram-probe] result=success")
    print("[telegram-probe] message_sent=true")
    print("[telegram-probe] next_gate=If Telegram received this, continue to price-change detection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
