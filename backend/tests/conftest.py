import os
import tempfile
from pathlib import Path

# 测试使用临时 SQLite 文件，须在导入 app 之前设置
_tmp = tempfile.mkdtemp()
os.environ["STUDYROOM_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["STUDYROOM_BCRYPT_ROUNDS"] = "4"
os.environ["STUDYROOM_RESERVATION_SWEEP_INTERVAL_SECONDS"] = "0"
os.environ["STUDYROOM_BACKUP_INTERVAL_SECONDS"] = "0"
os.environ["STUDYROOM_LOG_PURGE_INTERVAL_SECONDS"] = "0"
os.environ.setdefault("STUDYROOM_ENV", "test")

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_cfg(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture
def api_db(tmp_path):
    """每个测试一个全新、已迁移到 head 的数据库，返回 sessionmaker。"""
    from app.db import make_engine

    url = f"sqlite:///{tmp_path}/api.db"
    command.upgrade(alembic_cfg(url), "head")
    eng = make_engine(url)
    yield sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    eng.dispose()


@pytest.fixture
def client(api_db):
    from app.db import get_session
    from app.main import create_app

    app = create_app()

    def _session():
        with api_db() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_user(api_db):
    """直接在库中建用户（可指定角色），返回 (student_no, password)。"""
    from app.models import Role, User
    from app.security import hash_password

    def _make(student_no="20260001", password="secret123", roles=("user",), **kw):
        with api_db() as s:
            role_objs = list(s.scalars(select(Role).where(Role.name.in_(roles))))
            s.add(
                User(
                    student_no=student_no,
                    name=kw.pop("name", "测试用户"),
                    password_hash=hash_password(password),
                    roles=role_objs,
                    **kw,
                )
            )
            s.commit()
        return student_no, password

    return _make


@pytest.fixture
def login(client):
    """登录并返回带 Authorization 头的 dict。"""

    def _login(student_no, password):
        r = client.post("/api/auth/login", json={"student_no": student_no, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _login
