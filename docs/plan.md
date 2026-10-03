# 웹 기반 AI 챗봇 서비스 구현 계획

> 기준 문서: `[subject.pdf](./subject.pdf)`  
> 대상: 3인 팀 / FastAPI 기반 텀 프로젝트  
> 목적: 과제 필수 요구사항을 빠짐없이 구현하고, 팀 역량과 일정에 따라 안전하게 확장한다.

## 1. 과제 해석과 기술 선택 원칙

과제에서 **Python과 FastAPI는 필수**이다. DB 기술은 평가자가 저장된 대화 로그를 확인할 수 있으면 되므로 PostgreSQL로 통일한다. Jinja2는 명시적 필수 기술은 아니지만, FastAPI의 서버 렌더링 UI를 가장 적은 복잡도로 구현할 수 있어 기본안으로 채택한다.

이 프로젝트의 우선순위는 다음과 같다.

1. 회원가입/로그인 후 질문하고 AI 답변을 받는 핵심 흐름을 완성한다.
2. 대화 문맥, DB 저장, 로그 조회, 예외 처리 등 평가 필수 조건을 검증 가능하게 만든다.
3. 외부에서 접속 가능한 환경에 배포하고 문서와 Git 이력을 갖춘다.
4. 위 항목이 안정화된 뒤에만 프론트엔드 분리, 스트리밍 등의 확장을 검토한다.

### 권장 기본 스택


| 영역     | 기본 선택                              | 선택 이유                                             |
| ------ | ---------------------------------- | ------------------------------------------------- |
| 백엔드    | Python + FastAPI                   | 과제 필수, 타입 기반 검증과 API 문서 지원                        |
| UI     | Jinja2 + HTML/CSS + 소량의 JavaScript | 단일 저장소에서 인증과 화면을 단순하게 구현 가능                       |
| DB     | PostgreSQL / Render PostgreSQL        | 모든 환경의 DB 동작을 통일하고 운영 데이터는 Render PostgreSQL에 저장한다.     |
| 스키마 변경 | Alembic                            | SQLAlchemy 모델과 스키마 변경 이력을 표준 도구로 관리                 |
| 인증     | 서명된 쿠키 세션 + 비밀번호 해시                | Jinja2 기반 단일 웹 앱에 단순하며 별도 세션 저장소가 필요 없음           |
| AI 연동  | 공급자 SDK 또는 `httpx`를 감싼 어댑터         | API 키를 서버에만 두고 테스트 시 가짜 구현으로 교체 가능                |
| 테스트    | pytest + FastAPI TestClient/httpx  | 인증, API, DB, 장애 시나리오 자동 검증                        |
| CI     | GitHub Actions                     | PR마다 마이그레이션과 테스트를 자동 검증                           |
| 설정     | `.env` + 설정 클래스                    | 키를 코드와 Git에서 분리하고 필수 설정 누락을 조기 발견                 |
| 배포     | Render Free Web Service            | GitHub 연동, 자동 배포와 HTTPS URL을 별도 서버 운영 없이 제공한다.       |




## 2. 필수 범위와 완료 기준

아래 P0 범위는 모두 구현해야 한다. P1은 품질 향상 항목이며 P0 완료 전에는 착수하지 않는다.


| ID  | 스코프             | 우선순위 | 완료 기준                                         |
| --- | --------------- | ---- | --------------------------------------------- |
| S1  | 프로젝트 기반 구조와 설정  | P0   | 앱이 로컬에서 실행되고 환경 변수 누락 시 이해 가능한 오류를 출력한다.      |
| S2  | 회원가입·로그인·로그아웃   | P0   | 회원가입과 로그인이 동작하고 비밀번호가 해시로 저장된다.               |
| S3  | 인증 기반 접근 제어     | P0   | 비로그인 사용자는 챗봇과 개인 로그에 접근할 수 없다.                |
| S4  | 챗봇 웹 UI         | P0   | 같은 화면에서 질문을 전송하고 응답 또는 오류 안내를 확인한다.           |
| S5  | AI API 연동       | P0   | 서버에서 AI API를 호출하며 키가 브라우저나 저장소에 노출되지 않는다.     |
| S6  | 최소 문맥 유지        | P0   | 같은 사용자의 최근 대화를 다음 AI 요청에 포함한다.                |
| S7  | 대화 로그 저장        | P0   | 사용자, 시각, 질문, 응답을 DB에 누적한다.                    |
| S8  | 사용자별 로그 조회      | P0   | 로그인 사용자가 자신의 대화만 화면/API로 조회할 수 있다.            |
| S9  | 검증·예외·운영 로그     | P0   | 빈/과도한 입력을 막고 AI 실패·타임아웃을 처리하며 핵심 이벤트를 기록한다.   |
| S10 | 테스트             | P0   | 핵심 정상 흐름, 권한, 검증, AI 장애 시나리오가 자동 테스트를 통과한다.   |
| S11 | 배포·문서·DB 확인 가이드 | P0   | 외부 URL, README, API/DB/실행 설명, 로그 확인 수단이 제공된다. |
| S12 | Git/PR 협업 증빙    | P0   | 기능 브랜치와 PR 병합 기록, 팀원별 유의미한 커밋 10회 이상이 남는다.    |
| S13 | UX·운영 확장        | P1   | 스트리밍, 대화방, 관리자 기능 등을 팀 선택에 따라 추가한다.           |




