# Discord cmux bot deployment

이 디렉터리는 Discord / OpenAI / cmux 브리지를 서버에서 서비스로 띄울 때
필요한 systemd 유닛 예시를 담고 있습니다.

## 전제

- 서버에 `cmux`와 `opencode`가 설치되어 있어야 함
- `/opt/hololive_OCG_helper` 경로에 이 레포가 배치되어 있어야 함
- `/opt/hololive_OCG_helper/.venv` 가 생성되어 있고 의존성이 설치되어 있어야 함
- `/etc/hololive_ocg_helper/discord-cmux-bot.env` 파일에 환경변수를 채워야 함

## 환경변수 예시

```bash
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...
DISCORD_ALLOWED_USER_IDS=123,456
DISCORD_ALLOWED_CHANNEL_IDS=111222333444555666
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini
DISCORD_EPHEMERAL_RESPONSES=true
```

## 설치

```bash
sudo install -d -m 0755 /etc/hololive_ocg_helper
sudo install -m 0644 deploy/discord-cmux-bot.service /etc/systemd/system/discord-cmux-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now discord-cmux-bot.service
sudo systemctl status discord-cmux-bot.service
```

## 주의

- `DISCORD_ALLOWED_CHANNEL_IDS`를 지정하지 않으면 모든 채널에서 작동합니다.
- `DISCORD_ALLOWED_USER_IDS`를 지정하지 않으면 허용 채널의 모든 사용자에게 열립니다.
- 서비스 계정 `hololive`와 경로는 서버 환경에 맞게 조정하세요.
