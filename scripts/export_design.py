"""Export actual OpenAPI and migrated schema into reviewable design appendices."""

import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    output = ROOT / "docs/design"
    evidence = ROOT / "evidence/20261125"
    output.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="course-design-") as temp:
        os.environ["STUDYROOM_DATABASE_URL"] = (
            "sqlite:///" + (Path(temp) / "design.db").as_posix()
        )
        os.environ["STUDYROOM_ENV"] = "test"
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import inspect
        from app.db import engine
        from app.main import create_app

        cfg = Config(str(ROOT / "backend/alembic.ini"))
        cfg.set_main_option("script_location", str(ROOT / "backend/migrations"))
        with engine.connect() as connection:
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
        schema = create_app().openapi()
        (evidence / "openapi.json").write_text(
            json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        lines = [
            "# 接口字段附录",
            "",
            "日期2026-11-25；由实际应用OpenAPI生成。业务约束见[接口与关键设计](接口与关键设计说明书.md)。",
            "",
            "目录：逐方法接口 → 请求/响应schema。所有非公开路由仍受服务端鉴权；schema不表示人工已确认。",
            "",
        ]
        index = 0
        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                if method not in {"get", "post", "put", "patch", "delete"}:
                    continue
                index += 1
                lines += [
                    f"## API-{index:03d} / {method.upper()} {path}",
                    "",
                    operation.get("description", operation.get("summary", "")),
                    "",
                    f"处理函数：`{operation.get('operationId', '')}`。",
                    "",
                    "| 位置 | 字段 | 必填 | 类型/约束 |",
                    "|---|---|---|---|",
                ]
                for param in operation.get("parameters", []):
                    value = json.dumps(
                        param.get("schema", {}), ensure_ascii=False
                    ).replace("|", "\\|")
                    lines.append(
                        f"| {param['in']} | {param['name']} | {param.get('required', False)} | `{value}` |"
                    )
                if "requestBody" in operation:
                    body = operation["requestBody"]
                    for mime, content in body.get("content", {}).items():
                        value = json.dumps(
                            content.get("schema", {}), ensure_ascii=False
                        ).replace("|", "\\|")
                        lines.append(
                            f"| body ({mime}) | JSON | {body.get('required', False)} | `{value}` |"
                        )
                lines += [
                    "",
                    "响应：",
                    "",
                    "```json",
                    json.dumps(operation["responses"], ensure_ascii=False, indent=2),
                    "```",
                    "",
                ]
        lines += [
            "## 数据结构定义",
            "",
            "字段必填由required列表给出；nullable/anyOf/长度/范围见JSON。",
            "",
            "```json",
            json.dumps(
                schema.get("components", {}).get("schemas", {}),
                ensure_ascii=False,
                indent=2,
            ),
            "```",
            "",
        ]
        (output / "接口字段附录.md").write_text("\n".join(lines), encoding="utf-8")
        inspector = inspect(engine)
        tables = {}
        db_lines = [
            "# 数据库设计说明书",
            "",
            "版本DB-20261125；从独立SQLite经Alembic迁移0001～0008后读取，未改原业务库。目录：概念关系 → 逐表逻辑/物理结构 → 事务与数据操作。",
            "",
            "## 1. 概念结构与关系",
            "",
            "```mermaid",
            "erDiagram",
            "    users ||--o{ reservations : owns",
            "    study_rooms ||--o{ seats : contains",
            "    study_rooms ||--o{ opening_schedules : defines",
            "    seats ||--o{ reservations : assigned",
            "    reservations ||--o{ arrival_records : records",
            "    users ||--o{ violation_records : incurs",
            "    users ||--o{ restrictions : receives",
            "    violation_records ||--o{ appeals : disputed",
            "    users ||--o{ notifications : receives",
            "    users ||--o{ auth_sessions : opens",
            "    users ||--o{ user_roles : links",
            "    roles ||--o{ user_roles : links",
            "    roles ||--o{ role_permissions : grants",
            "    permissions ||--o{ role_permissions : grants",
            "```",
            "",
            "区域为seats.zone_type，不单独建zones；暂离在reservations字段；门禁HMAC键与用户为逻辑关联，reservation_id为外键。arrival_records.reservation_id没有唯一约束，ER按真实DB表示1:N而非伪称强制1:1。",
            "",
            "## 2. 逐表逻辑与物理结构",
            "",
            "SQLite VARCHAR长度声明不自动强制长度；API校验和CHECK分别承担约束。时区日期由LocalDateTime转Asia/Shanghai无时区存储，读出补时区。无版本锁列。",
            "",
        ]
        for table in inspector.get_table_names():
            columns = inspector.get_columns(table)
            fks = inspector.get_foreign_keys(table)
            indexes = inspector.get_indexes(table)
            checks = inspector.get_check_constraints(table)
            unique = inspector.get_unique_constraints(table)
            pk = inspector.get_pk_constraint(table)
            tables[table] = dict(
                columns=columns,
                foreign_keys=fks,
                indexes=indexes,
                checks=checks,
                unique=unique,
                primary_key=pk,
            )
            db_lines += [
                f"### {table}",
                "",
                "| 字段 | SQL类型/长度 | 可空 | 主键 | 默认 |",
                "|---|---|---|---|---|",
            ]
            for col in columns:
                db_lines.append(
                    f"| {col['name']} | {col['type']} | {col['nullable']} | {col['name'] in pk['constrained_columns']} | {col.get('default')} |"
                )
            for title, values in [
                ("外键", fks),
                ("唯一约束", unique),
                ("索引", indexes),
                ("CHECK", checks),
            ]:
                db_lines += [
                    "",
                    f"{title}：",
                    "",
                    "```json",
                    json.dumps(values, ensure_ascii=False, indent=2, default=str),
                    "```",
                ]
            db_lines += [""]
        db_lines += [
            "## 3. 关键操作、事务与迁移",
            "",
            "预约创建在BEGIN IMMEDIATE内查开放与座位/本人重叠，写预约/到达/通知；换座同步到达引用；取消、违规/限制、申诉、设施取消按同事务规则。详情见接口与关键设计。部分唯一索引(seat_id,start_time)仅约束相同起点，任意交叠由写锁内区间查询保证。幂等键/通知键/门禁来源事件号分别唯一，NULL可多条。",
            "",
            "0001核心表、0002认证、0003权限快照、0004设置校历、0005登录日志、0006通知/门禁扩展、0007楼层/指纹、0008暂离违规类型。当前修复不新增迁移。外键删除RESTRICT保留预约/用户历史，关联清理CASCADE与SET NULL逐表如上；禁止用删除历史数据代替业务归档。",
            "",
            "SQLite WAL、foreign_keys=ON、busy_timeout=5000ms；一致快照备份和停服恢复不代表RPO0。测试用独立文件库与多连接，执行证据不包含密码/token。",
            "",
        ]
        (output / "数据库设计说明书.md").write_text(
            "\n".join(db_lines), encoding="utf-8"
        )
        (evidence / "migrated-schema.json").write_text(
            json.dumps(tables, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        engine.dispose()
        print(f"Exported {index} API operations and {len(tables)} tables")


if __name__ == "__main__":
    main()
