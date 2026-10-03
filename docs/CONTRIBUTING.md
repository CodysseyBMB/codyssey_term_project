# 기여 가이드

## 작업 흐름

이 저장소는 GitHub Flow를 사용합니다.

1. GitHub 이슈에 목적, 구현 범위, 완료 조건과 테스트 방법을 기록합니다.
2. 최신 `main`에서 이슈 번호를 포함한 브랜치를 만듭니다.
3. 실행 가능한 작은 단위로 커밋합니다.
4. `main`을 대상으로 Pull Request를 생성하고 `Closes #이슈번호`를 적습니다.
5. CI 성공과 작성자 외 한 명 이상의 승인을 받은 뒤 병합합니다.

브랜치 예시:

```text
feature/12-chat-service
fix/21-session-expiry
docs/5-contributing-guide
```

## 커밋과 PR

커밋과 PR 제목에는 다음 접두사를 사용합니다.

- `feat:` 기능
- `fix:` 결함 수정
- `test:` 테스트
- `docs:` 문서
- `chore:` 설정과 유지보수
- `refactor:` 동작 변경 없는 구조 개선

한 PR은 가능한 한 하나의 이슈를 해결해야 합니다. 화면 변경은 캡처를 첨부하고, 변경한 동작을 검증하는 테스트나 명확한 수동 검증 절차를 포함합니다.

`main` 직접 push, force push, CI 실패 상태의 병합과 승인 없는 self-merge는 허용하지 않습니다.

## 로컬 검증

PR을 열기 전에 다음을 실행합니다.

```bash
ruff check .
pytest
```

## DB 변경

1. SQLAlchemy 모델을 먼저 수정합니다.
2. `alembic revision --autogenerate -m "설명"`으로 초안을 만듭니다.
3. `upgrade()`와 `downgrade()`를 직접 검토합니다.
4. 빈 DB에서 upgrade하고, 지원 범위에서 downgrade 후 다시 upgrade합니다.
5. 공유되거나 운영에 적용된 revision은 수정하지 않습니다.

서로 다른 PR에서 Alembic head가 갈라지면 최신 `main`을 반영한 뒤 revision을 재생성하거나 명시적인 merge revision을 추가합니다.

## 협업 기록

팀원별 유의미한 커밋 10회 이상을 기능, 테스트, 문서 작업 과정에서 자연스럽게 누적합니다. 역할은 소유권이지 독점 작업이 아니며 인증, AI와 배포 영역은 다른 팀원이 최소 한 번 리뷰하고 직접 실행합니다.
