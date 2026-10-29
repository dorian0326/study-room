"""认证接口（FR-001~004，UC-001~003）。"""

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.deps import AuthDep, CurrentUser, SessionDep
from app.models import User
from app.permissions import permissions_of
from app.schemas.auth import (
    ChangePasswordIn,
    LoginIn,
    LoginOut,
    RegisterIn,
    ResetPasswordIn,
    UserOut,
)
from app.services import auth as svc
from app.services.logs import record_login

router = APIRouter(prefix="/auth", tags=["auth"])


def _err(e: svc.AuthError) -> HTTPException:
    return HTTPException(e.status, detail={"code": e.code, "message": e.message})


def user_out(user) -> UserOut:  # noqa: ANN001
    return UserOut(
        id=user.id,
        student_no=user.student_no,
        name=user.name,
        department=user.department,
        contact=user.contact,
        status=user.status,
        roles=sorted(r.name for r in user.roles),
        permissions=sorted(permissions_of(r.name for r in user.roles)),
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register(body: RegisterIn, session: SessionDep) -> UserOut:
    try:
        user = svc.register(
            session,
            student_no=body.student_no,
            name=body.name,
            password=body.password,
            department=body.department,
            contact=body.contact,
        )
    except svc.AuthError as e:
        raise _err(e) from e
    return user_out(user)


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, request: Request, session: SessionDep) -> LoginOut:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    log = {"student_no": body.student_no, "ip": ip, "user_agent": ua}
    try:
        user = svc.authenticate(session, body.student_no, body.password)
    except svc.AuthError as e:
        known = session.scalar(select(User).where(User.student_no == body.student_no.strip()))
        record_login(session, user=known, success=False, reason=e.code, **log)
        raise _err(e) from e
    token, ttl = svc.create_session(session, user, ip=ip, user_agent=ua)
    record_login(session, user=user, success=True, **log)
    return LoginOut(access_token=token, expires_in=ttl, user=user_out(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(auth: AuthDep, session: SessionDep, request: Request) -> None:
    svc.revoke_session(session, auth[1])
    record_login(
        session,
        student_no=auth[0].student_no,
        user=auth[0],
        event="logout",
        success=True,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return user_out(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: ChangePasswordIn, user: CurrentUser, session: SessionDep) -> None:
    try:
        svc.change_password(session, user, body.old_password, body.new_password)
    except svc.AuthError as e:
        raise _err(e) from e


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(body: ResetPasswordIn, session: SessionDep) -> None:
    try:
        svc.reset_password(session, body.student_no, body.reset_code, body.new_password)
    except svc.AuthError as e:
        raise _err(e) from e


__all__ = ["router", "user_out"]
