"""运维命令行。首个管理员只能由此创建（注册接口只发「用户」角色）。

python -m app.cli create-user --student-no A0001 --name 管理员 --role admin
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal, transaction
from app.models import Role, User
from app.models.enums import RoleName
from app.services import auth as auth_svc


def create_user(student_no: str, name: str, password: str, roles: list[str]) -> User:
    with SessionLocal() as session:
        user = auth_svc.register(session, student_no=student_no, name=name, password=password)
        with transaction(session):
            user.roles = list(session.scalars(select(Role).where(Role.name.in_(roles))))
        return user


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-user", help="创建用户并指定角色")
    p.add_argument("--student-no", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--role", action="append", choices=[r.value for r in RoleName])
    p.add_argument("--password", help="不传则交互输入")
    p = sub.add_parser("purge-logs", help="清理超过保留期的操作日志与登录日志")
    p.add_argument("--days", type=int, help="保留天数，默认取 STUDYROOM_LOG_RETENTION_DAYS")
    args = parser.parse_args(argv)

    if args.cmd == "purge-logs":
        from app.services.logs import purge_expired

        with SessionLocal() as session:
            print(purge_expired(session, args.days))
        return 0

    if args.cmd == "create-user":
        password = args.password or getpass.getpass("密码：")
        try:
            user = create_user(args.student_no, args.name, password, args.role or ["user"])
        except auth_svc.AuthError as e:
            print(f"失败：{e.message}", file=sys.stderr)
            return 1
        print(f"已创建用户 {user.student_no}，角色：{', '.join(args.role or ['user'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
