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
    p = sub.add_parser("seed-mock", help="导入演示 Mock 数据（仅 dev/test 环境，幂等）")
    p.add_argument("--reset", action="store_true", help="删除已有 Mock 行后重建")
    sub.add_parser("backup", help="立即备份数据库")
    sub.add_parser("list-backups", help="列出备份")
    p = sub.add_parser("restore", help="从备份恢复（必须先停止服务）")
    p.add_argument("name")
    p.add_argument("--yes", action="store_true", help="确认覆盖当前数据库")
    args = parser.parse_args(argv)

    if args.cmd in ("backup", "list-backups", "restore"):
        from app.db import engine
        from app.services import backup

        if args.cmd == "backup":
            print(backup.create_backup(engine))
        elif args.cmd == "list-backups":
            for b in backup.list_backups():
                print(b.name)
        else:
            if not args.yes:
                print("将覆盖当前数据库，请先停止服务并加 --yes 确认")
                return 1
            backup.create_backup(engine)  # 恢复前先留一份当前状态
            print("已恢复自", backup.restore_backup(engine, args.name))
        return 0

    if args.cmd == "seed-mock":
        from app import mock_data

        try:
            with SessionLocal() as session:
                created = mock_data.seed(session, reset=args.reset)
                counts = mock_data.summary(session)
        except mock_data.MockDataError as e:
            print(f"拒绝：{e}", file=sys.stderr)
            return 1
        print("已导入演示数据" if created else "演示数据已存在，跳过（加 --reset 可重建）")
        for table, n in counts.items():
            print(f"  {table}: {n}")
        return 0

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
