# Discord / cmux 브리지

이 레포의 `scripts/discord_cmux_bot.py`는 Discord slash command로
OpenAI 답변을 받고, 동시에 `cmux` 워크스페이스 상태를 조회하거나
OpenCode 역할 워크스페이스를 시작하는 얇은 브리지입니다.

## 지원 명령

- `/ask prompt:` OpenAI Responses API로 답변 생성
- `/cmux status`: `cmux list-workspaces` 출력 조회
- `/cmux start role:` 역할별 워크스페이스 시작
- `/cmux capture workspace_ref surface_ref lines:` 특정 pane 스크롤백 캡처

## 필요한 환경 변수

```bash
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...            # 개발 중 즉시 동기화하려면 권장
DISCORD_ALLOWED_USER_IDS=123,456 # 허용된 사용자만 사용
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini
DISCORD_EPHEMERAL_RESPONSES=true
```

## 설치

```bash
source .venv/bin/activate  # 이미 있으면 활성화
python3 -m pip install -r requirements.txt
```

## 실행

```bash
python3 scripts/discord_cmux_bot.py
```

## Discord Developer Portal 설정

1. 새 Application 생성
2. Bot 추가
3. OAuth2 URL Generator에서 다음 scope 선택
   - `bot`
   - `applications.commands`
4. 봇 토큰을 `DISCORD_BOT_TOKEN`에 넣기
5. 테스트 서버가 있으면 `DISCORD_GUILD_ID`를 넣어서 slash command를 즉시 동기화하기

## 주의

- 이 브리지는 임의 shell 실행을 열지 않습니다.
- `cmux start`는 레포에 있는 역할 스크립트만 실행합니다.
- 운영 환경에서는 `DISCORD_ALLOWED_USER_IDS`를 꼭 설정하세요.
