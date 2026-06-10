# BTC Risk Alert

GitHub Actions로 5분마다 BTCUSDT 위험 신호를 확인하고 Telegram으로 알림을 보내는 봇입니다.

## 기능
- 5분 / 15분 / 60분 급등락 감지
- 거래량 폭증 감지
- 1시간 RSI 과열/공포 감지
- 1시간 EMA200 기준 추세 위험 감지
- 자동매매 없음, 알림 전용

## 필요한 GitHub Secrets
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
