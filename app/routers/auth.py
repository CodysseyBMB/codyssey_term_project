from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access_control import (
    get_or_create_csrf_token,
    require_form_csrf,
    require_page_user,
)
from app.db import get_db
from app.models import User
from app.security import hash_password, verify_password
from app.templating import templates

# APIRouter = 경로들의 묶음. main.py에서 include_router()로 앱에 연결한다.
# prefix="/auth"를 주면 아래 "/signup"은 실제로 "/auth/signup"이 된다.
router = APIRouter(prefix="/auth", tags=["auth"])

INVALID_CREDENTIALS_MESSAGE = "아이디 또는 비밀번호가 올바르지 않습니다."


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": None,
            "username": "",
            "csrf_token": get_or_create_csrf_token(request),
        },
    )


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    _csrf: None = Depends(require_form_csrf),
    db: Session = Depends(get_db),
):
    username = username.strip()
    if not (3 <= len(username) <= 20) or not (8 <= len(password) <= 100):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "아이디는 3~20자, 비밀번호는 8~100자 사이로 입력해주세요.",
                "username": username,
                "csrf_token": get_or_create_csrf_token(request),
            },
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": INVALID_CREDENTIALS_MESSAGE,
                "username": username,
                "csrf_token": get_or_create_csrf_token(request),
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout(
    request: Request,
    _current_user: User = Depends(require_page_user),
    _csrf: None = Depends(require_form_csrf),
):
    request.session.clear()
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(
        "session",
        path="/",
        secure=request.app.state.settings.is_production,
        httponly=True,
        samesite="lax",
    )
    return response

@router.get("/signup", response_class=HTMLResponse)
def signup_form(request: Request):
    # GET: 빈 회원가입 폼 화면만 보여준다.
    return templates.TemplateResponse(
        request = request,
        name = "signup.html",
        context={
            "error": None,
            "csrf_token": get_or_create_csrf_token(request),
        },
    )

@router.post("/signup", response_class=HTMLResponse)
def signup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...), # Form(...)의 ...은 필수값이라는 뜻
    _csrf: None = Depends(require_form_csrf),
    db: Session = Depends(get_db), # get_db가 세션을 자동으로 넣어준다.
):
    username = username.strip()

    # 입력 검증: 너무 짧거나 긴 아이디/비밀번호 거부
    if not (3 <= len(username) <= 20) or not (8 <= len(password) <= 100):
        return templates.TemplateResponse(
            request = request,
            name = "signup.html",
            context = {
                "error": "아이디는 3~20자, 비밀번호는 8~100자 사이로 입력해주세요.",
                "csrf_token": get_or_create_csrf_token(request),
            },
            status_code = 422,
        )

    # 완료 조건: 평문이 이나리 해시만 저장
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # username에 unique = True가 있어서, 중복 가입시 DB가 예외를 던진다.
        # 여기서 잡아 "이미 존재하는 아이디"로 안내한다 (완료 조건 2번).
        db.rollback()
        return templates.TemplateResponse(
            request = request,
            name="signup.html",
            context={
                "error": "이미 사용 중인 아이디입니다.",
                "csrf_token": get_or_create_csrf_token(request),
            },
            status_code = 409,
        )

    # 303 See Other: POST 처리 결과를 GET으로 다시 보여주라는 뜻.
    # 새로고침해도 폼이 중복 제출되지 않는다.
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