## 3. 목표 아키텍처

라우터가 AI SDK나 SQL을 직접 다루지 않게 한다. `ChatService`가 “요청 수신 → 문맥 조회 → AI 호출 → 응답 저장 → 결과 반환”을 조정하고, 외부 AI 호출과 DB 접근은 각각 어댑터와 저장소로 분리한다. 로컬·CI·운영 모두 PostgreSQL을 사용하고 SQLAlchemy와 Alembic으로 같은 스키마를 관리한다.

### 제안 디렉터리 구조

```text
app/
├── main.py                 # 앱 생성, 미들웨어, 라우터 연결
├── config.py               # 환경 변수 및 설정
├── db.py                   # 엔진, 세션, 의존성
├── models/                 # SQLAlchemy 모델
├── schemas/                # 요청/응답 검증 모델
├── routers/
│   ├── auth.py
│   ├── chat.py
│   └── history.py
├── services/
│   ├── auth_service.py
│   └── chat_service.py
├── repositories/
├── integrations/
│   └── ai_client.py
├── templates/
└── static/
alembic/
├── env.py                   # SQLAlchemy metadata와 DATABASE_URL 연결
└── versions/                # Alembic revision 파일
alembic.ini
.github/
└── workflows/
    └── pr-check.yml
Dockerfile                   # FastAPI Web 이미지
compose.yaml                 # 로컬 FastAPI Web과 PostgreSQL
tests/
.env.example
.gitignore
README.md
```



## 4. 스코프별 구현 방법



### S1. 프로젝트 기반 구조와 환경 설정

- 앱 팩토리 또는 `app/main.py`에서 FastAPI 인스턴스를 만들고 라우터, 정적 파일, 템플릿, 세션 미들웨어를 등록한다.
- `APP_ENV`, `SESSION_SECRET`, `AI_API_KEY`, `AI_MODEL`, `DATABASE_URL`, `AI_TIMEOUT_SECONDS`를 환경 변수로 받는다.
- 실제 `.env`는 `.gitignore`에 포함하고, 값이 없는 `.env.example`만 커밋한다.
- CSS/JavaScript는 `StaticFiles`로 애플리케이션에 직접 마운트한다.
- 개발용 실행 명령, 마이그레이션 명령, 테스트 명령을 README에 고정한다.
- `/health`는 AI API를 호출하지 않고 앱 프로세스의 생존 여부만 반환한다. 필요하면 `/ready`에서 DB 연결을 별도로 확인한다.

완료 검증:

- 새 팀원이 README만 보고 빈 환경에서 앱을 실행할 수 있다.
- `AI_API_KEY`가 Git 이력, HTML, 브라우저 네트워크 응답, 서버 로그에 나타나지 않는다.



### S2-S3. 사용자 인증과 접근 제어

인증 상태는 Starlette `SessionMiddleware` 기반의 **서명된 쿠키 세션**으로 관리한다. 서버 DB에 세션 레코드를 저장하는 방식이나 JWT는 사용하지 않는다. 서명은 쿠키 변조를 탐지하지만 내용을 암호화하지는 않으므로 세션에는 내부 `user_id`만 저장한다.

세션 방식별 구조, JWT와의 차이, 보안 속성 및 선택 근거는 [서명 쿠키 세션과 JWT 인증 설계 가이드](./authentication.md)에 정리한다.

1. `POST /auth/signup`에서 이메일 또는 사용자명을 정규화하고 중복을 검사한다.
2. 비밀번호는 Argon2 또는 bcrypt 계열 해시로 저장하며 평문은 저장하거나 기록하지 않는다.
3. `POST /auth/login` 성공 시 기존 세션을 비운 뒤 `request.session["user_id"]`에 내부 사용자 ID만 저장한다.
4. `POST /auth/logout`에서 `request.session.clear()`로 세션을 제거한다.
5. `require_user` 의존성을 만들어 챗봇, 채팅 API, 내 기록 경로에 공통 적용한다.
6. 비로그인 페이지 요청은 로그인 화면으로, JSON API 요청은 `401`로 응답한다.

보안 기본선:

- `SESSION_SECRET`은 충분히 긴 무작위 값으로 생성해 서버 환경 변수로만 관리한다.
- 세션 쿠키에 `HttpOnly`, 배포 환경에서 `Secure`, `SameSite=Lax`, 명시적 만료 시간을 적용한다.
- 세션 쿠키에는 `user_id` 외의 비밀번호, 이메일, API 키, 권한 정보 등 민감한 값을 넣지 않는다.
- 요청마다 세션의 `user_id`로 DB 사용자를 다시 조회하고, 존재하지 않는 사용자의 세션은 제거한다.
- 로그인 실패 메시지는 계정 존재 여부를 과도하게 노출하지 않는다.
- 최소 비밀번호 길이와 최대 입력 길이를 검증한다.
- 상태를 변경하는 폼은 CSRF 방어를 적용한다. 라이브러리를 쓰지 않으면 세션 기반 토큰을 폼과 비교한다.



