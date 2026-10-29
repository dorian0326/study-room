# 智慧自习室管理系统（study-room）

面向高校多间自习室的统一管理平台：把座位查看、智能预约、签到签退和违规治理放到线上，提升座位利用率与管理效率。

本仓库对应软件工程课程设计项目《智慧自习室管理系统》，开发与交付曾依托华为云 CodeArts（代码托管、持续集成、自动化部署与持续测试），并结合 ECS 对外提供访问。

## 能做什么

**用户端**
- 学号/工号注册登录，访客 / 学生 / 管理员分级
- 可视化查看座位状态（未开放 / 空闲 / 已预约）
- 按半小时粒度预约、取消；预约前后签到签退
- 查询预约记录与违规记录

**管理员端**
- 自习室与座位的增删改
- 用户维护、信誉分与封禁处罚
- 预约干预、利用率与资源浪费监控
- 手动/自动违规标记

**核心逻辑**
- 座位时段冲突检测
- 超时未签到/签退自动释放并记违规
- 预约状态机（已预约 → 已签到 → 已签退等）

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy 2 / Alembic |
| 数据库 | SQLite（WAL 模式） |
| 前端 | Vue 3 + Vite |
| 工程实践 | 敏捷（Scrum）双迭代，DevOps / CodeArts 流水线 |

## 本地开发

> 时间基准统一为 Asia/Shanghai（UTC+8，HD-39），后端通过 `app.timeutil.now()` 取当前时间。

### 一键脚本（推荐）

`scripts/dev.py` 只用 Python 标准库，macOS / Linux / Windows 通用。需要 Python 3.11+、Node.js 20+。

```bash
# macOS / Linux 用 python3；Windows 用 py（Python 启动器），也可用 python
python3 scripts/dev.py setup       # 建 backend/.venv、装依赖、迁移数据库、npm ci
python3 scripts/dev.py             # 迁移 + 自动导入演示数据，再同时启动后端 :8000 和前端 :5173，Ctrl+C 一起停止
python3 scripts/dev.py test        # ruff + pytest + 前端 lint/format:check/build
python3 scripts/dev.py create-user --student-no A0001 --name 张三 --role admin --password Passw0rd
```

```powershell
py scripts\dev.py setup
py scripts\dev.py
```

### 演示数据 / 助教运行说明

`python3 scripts/dev.py`（Windows：`py scripts\dev.py`）启动前会自动执行数据库迁移并导入一组 Mock 数据，启动后终端会打印演示账号。首次 `setup` 后直接运行这一条即可看到完整页面效果。

| 账号 | 密码 | 角色 | 说明 |
| --- | --- | --- | --- |
| `A0000001` | `Admin1234` | 管理员 | 报表、申诉审核、日志、座位/用户/配置管理 |
| `O0000001` | `Ops12345` | 运维 | 运维面板、闸机 |
| `20260001` | `Demo1234` | 学生 | 主演示账号，有历史预约（开放时段内导入时还有进行中的预约） |
| `20260002` | `Demo1234` | 学生 | 暂离中（开放时段内导入时） |
| `20260004` | `Demo1234` | 学生 | 有待审核申诉、明天的预约 |
| `20260014` | `Demo1234` | 学生 | 违规累计已被限制预约，有待审核申诉 |
| `20260015` | `Demo1234` | 学生 | 已停用，登录返回 403 |

其余学生 `20260003`–`20260013` 密码同为 `Demo1234`。数据包括 4 个自习室、40 个座位（1 个维修中）、16 条开放时段、节假日/考试周日历，以及近 14 天约 200 条预约（完成、取消、超时取消、管理员取消、爽约、暂离超时）、违规与申诉（待审/通过/驳回）、闸机进出、登录日志、操作日志和通知。数据按导入时刻生成，均符合业务规则（无时段冲突、在开放时间内、每人最多 1 个有效预约）。

- 已导入过则自动跳过，不会重复或覆盖你自己的数据；只删除/重建 Mock 数据用 `python3 scripts/dev.py --reset-mock`。
- 不想导入：`python3 scripts/dev.py --no-mock`。单独导入：`python3 scripts/dev.py demo-data [--reset]` 或 `cd backend && python -m app.cli seed-mock [--reset]`。
- 仅当 `STUDYROOM_ENV` 为 `dev` 或 `test` 时才会导入，其他环境会拒绝。
- 时间相关的状态（进行中、暂离、明天的预约）以导入时刻为准；隔天演示时运行一次 `--reset-mock` 刷新。

前端端口可用 `dev --frontend-port 5174` 修改；后端固定 8000，因为前端 `/api` 代理写死了这个端口。
不需要先激活虚拟环境。下面的手动步骤仍然可用。

### 后端（`backend/`）

需要 Python 3.11 及以上。

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head               # 初始化 / 升级 SQLite 数据库（默认 backend/data/study_room.db）
uvicorn app.main:app --reload      # http://127.0.0.1:8000/api/health
pytest                             # 运行测试
ruff check . && ruff format --check .   # 代码检查
```

配置通过环境变量覆盖（前缀 `STUDYROOM_`），参考 `backend/.env.example`。

### 前端（`frontend/`）

需要 Node.js 20 及以上。

```bash
cd frontend
npm ci
npm run dev       # http://localhost:5173，/api 自动代理到 8000 端口
npm run lint      # ESLint
npm run build     # 生产构建
```

### CI

推送和 PR 会触发 GitHub Actions（`.github/workflows/ci.yml`），运行后端 ruff + pytest 与前端 lint + build。

## 已知限制

实现与需求文档的有意差异见 [docs/limitations.md](./docs/limitations.md)。

## 参与贡献

请先阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)。向 `main` 的改动须经 Pull Request，并由 CODEOWNERS（@dorian0326）审核通过后才能合并。

## 许可证

[MIT](./LICENSE) © 2026 Dorian Zhang

## 部署环境变量

| 变量 | 说明 |
| --- | --- |
| `STUDYROOM_ENV` | 运行环境，默认 `dev`；测试用 `test`，部署设为 `prod` 等其他值。 |
| `STUDYROOM_GATE_HMAC_SECRET` | 门禁脱敏用户键的 HMAC 密钥。`STUDYROOM_ENV` 不是 `dev`/`test` 时必须设置为独立随机值，否则后端拒绝启动。 |
| `STUDYROOM_LOGIN_MAX_FAILURES` | 连续登录失败锁定阈值，默认 `5`；`0` 关闭锁定。 |
| `STUDYROOM_LOGIN_LOCKOUT_MINUTES` | 登录锁定分钟数，默认 `15`。 |
| `STUDYROOM_BACKUP_INTERVAL_SECONDS` | 定时备份间隔（秒），默认 `0`（关闭）；生产可设 `86400`。CLI `python -m app.cli backup` 仍可用。 |
| `STUDYROOM_LOG_PURGE_INTERVAL_SECONDS` | 定时日志清理间隔（秒），默认 `0`；保留天数见 `STUDYROOM_LOG_RETENTION_DAYS`（默认 180，约一学期）。CLI `python -m app.cli purge-logs` 仍可用。 |
