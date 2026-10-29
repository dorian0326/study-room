"""密码哈希（bcrypt，经 pwdlib；NFR-005）与随机令牌。"""

import hashlib
import re
import secrets
from functools import cache

from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from app.config import get_settings


@cache
def _hasher() -> PasswordHash:
    return PasswordHash((BcryptHasher(rounds=get_settings().bcrypt_rounds),))


def hash_password(password: str) -> str:
    return _hasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher().verify(password, password_hash)
    except Exception:  # 哈希格式损坏时按校验失败处理
        return False


# bcrypt 只取前 72 字节
MAX_PASSWORD_BYTES = 72


def password_problem(password: str) -> str | None:
    """返回不符合密码策略的原因；符合时返回 None。"""
    min_len = get_settings().password_min_length
    if len(password) < min_len:
        return f"密码至少 {min_len} 位"
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        return f"密码不能超过 {MAX_PASSWORD_BYTES} 字节"
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        return "密码须同时包含字母和数字"
    return None


def student_no_valid(student_no: str) -> bool:
    return re.fullmatch(get_settings().student_no_pattern, student_no) is not None


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