### S4. 챗봇 웹 UI

- `/chat` 한 화면에 이전 대화, 질문 입력창, 전송 버튼, 로딩 상태, 오류 메시지를 둔다.
- 초기 렌더링은 Jinja2로 하고, 질문 전송만 `fetch()`로 `POST /api/chat`을 호출하면 페이지 새로고침 없이 같은 화면에 결과를 표시할 수 있다.
- JavaScript가 실패해도 폼 제출로 동작하게 만들지는 선택 사항이지만, 구현하면 접근성과 장애 대응이 좋아진다.
- 사용자 질문과 AI 응답은 서로 다른 시각적 스타일로 구분하고 긴 텍스트는 줄바꿈한다.
- AI 응답을 HTML로 직접 삽입하지 말고 기본적으로 텍스트로 렌더링해 XSS를 방지한다. Markdown을 지원하면 허용 태그 기반 정화가 필요하다.

입력 검증 기본값:

- 앞뒤 공백 제거 후 빈 질문 거부
- 질문 길이 1~2,000자 범위로 제한
- 중복 전송 방지를 위해 처리 중 버튼 비활성화



### S5-S6. AI API 연동과 문맥 유지

`AIClient` 인터페이스를 만들고 실제 구현과 테스트용 가짜 구현을 분리한다.

```python
class AIClientProtocol(Protocol):
    async def generate(self, messages: list[dict[str, str]]) -> str: ...
```

채팅 처리 순서:

1. 인증 사용자와 검증된 질문을 받는다.
2. `request_id`를 발급하고 요청 수신 로그를 남긴다.
3. 해당 사용자의 최근 대화 N개를 시간순으로 조회한다.
4. 시스템 지침 + 최근 Q/A + 현재 질문으로 메시지를 구성한다.
5. 명시적 타임아웃과 함께 AI API를 호출한다.
6. 성공한 답변을 현재 질문과 함께 하나의 트랜잭션으로 저장한다.
7. 응답과 `chat_id`, 생성 시각을 반환한다.

기본 문맥 정책은 **같은 사용자의 최근 5개 Q/A**로 시작한다. 구현이 단순하고 과제 요구를 충족한다. 다만 사용자 전체 대화를 섞으면 주제가 바뀌었을 때 품질이 떨어지므로, P1에서 `conversation_id` 기반 대화방을 도입한다.

문맥에는 DB에서 읽은 텍스트만 넣고 비밀번호, 세션 값, API 키, 내부 오류 스택은 절대 포함하지 않는다. 길이가 모델 한도를 넘지 않도록 대화 개수와 각 메시지 길이를 제한한다.

### S7-S8. 대화 로그 저장과 사용자별 조회

최소 DB 모델:

```text
users
- id                 INTEGER PK
- username           VARCHAR UNIQUE NOT NULL
- password_hash      VARCHAR NOT NULL
- created_at         DATETIME NOT NULL

chats
- id                 INTEGER PK
- user_id            INTEGER FK(users.id) NOT NULL, INDEX
- question           TEXT NOT NULL
- answer             TEXT NOT NULL
- created_at         DATETIME NOT NULL, INDEX
- request_id         VARCHAR UNIQUE NOT NULL
- ai_model            VARCHAR NULL
- latency_ms         INTEGER NULL
```

과제의 최소 추적 필드는 `user_id`, `created_at`, `question`, `answer`이다. `request_id`, 모델명, 지연 시간은 장애 추적과 시연에 유용해 함께 저장한다. 시간은 DB에 UTC로 저장하고 화면에서 로컬 시간대로 표시한다.

조회 구현:

- `GET /api/me/chats?limit=20&offset=0`: 현재 사용자의 기록만 최신순으로 반환
- `GET /history`: 위 데이터를 이용해 사람이 확인 가능한 화면 제공

객체 ID를 요청받는 API를 추가할 경우 반드시 `chat.user_id == current_user.id`를 검사한다. 단순히 ID로만 조회하면 다른 사용자의 대화가 노출될 수 있다.

#### Alembic 마이그레이션 관리

DB 구조 변경은 SQLAlchemy 모델과 Alembic revision으로 관리한다.

```text
alembic/
├── env.py
└── versions/
    ├── <revision>_create_users.py
    ├── <revision>_create_chats.py
    └── <revision>_add_request_id.py
alembic.ini
```

`alembic/env.py`는 애플리케이션의 `Base.metadata`와 `DATABASE_URL`을 사용하도록 구성한다. 개발자가 모델을 변경한 뒤 다음 명령으로 revision 초안을 만든다.

```bash
alembic revision --autogenerate -m "add request id to chats"
```

자동 생성 결과는 그대로 병합하지 않고 `upgrade()`와 `downgrade()`가 의도한 스키마 변경만 포함하는지 리뷰한다. 타입, 인덱스와 제약 조건은 PostgreSQL을 기준으로 작성하고 로컬 PostgreSQL과 Render PostgreSQL 양쪽에서 검증한다.

