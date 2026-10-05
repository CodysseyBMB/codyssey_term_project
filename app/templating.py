from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

# 다른 파일(main.py, routers/auth.py...)이 전부 이 템플릿 객체를
# import해서 쓴다. 각자 따로 만들면 경로를 중복해서 적어야 하고,
# 나중에 templates 폴더 위치가 바뀌면 여러 곳을 고쳐야 한다.
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)