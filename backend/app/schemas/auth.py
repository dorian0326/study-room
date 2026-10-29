from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AccountStatus, RoleName


class RegisterIn(BaseModel):
    student_no: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    department: str | None = Field(default=None, max_length=128)
    contact: str | None = Field(default=None, max_length=128)


class LoginIn(BaseModel):
    student_no: str
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordIn(BaseModel):
    student_no: str
    reset_code: str
    new_password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    name: str
    department: str | None
    contact: str | None
    status: AccountStatus
    roles: list[RoleName]


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ResetCodeOut(BaseModel):
    reset_code: str
    expires_in: int