```bash
alembic upgrade head
alembic downgrade -1
alembic current
```

한 번 공유되거나 운영 DB에 적용된 revision 파일은 수정하지 않는다. 스키마를 다시 바꾸려면 새 revision을 추가한다. 로컬·CI에서는 `alembic upgrade head`를 명시적으로 실행한다. Render 무료 플랜은 별도 pre-deploy command를 제공하지 않으므로 시작 명령에서 마이그레이션이 성공한 경우에만 Uvicorn을 실행한다. 운영 migration은 이전 애플리케이션 버전과 호환되도록 additive change를 우선한다.



### S9. 입력 검증, 예외 처리, 운영 로그

AI 계층의 예외를 서비스 내부 예외로 변환한다.


| 상황         | 사용자 응답                          | HTTP 상태      | 서버 로그                    |
| ---------- | ------------------------------- | ------------ | ------------------------ |
| 빈 입력/길이 초과 | 입력 조건 안내                        | 422          | 검증 실패 사유, request_id     |
| 비로그인       | 로그인 필요 안내                       | 401 또는 리다이렉트 | 경로, request_id           |
| AI 타임아웃    | 잠시 후 재시도 안내 + `AI_TIMEOUT`      | 504          | 실패 유형, 지연 시간, request_id |
| AI 공급자 오류  | 일시적 오류 안내 + `AI_UPSTREAM_ERROR` | 502          | 공급자 상태, request_id       |
| DB 저장 실패   | 저장 실패 안내 + `DB_WRITE_ERROR`     | 500          | 예외와 request_id           |
| 알 수 없는 오류  | 일반 오류 안내                        | 500          | 스택 트레이스와 request_id      |


과제에서 요구하는 다음 이벤트명을 일관되게 남긴다.

- `request_received`
- `ai_call_start`
- `ai_call_success` 또는 `ai_call_failure`
- `db_save_success` 또는 `db_save_failure`

로그에는 `request_id`, `user_id`, 경로, 처리 시간처럼 검색 가능한 필드를 넣되 질문/응답 원문, 비밀번호, 쿠키, API 키는 기본적으로 남기지 않는다. AI 실패 시 프로세스를 종료하지 않고 해당 요청만 오류 응답으로 끝낸다.

DB 저장 정책은 팀이 명확히 합의해야 한다. 기본안은 **AI 호출 성공 + DB 저장 성공일 때만 정상 응답**이다. AI 호출 실패도 분석해야 한다면 P1에서 별도의 `chat_attempts` 테이블에 상태와 안전한 오류 코드만 저장한다.

### S10. 테스트 전략

외부 AI API를 테스트에서 직접 호출하지 않는다. 의존성 주입으로 가짜 AI 클라이언트를 사용해 빠르고 재현 가능한 테스트를 만든다.

필수 자동 테스트:

- 회원가입 성공, 중복 가입 거부, 로그인 성공/실패, 로그아웃
- 로그인 성공 시 서명 세션 쿠키가 발급되고 로그아웃 시 제거되는지 확인
- 임의로 변조한 세션 쿠키가 인증에 사용되지 않는지 확인
- 비로그인 사용자의 `/chat`, `/api/chat`, `/api/me/chats` 접근 차단
- 빈 질문과 최대 길이 초과 거부
- 정상 AI 응답 반환 및 DB 저장
- 두 사용자 사이의 대화 기록 격리
- 최근 N개 대화가 시간순으로 문맥에 포함되는지 확인
- AI 타임아웃 및 공급자 오류가 약속된 상태 코드/오류 코드로 변환되는지 확인
- DB 저장 실패가 처리되고 실패 로그가 남는지 확인
- 빈 PostgreSQL 테스트 DB에 `alembic upgrade head`를 실행하면 최신 스키마가 생성되는지 확인
- 같은 PostgreSQL DB에 `alembic upgrade head`를 다시 실행해도 변경 없이 성공하는지 확인
- `alembic current`와 `alembic heads`가 동일한 revision을 가리키는지 확인
- 지원하는 downgrade 범위에서 `downgrade` 후 `upgrade head`가 다시 성공하는지 확인
- PostgreSQL 드라이버가 설치된 상태에서 Render Internal Database URL을 파싱할 수 있는지 확인
- Render 시작 명령이 `$PORT`에 바인딩하고 migration 실패 시 Uvicorn을 실행하지 않는지 확인



#### PR 자동 검증

PR이 생성되거나 새 커밋이 올라오면 GitHub Actions가 운영 DB가 아닌 PostgreSQL service container를 대상으로 다음 작업을 실행한다.

```text
PR 생성 또는 갱신
       ↓
의존성 설치
       ↓
격리된 PostgreSQL에 alembic upgrade head 실행
       ↓
pytest가 마이그레이션된 DB로 FastAPI 시작
       ↓
기능 테스트 / Alembic revision 상태 검증
       ↓
모두 성공해야 병합 가능
```

