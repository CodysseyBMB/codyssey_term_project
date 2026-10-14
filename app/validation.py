from __future__ import annotations

import re

# 아이디 정책: 영문 대소문자/숫자/밑줄/하이픈만 허용, 3~20자.
# - 공백·한글·이모지 등 다른 유니코드 문자는 허용하지 않는다 (ASCII로 제한).
# - 대소문자를 구분한다 (예: "Whale01"과 "whale01"은 다른 아이디다).
# - HTML(login.html, signup.html)의 minlength/maxlength/pattern, DB 컬럼(String(20))과
#   길이를 반드시 동일하게 맞춘다 — 셋 중 하나만 바꾸면 다시 불일치가 생긴다.
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 20
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

# 비밀번호 정책: 길이만 8~100자로 제한하고, 문자 종류는 제한하지 않는다
# (공백·유니코드·이모지 포함 전부 허용). 더 다양한 문자를 허용할수록
# 사용자가 암호를 더 안전하게 만들 여지가 커진다.
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 100

USERNAME_POLICY_MESSAGE = (
    f"아이디는 영문, 숫자, '_', '-'만 사용해 "
    f"{USERNAME_MIN_LENGTH}~{USERNAME_MAX_LENGTH}자로 입력해주세요."
)
PASSWORD_POLICY_MESSAGE = (
    f"비밀번호는 {PASSWORD_MIN_LENGTH}~{PASSWORD_MAX_LENGTH}자 사이로 입력해주세요."
)


def is_valid_username(username: str) -> bool:
    return (
        USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH
        and USERNAME_PATTERN.fullmatch(username) is not None
    )


def is_valid_password(password: str) -> bool:
    # 길이만 검사한다. 비밀번호는 여기서도, 호출하는 쪽(routers/auth.py)에서도
    # strip()이나 다른 가공을 하지 않고 원문 그대로 hash_password에 넘긴다.
    return PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH
