# AI Chatbot

FastAPI, Jinja2, SQLAlchemy와 SQLite로 구현하는 웹 기반 AI 챗봇 프로젝트입니다. 현재는 애플리케이션을 실행하고 테스트할 수 있는 최소 스켈레톤만 구현되어 있습니다.

## 요구 환경

- Python 3.12
- SQLite 3
- Git

## 로컬 시작

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

DB를 최신 revision으로 만든 후 앱을 실행합니다.

```bash
alembic upgrade head
uvicorn app.main:create_app --factory --reload
```

브라우저에서 다음 경로를 확인할 수 있습니다.

| 경로 | 역할 |
| --- | --- |
| `/` | 스켈레톤 준비 화면 |
| `/health` | 외부 의존성과 무관한 프로세스 상태 |
| `/docs` | FastAPI OpenAPI UI |

## 설정

| 환경 변수 | 필수 | 기본값/설명 |
| --- | --- | --- |
| `APP_ENV` | 아니요 | `development`; 운영에서는 `production` |
| `DATABASE_URL` | 아니요 | `sqlite:///./data/chatbot.db` |

실제 `.env`, DB, 로그, 백업과 비밀값은 Git에 커밋하지 않습니다.

## Alembic

모델을 변경한 다음 revision 초안을 생성하고 내용을 검토합니다.

```bash
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
alembic current
alembic heads
```

공유되거나 운영 DB에 적용된 revision은 수정하지 않고 새 revision을 추가합니다. SQLite의 복잡한 컬럼·제약 조건 변경에는 Alembic batch mode를 사용합니다.

## 품질 검사

```bash
ruff check .
pytest
```

GitHub Actions의 `pr-check`도 임시 SQLite에 `alembic upgrade head`를 실행한 뒤 같은 검사를 수행합니다.

EC2 설정과 배포 스크립트는 애플리케이션 기능이 준비된 뒤 별도 이슈에서 구현합니다.

## 프로젝트 문서

- [전체 구현 계획](docs/plan.md)
- [스켈레톤 및 이슈 계획](docs/skelton_plan.md)
- [인증 설계](docs/authentication.md)
- [협업 가이드](CONTRIBUTING.md)