PR 워크플로에는 Render 운영 DB 연결 문자열과 운영 비밀값을 전달하지 않는다. 워크플로가 일회성 PostgreSQL service container를 만들고 `alembic upgrade head`를 실행한 뒤 테스트 fixture와 애플리케이션 팩토리가 같은 테스트 DB를 사용하게 한다. 리뷰 중인 코드가 운영 DB를 변경하거나 배포되지 않도록 PR 단계는 마이그레이션 **검증만** 담당한다.

```python
def test_app_starts_with_migrated_database(migrated_database_url):
    with TestClient(create_app(database_url=migrated_database_url)) as client:
        assert client.get("/health").status_code == 200
```

`.github/workflows/pr-check.yml`의 핵심 트리거와 실행 순서는 다음과 같다.

```yaml
on:
  pull_request:
    branches: [main]

jobs:
  pr-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: alembic upgrade head
      - run: pytest
```

브랜치 보호 규칙에서 `pr-check`를 필수 상태 검사로 지정해 성공한 PR만 병합한다. CI는 “PostgreSQL service 준비 → `alembic upgrade head` → 테스트” 순서를 검증하며 운영 Render PostgreSQL에는 연결하지 않는다.

수동 인수 테스트:

1. 새 계정 가입 → 로그인 → 질문 → 같은 화면에서 응답 확인
2. 후속 질문으로 직전 문맥 유지 확인
3. 내 기록 화면에서 질문/응답/시간 확인
4. 로그아웃 후 챗봇 접근 차단 확인
5. 가짜 지연 또는 잘못된 AI 키로 오류 안내와 서버 생존 확인
6. 외부 네트워크에서 배포 URL 접속 확인



### S11. 배포, 문서, 평가용 패키지

배포 대상은 **Render Free Web Service**, 운영 DB는 **Render Free PostgreSQL**로 확정한다. Render를 GitHub 저장소의 `main` 브랜치와 연결해 병합된 커밋만 자동 배포한다. 로컬은 Docker Compose로 FastAPI Web과 PostgreSQL을 함께 실행하고, PR CI는 PostgreSQL service container를 사용한다. Render의 로컬 파일시스템은 영속 저장소로 사용하지 않는다.

현재 단계에서 애플리케이션과 문서는 다음 배포 경계를 지킨다.

- Render Dashboard에서 Python runtime, 무료 plan, `main` 자동 배포와 `/health` health check를 설정한다.
- build command는 `pip install -r requirements.txt`로 고정한다.
- 무료 plan에는 pre-deploy command가 없으므로 start command는 `alembic upgrade head && uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT`로 고정한다.
- migration이 실패하면 Uvicorn을 실행하지 않아 새 deploy를 실패 처리한다.
- 운영 `DATABASE_URL`, `SESSION_SECRET`, `AI_API_KEY`는 Render Secret Environment Variables로만 저장한다.
- Web Service와 PostgreSQL을 같은 리전에 두고 Render Internal Database URL을 사용한다. 실제 연결 문자열은 저장소나 GitHub Actions에 넣지 않는다.
- Render 로컬 파일에 사용자 데이터·백업을 저장하지 않는다.
- Render가 제공하는 HTTPS `onrender.com` URL을 사용하며 별도 Nginx, systemd, SSH 서버와 GitHub Actions CD workflow는 두지 않는다.

무료 plan 제약은 문서와 시연 절차에 명시한다.

- Render는 일정 시간 요청이 없으면 sleep하고 첫 요청에서 cold start가 발생할 수 있으므로 발표 전에 URL을 한 번 호출한다.
- Render 무료 PostgreSQL은 생성 후 30일에 만료되므로 제출·발표 전에 만료일과 DB 연결을 확인한다.
- 무료 plan 한도 또는 정책 변경에 대비해 평가 직전 `/health`, 회원가입, 질문, 기록 조회를 전체 리허설한다.
- Render 장애 시 자동 우회 배포는 만들지 않고 서비스 대시보드 상태와 로그를 확인한다.

