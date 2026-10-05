# AI Chatbot

FastAPI, Jinja2, SQLAlchemy와 PostgreSQL로 구현하는 웹 기반 AI 챗봇 프로젝트입니다. 로컬 개발 환경은 Docker Compose로 Web과 PostgreSQL을 함께 실행하고, 운영 환경은 Render Web Service와 Render PostgreSQL을 사용합니다.

## 요구 환경

- Docker
- Docker Compose
- Git

## 로컬 시작

```bash
docker compose up --build
```

Compose가 PostgreSQL 준비를 기다린 뒤 `alembic upgrade head`를 실행하고 FastAPI 개발 서버를 시작합니다. 브라우저에서 <http://localhost:8000>을 엽니다. 소스 변경은 Uvicorn reload로 반영됩니다.

백그라운드 실행과 종료는 다음 명령을 사용합니다.

```bash
docker compose up --build -d
docker compose down
```

PostgreSQL 데이터는 `postgres_data` 볼륨에 유지됩니다. 데이터를 포함해 완전히 초기화할 때만 `docker compose down -v`를 사용합니다.

브라우저에서 다음 경로를 확인할 수 있습니다.

| 경로 | 역할 |
| --- | --- |
| `/` | 스켈레톤 준비 화면 |
| `/auth/signup` | 회원가입 화면 |
| `/auth/login` | 로그인 화면 |
| `/health` | 외부 의존성과 무관한 프로세스 상태 |
| `/docs` | FastAPI OpenAPI UI |

## 설정

| 환경 변수 | 필수 | 기본값/설명 |
| --- | --- | --- |
| `APP_ENV` | 아니요 | `development`; 운영에서는 `production` |
| `DATABASE_URL` | 아니요 | Compose 내부 PostgreSQL URL; Render에서는 Internal Database URL |
| `SESSION_SECRET` | 예 | 32자 이상의 임의 문자열; 운영 값은 Render Secret Environment Variable로만 저장 |

로컬 Compose 설정은 과제 개발용 계정만 사용합니다. Render의 실제 `DATABASE_URL`과 그 밖의 비밀값은 Render 환경변수에만 저장하고 Git에 커밋하지 않습니다.

## Alembic

모델을 변경한 다음 revision 초안을 생성하고 내용을 검토합니다.

```bash
docker compose exec web alembic revision --autogenerate -m "describe schema change"
docker compose exec web alembic upgrade head
docker compose exec web alembic current
docker compose exec web alembic heads
```

공유되거나 운영 DB에 적용된 revision은 수정하지 않고 새 revision을 추가합니다. 자동 생성한 revision은 커밋하기 전에 반드시 검토합니다.

## 품질 검사

```bash
docker compose exec web ruff check .
docker compose exec web pytest
```

Web 컨테이너를 계속 실행하지 않고 검사만 수행하려면 다음 명령을 사용합니다.

```bash
docker compose run --rm web ruff check .
docker compose run --rm web pytest
```

GitHub Actions의 `pr-check`도 일회성 PostgreSQL service container에 `alembic upgrade head`를 실행한 뒤 같은 검사를 수행합니다.

## Render 배포

Render Web Service에는 운영 PostgreSQL의 **Internal Database URL**을 `DATABASE_URL`로 등록합니다. Web Service와 PostgreSQL은 같은 리전을 사용해야 합니다.

```text
Build Command: pip install -r requirements.txt
Start Command: alembic upgrade head && uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

`main` 브랜치에 변경 사항을 푸시하면 Render가 자동 배포합니다. 무료 PostgreSQL은 생성 후 30일에 만료되므로 제출 및 발표 일정을 기준으로 만료일을 확인합니다.

## 프로젝트 문서

- [전체 구현 계획](docs/plan.md)
- [스켈레톤 및 이슈 계획](docs/skelton_plan.md)
- [인증 설계](docs/authentication.md)
- [협업 가이드](docs/CONTRIBUTING.md)
