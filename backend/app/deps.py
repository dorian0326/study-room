"""FastAPI 公共依赖：数据库会话与当前用户。"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import AuthSession, User
from app.models.enums import AccountStatus
from app.services.auth import user_for_token

SessionDep = Annotated[Session, Depends(get_session)]
_bearer = HTTPBearer(auto_error=False)


def get_auth(
    request: Request,
    session: SessionDep,
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> tuple[User, AuthSession]:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "请先登录")
    found = user_for_token(session, cred.credentials)
    if found is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录已失效，请重新登录")
    user, auth = found
    if user.status != AccountStatus.NORMAL:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账户已被禁用，请联系管理员")
    request.state.user = user
    return user, auth


AuthDep = Annotated[tuple[User, AuthSession], Depends(get_auth)]


def get_current_user(auth: AuthDep) -> User:
    return auth[0]


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(code: str):
    """依赖工厂：当前用户的任一角色拥有该权限才放行，否则 403。"""
    from app.permissions import roles_for

    allowed = roles_for(code)

    def _check(user: CurrentUser) -> User:
        if not any(r.name in allowed for r in user.roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "无权限执行此操作")
        return user

    return _check


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