무료 plan의 최신 제한은 [Render Free 문서](https://render.com/docs/free)를 기준으로 배포 직전에 다시 확인한다.

평가자가 DB를 확인할 수 있도록 다음 방법을 준비한다.

- 로그인 후 `/history` 화면
- `GET /api/me/chats` API와 응답 예시
- 필요하면 개인정보를 제거한 평가용 계정과 샘플 대화

README에 반드시 포함할 내용:

- 문제 정의, 타겟 사용자, 핵심 사용 시나리오
- 아키텍처와 컴포넌트 역할
- API 요청/응답 예시와 오류 코드
- ERD 또는 테이블/필드 설명
- 로컬 실행, 테스트, Alembic 마이그레이션 방법
- 환경 변수 이름과 설정 방법(실제 비밀값 제외)
- DB 로그 확인 화면/API 사용법
- 브랜치 전략과 PR 규칙
- 팀 역할과 개인별 실제 작업 요약
- 배포가 완료된 뒤 Render URL, Internal Database URL 연결 방식과 cold start 대응 절차
- Alembic revision 생성·리뷰·upgrade·downgrade 규칙

배포 전에는 Git 전체 이력에서도 비밀값 노출 여부를 확인한다. 한 번 커밋된 키는 파일에서 지우는 것만으로 부족하므로 즉시 폐기·재발급하고 이력 정리 여부를 판단해야 한다.

### S12. Git/PR 협업

권장 흐름:

```text
main       배포 가능한 안정 버전
feature/*  기능 단위 작업 브랜치
fix/*      결함 수정 브랜치
docs/*     문서 변경 브랜치
```

- 모든 변경은 이슈 → 작업 브랜치 → PR → 1명 이상 리뷰 → 병합 순서로 진행한다.
- 커밋은 실행 가능한 작은 단위로 나누고 `feat:`, `fix:`, `test:`, `docs:`, `chore:` 등의 접두사를 통일한다.
- 과제 조건인 **팀원별 유의미한 커밋 10회 이상**을 마지막 주에 채우지 말고, 각 스프린트에서 자연스럽게 누적한다.
- PR 설명에 변경 목적, 검증 방법, 화면 변경 시 캡처, 관련 이슈를 적는다.
- 역할은 소유권이지 독점 작업이 아니다. 각자 주 담당 영역을 가지되 최소 한 영역은 교차 리뷰한다.



## 5. 제안 API 계약


| Method   | Path            | 인증  | 용도                    |
| -------- | --------------- | --- | --------------------- |
| GET      | `/`             | 선택  | 서비스 소개 또는 로그인 상태별 진입점 |
| GET/POST | `/auth/signup`  | 아니요 | 회원가입 화면/처리            |
| GET/POST | `/auth/login`   | 아니요 | 로그인 화면/처리             |
| POST     | `/auth/logout`  | 예   | 세션 종료                 |
| GET      | `/chat`         | 예   | 챗봇 화면                 |
| POST     | `/api/chat`     | 예   | 질문 전송과 AI 응답 반환       |
| GET      | `/history`      | 예   | 내 대화 기록 화면            |
| GET      | `/api/me/chats` | 예   | 내 대화 기록 JSON 조회       |
| GET      | `/health`       | 아니요 | 프로세스 상태 확인            |


채팅 요청 예시:

```json
{
  "question": "내가 직전에 무엇을 물어봤지?"
}
```

성공 응답 예시:

```json
{
  "chat_id": 42,
  "answer": "직전에는 배포 방법을 질문하셨습니다.",
  "created_at": "2026-10-02T06:30:00Z",
  "request_id": "9f3b..."
}
```

오류 응답 예시:

```json
{
  "error": {
    "code": "AI_TIMEOUT",
    "message": "응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.",
    "request_id": "9f3b..."
  }
}
```



## 6. 3인 팀 역할 분담

역할은 아래처럼 시작하되, Git 이력과 최종 문서에는 실제 수행 내역을 반영한다.


| 담당             | 주 소유 범위                              | 교차 책임                  |
| -------------- | ------------------------------------ | ---------------------- |
| 팀원 A: 백엔드/AI   | S5-S6 AI 어댑터, 문맥 구성, 채팅 서비스, 장애 처리   | 팀원 C의 API 연동 리뷰        |
| 팀원 B: 인증/데이터   | S2-S3 인증, S7-S8 모델·마이그레이션·조회, 보안     | 팀원 A의 서비스/DB 트랜잭션 리뷰   |
| 팀원 C: UI/배포·QA | S4 템플릿/JS/CSS, S10 인수 테스트, S11 배포/문서 | 팀원 B의 인증 화면 및 접근 제어 리뷰 |


공동 책임:

- 아키텍처와 API 계약 결정
- PR 리뷰와 통합 테스트
- README의 개인별 작업 요약
- 외부 URL 및 평가 시나리오 최종 점검

단일 담당자에게만 지식이 몰리지 않도록 인증, AI, 배포 영역은 각각 다른 팀원이 최소 한 번 직접 리뷰하고 로컬에서 실행한다.

## 7. 구현 순서와 마일스톤



### M0. 합의와 저장소 준비

- 사용자 시나리오, 기본 스택, AI 공급자 결정
- 브랜치/PR/커밋 규칙과 코드 스타일 합의
- FastAPI 골격, 설정, DB 연결, Alembic, PR 자동 검증 골격 생성

종료 조건: 세 팀원이 Docker Compose PostgreSQL로 앱을 실행하고, 빈 테스트 DB에 `alembic upgrade head`를 적용한 뒤 테스트를 통과한다.

### M1. 인증 가능한 웹 앱

- 회원가입, 로그인, 로그아웃
- 세션과 접근 제어
- 빈 챗봇 화면과 기본 레이아웃

종료 조건: 비로그인/로그인 접근 제어 테스트가 통과한다.

### M2. 핵심 채팅 파이프라인

- AI 어댑터와 가짜 구현
- 질문 검증, 타임아웃, 오류 매핑
- 대화 저장, 최근 N개 문맥, 채팅 UI 연동
- 핵심 이벤트 로깅

종료 조건: “로그인 → 질문 → 응답 → DB 저장 → 후속 질문” 흐름이 동작한다.

### M3. 조회·테스트·평가 준비

- 내 대화 기록 화면/API와 확인용 SQL
- 권한 격리 및 장애 테스트
- README, API 명세, ERD, 역할/작업 요약
- Render PostgreSQL 연결과 운영 migration 검증
- Render GitHub 연동·자동 배포와 외부 접속 확인

종료 조건: 필수 인수 테스트와 평가 체크리스트가 모두 통과한다.

### M4. 선택 확장과 안정화

- P1 기능 중 가치가 큰 항목만 선택
- 접근성/반응형/로딩 UX 개선
- 리허설에서 발견된 결함 수정

종료 조건: 새 기능 때문에 P0 테스트나 배포 안정성이 깨지지 않는다.

## 8. 팀 합의에 따른 빌드업 선택지

확장은 “멋있어 보이는 기술”보다 해결하려는 문제가 분명할 때 선택한다.


| 확장               | 도입 조건                                         | 추가 구현                                  | 주의점                            |
| ---------------- | --------------------------------------------- | -------------------------------------- | ------------------------------ |
| 운영 DB 유료 전환     | 무료 Render PostgreSQL의 30일 만료가 문제가 될 때                | 유료 plan, 백업·복구 정책                     | 과제 일정이 30일 이내면 무료 plan 유지       |
| React/Vue 프론트 분리 | 팀원이 SPA 경험이 있고 UI 상호작용이 핵심                    | CORS, 별도 빌드/배포, API 인증 설계              | 과제 핵심보다 통합 비용이 커질 수 있음         |
| HTMX             | Jinja2를 유지하며 부분 갱신을 간결하게 만들고 싶을 때             | HTML fragment 응답                       | 팀 전체가 패턴을 익혀야 함                |
| 응답 스트리밍(SSE)     | 긴 AI 응답의 체감 대기 시간을 개선할 때                      | 스트림 API, 중단/실패 UI, 저장 시점 정의            | 테스트와 오류 처리가 복잡해짐               |
| 대화방/새 대화         | 사용자별 여러 주제를 분리할 필요가 있을 때                      | `conversations` 테이블과 `conversation_id` | 권한 검사 대상 증가                    |
| Redis            | 서버를 여러 인스턴스로 확장하거나 세션/제한 상태 공유 필요             | Redis 배포, 만료 정책                        | MVP 단일 인스턴스에는 과할 수 있음          |
| 관리자 대시보드         | 운영자가 전체 로그를 확인해야 할 때                          | 관리자 역할, 감사 로그, 강한 권한 검사                | 개인정보 노출 위험 증가                  |


권장 확장 순서는 `자동 테스트/CI → 대화방 → 스트리밍`이다. React/Vue, Redis, 관리자 기능은 명확한 필요가 있을 때만 선택한다.

### 기술 결정 시 확인할 질문

1. 이 변경이 과제의 어떤 필수 조건 또는 사용자 문제를 더 잘 해결하는가?
2. 세 팀원 모두 로컬 실행과 장애 대응이 가능한가?
3. 테스트와 배포까지 포함한 작업량을 감당할 수 있는가?
4. 문제가 생기면 기본안으로 되돌릴 수 있는가?
5. 평가자가 데이터와 동작을 쉽게 검증할 수 있는가?

결정은 `docs/decisions/ADR-XXX.md`에 배경, 선택, 대안, 결과를 짧게 남긴다.

## 9. 범위 제외 권장 항목

다음은 과제 필수 범위가 아니므로 P0가 안정화되기 전에는 제외한다.

- 소셜 로그인, 이메일 인증, 비밀번호 재설정
- 결제, 다국어, 파일 업로드, 음성 채팅
- 벡터 DB/RAG, 에이전트 도구 호출, 모델 파인튜닝
- 마이크로서비스, Kubernetes, 복잡한 메시지 큐
- 실시간 다중 사용자 채팅



## 10. 주요 위험과 대응


| 위험              | 조기 신호                     | 대응                                          |
| --------------- | ------------------------- | ------------------------------------------- |
| API 키 노출        | 키를 코드/PR에 붙여 넣음           | `.env.example`, secret scan, 노출 키 즉시 폐기·재발급 |
| 운영 DB migration 오류 | 잘못된 Alembic revision이 Render DB에 적용됨 | additive migration 우선, revision 리뷰, PR 임시 DB 검증       |
| PR이 운영 DB를 변경   | PR 워크플로에 운영 연결 문자열이 포함됨    | CI PostgreSQL service만 사용하고 운영 secrets를 전달하지 않음 |
| Alembic head 충돌   | 두 PR이 서로 다른 head revision을 생성 | PR 병합 전 최신 `main` 기준으로 revision을 재생성하거나 merge revision 추가 |
| Render cold start | 첫 접속이 오래 걸리거나 health check가 지연됨 | 평가 전 사전 호출, 로딩 안내, 배포 URL 리허설                  |
| Render DB 만료   | 생성 30일 후 DB 접근 불가               | 제출·발표 전 만료일 확인, 필요 데이터 사전 백업                  |
| 무료 한도 초과        | 배포·대역폭·DB 용량 제한 경고            | 대시보드 사용량 확인, 불필요한 배포와 대용량 로그 억제             |
| 비밀값 커밋          | 설정 파일에 실제 운영 값 포함            | Render secret 환경 변수, 예시값만 커밋, secret scan           |
| 외부 AI API 실패    | 로컬에서는 되지만 Render에서 호출 실패   | Render 환경 변수와 공급자 설정 확인 후 배포 환경에서 실제 호출 테스트 |
| AI API 불안정/비용   | 테스트가 느리거나 호출량 급증          | 가짜 AI, 타임아웃, 공급자 사용량 점검                     |
| 사용자 간 기록 노출     | ID만으로 대화 조회               | 모든 쿼리에 현재 `user_id` 조건, 격리 테스트              |
| 문맥 길이 초과        | 대화가 길어질수록 API 오류          | 최근 N개 제한, 길이 예산, P1 요약 전략                   |
| 통합 지연           | 큰 PR, 충돌, 한 명만 실행 가능      | 작은 PR, 매일 통합, 교차 리뷰/실행                      |
| 커밋 수 미달         | 마지막 주에 몰아서 분할             | 기능·테스트·문서를 의미 있는 단위로 매주 커밋                  |
| 문서와 구현 불일치      | API/환경 변수가 README와 다름     | 릴리스 PR에서 문서 체크리스트 수행                        |




## 11. 최종 평가 체크리스트



### 기능

- [ ] 웹 페이지에서 회원가입과 로그인이 된다.
- [ ] 로그인 사용자만 챗봇 질문/응답 기능을 사용한다.
- [ ] 질문과 AI 응답을 같은 화면에서 확인한다.
- [ ] AI API는 서버에서만 호출되고 최소 문맥 전략이 적용된다.
- [ ] 사용자, 시각, 질문, 응답이 DB에 누적 저장된다.
- [ ] 사용자가 자신의 대화 로그를 조회·추적할 수 있다.
- [ ] 빈 입력 또는 길이 제한 검증이 동작한다.
- [ ] AI 실패와 타임아웃이 사용자 안내로 변환되고 서버는 계속 동작한다.



### 운영·보안

- [ ] 요청, AI 호출, AI 성공/실패, DB 저장 성공/실패 로그가 남는다.
- [ ] `.env`가 제외되고 `.env.example`과 환경 변수 설명이 있다.
- [ ] 비밀번호는 해시로 저장되고 비밀값/대화 원문은 로그에 남지 않는다.
- [ ] 외부 네트워크에서 배포 URL에 접속할 수 있다.
- [ ] Render HTTPS URL과 `/health`가 평가 기간 동안 정상 동작한다.
- [ ] 운영 데이터가 Render PostgreSQL에 저장되고 Web 재배포 후에도 유지된다.
- [ ] 배포 환경에서 선택한 AI API를 실제로 호출할 수 있다.
- [ ] PR에서 격리된 PostgreSQL에 `alembic upgrade head`를 적용한 뒤 테스트가 자동 실행된다.
- [ ] Render 시작 단계에서 `alembic upgrade head`가 성공한 뒤 앱이 실행된다.
- [ ] migration 실패 시 새 deploy가 실패하고 원인을 Render 로그에서 확인할 수 있다.
- [ ] Render Dashboard의 build/start/health check 설정이 README와 일치한다.
- [ ] 운영 비밀값과 Render DB 연결 문자열이 코드와 Git 이력에 없다.
- [ ] cold start와 Render DB 만료일을 평가 전에 점검했다.
- [ ] 평가자가 API 또는 화면으로 DB 로그를 확인할 수 있다.



### 협업·산출물

- [ ] 기능 브랜치와 PR 기반 병합 기록이 남는다.
- [ ] 팀원별 유의미한 커밋이 각각 10회 이상이다.
- [ ] README에 개요, 아키텍처, API, DB, 실행/배포, 환경 변수, 역할이 있다.
- [ ] 팀원별 실제 작업 요약이 Git 이력과 일치한다.
- [ ] 핵심 자동 테스트와 최종 수동 인수 테스트가 통과한다.



## 12. 첫 팀 회의에서 확정할 사항

- 서비스의 구체적 타겟 사용자와 챗봇 주제
- AI 공급자와 모델, 호출 비용 한도
- 사용자 식별자(이메일 또는 사용자명)와 세션 쿠키 만료 시간
- Render 계정 소유자와 팀원 접근 권한
- Render 서비스 이름, 리전과 GitHub `main` 자동 배포 설정
- Render PostgreSQL과 운영 `DATABASE_URL` 관리 담당자
- 최근 문맥 N 값과 대화방 기능 포함 여부
- 배포 담당, 백업 담당, 리뷰어 순번, 정기 통합 시간
- P1 확장 기능 최대 1~2개와 포기 기준

첫 회의 결과를 바탕으로 이 문서의 기본값을 확정하고, 각 스코프를 이슈로 분해해 담당자와 완료 조건을 연결한다.
