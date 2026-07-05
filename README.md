# Telegram Prime

본인/팀이 소유한 텔레그램 계정을 관리하는 셀프호스팅 도구. Docker 없이 Python(FastAPI+Telethon)과 Node(React+Vite)만으로 동작합니다.

## 기능

- 텔레그램 계정 로그인(전화번호+OTP+2FA) 또는 `.session` 파일 업로드
- 웹에서 web.telegram.org처럼 대화 조회/전송, 실시간 수신(WebSocket)
- 여러 계정에 이름/소개/유저네임/프로필 사진 일괄 편집 (속도 제한 + FloodWait/PeerFlood 대응)
- 계정 상태(활성/차단/FloodWait/연결끊김) 자동·수동 점검
- 계정별 자동응답(부재중 응답), 스토리 업로드
- 라이트/다크 모드

## 준비물

- Python 3.11+
- Node.js 18+
- 텔레그램 API 자격증명(`api_id`, `api_hash`) — https://my.telegram.org 에서 발급

## 백엔드 실행

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd ..
cp .env.example .env
# .env를 열어 ADMIN_PASSWORD, SESSION_SECRET, MASTER_ENCRYPTION_KEY를 채우세요.
# SESSION_SECRET: python -c "import secrets; print(secrets.token_urlsafe(32))"
# MASTER_ENCRYPTION_KEY: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

백엔드는 `http://127.0.0.1:8000`에서 실행됩니다. DB는 `backend/data/app.db` SQLite 파일 하나입니다.

## 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

`http://127.0.0.1:5173`에서 접속하고, `.env`에 설정한 `ADMIN_USERNAME`/`ADMIN_PASSWORD`로 로그인하세요.

## 테스트

```bash
cd backend
source .venv/bin/activate
python -m pytest app/tests/ -q
```

## 배포

Docker 없이도 충분합니다: 백엔드는 `uvicorn app.main:app --host 0.0.0.0 --port 8000`을 systemd 서비스로 등록하고, 프론트엔드는 `npm run build` 후 정적 파일을 nginx/Caddy 등으로 서빙하면서 `/api`를 백엔드로 리버스 프록시하면 됩니다. 반드시 TLS(HTTPS) 뒤에 두세요 — 로그인 코드/2FA 비밀번호가 평문으로 오갑니다.
