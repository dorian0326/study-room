# 智慧自习室管理系统（study-room）

面向高校多间自习室的统一管理平台：把座位查看、预约、签到签退和违规治理放到线上，提升座位利用率与管理效率。本仓库是软件工程课程设计项目《智慧自习室管理系统》的代码。

**两种查看方式：**

- **在线演示（免安装）**：<http://47.98.18.65/>，接口文档 <http://47.98.18.65/docs>
- **本地运行**：装好 Python 3.11+ 和 Node.js 20+ 后执行 `python scripts/dev.py setup`，再执行 `python scripts/dev.py`

## 目录

- [功能概览](#功能概览)
- [技术栈](#技术栈)
- [方式一：在线演示](#方式一在线演示)
- [演示账号](#演示账号)
- [建议演示路线](#建议演示路线)
- [方式二：本地运行](#方式二本地运行)
  - [一键脚本（推荐）](#一键脚本推荐)
  - [演示数据](#演示数据)
  - [手动启动后端与前端](#手动启动后端与前端)
  - [测试与检查](#测试与检查)
  - [常见问题](#常见问题)
- [目录结构](#目录结构)
- [配置（环境变量）](#配置环境变量)
- [CI 与分支规则](#ci-与分支规则)
- [相关文档](#相关文档)
- [许可证](#许可证)

## 功能概览

| 角色 | 功能 |
| --- | --- |
| 学生 | 学号注册、登录、找回和修改密码；按自习室、楼层、设施（电源、靠窗、无障碍）查找座位，或只选区域让系统自动分座；创建、改座、取消预约（冲突检测，迟取消会提示）；扫码或手输签到、暂离、结束；查看历史预约、违规记录并提交申诉；接收通知 |
| 管理员 | 自习室、开放时段、节假日和系统参数配置；座位维护（含 CSV 导入）；用户管理、角色和停用；违规申诉审核；统计报表 |
| 运维 | 系统日志与登录日志；备份和监控面板；闸机出入馆记录 |

系统自动处理的规则：超时未签到释放座位并记违规；暂离超过 30 分钟记违规；违规累计后限制预约，违规按周期归档；关闭自习室或改开放时间时取消受影响的预约并通知；连续登录失败锁定账号。所有时间按 Asia/Shanghai（UTC+8）计算。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11+、FastAPI、SQLAlchemy 2、Alembic、pwdlib（bcrypt） |
| 数据库 | SQLite（WAL 模式，外键开启，关键写操作用立即事务） |
| 前端 | Vue 3、Vite 6、vue-router，ESLint 9 和 Prettier |
| 工程 | GitHub Actions CI，Issue 加 PR 协作，`main` 分支受保护 |

## 方式一：在线演示

打开 <http://47.98.18.65/>，用下方的[演示账号](#演示账号)登录即可。Swagger 接口文档在 <http://47.98.18.65/docs>。

注意：

- 只有 HTTP，没有 HTTPS，请不要输入任何真实密码。
- 这是**公共演示环境**，所有人共用同一套数据，别人的操作可能改变你看到的内容。
- 数据都是 Mock 数据，按导入时间生成。导入时间在开放时段（07:00–22:30）之外时，不会有"使用中"和"暂离中"的预约。想要一份干净、时间准确的数据，请用本地运行。

## 演示账号

在线演示和本地运行使用同一组账号：

| 账号 | 密码 | 角色 | 说明 |
| --- | --- | --- | --- |
| `A0000001` | `Admin1234` | 管理员 | 报表、申诉审核、日志、座位/用户/配置管理 |
| `O0000001` | `Ops12345` | 运维 | 运维面板、闸机 |
| `20260001` | `Demo1234` | 学生 | 主演示账号，有历史预约（开放时段内导入时还有进行中的预约） |
| `20260002` | `Demo1234` | 学生 | 暂离中（开放时段内导入时） |
| `20260004` | `Demo1234` | 学生 | 有待审核申诉、明天的预约 |
| `20260014` | `Demo1234` | 学生 | 违规累计已被限制预约，有待审核申诉 |
| `20260015` | `Demo1234` | 学生 | 已停用，登录返回 403 |

其余学生 `20260003`–`20260013` 的密码都是 `Demo1234`。

## 建议演示路线

大约 10 分钟，按顺序走一遍：

1. **学生 `20260001`**
   - "首页"：看当前预约和提醒。
   - "预约"：按自习室、楼层、设施筛选座位，点开座位详情，创建一个预约；再试改座和取消（迟取消会二次确认）；也可以只选区域让系统自动分座。
   - "签到"：输入或扫描座位码签到，再试暂离和结束。
   - "违规"：看违规记录、提交申诉；"通知"：看系统通知。
2. **学生 `20260014`**：尝试预约，会被提示违规限制中。**`20260015`**：登录被拒绝（账号已停用）。
3. **管理员 `A0000001`**
   - "自习室配置"：开放时段、节假日、参数；"座位管理"：增删改座位、标记维修。
   - "用户管理"：查看、停用用户；"申诉处理"：审核 `20260004` 等人的申诉。
   - "统计报表"：利用率等统计。
4. **运维 `O0000001`**："系统日志"、"备份监控"（可手动备份）、"出入馆记录"。
5. 接口：打开 `/docs`，在 Swagger 里直接调用接口。

## 方式二：本地运行

### 前置条件

- Python **3.11 及以上**（macOS 和 Linux 用 `python3`，Windows 用 `py` 或 `python`）
- Node.js **20 及以上**（自带 npm）
- Git

```bash
git clone https://github.com/dorian0326/study-room.git
cd study-room
```

### 一键脚本（推荐）

`scripts/dev.py` 只依赖 Python 标准库，macOS、Linux、Windows 都能用，不用先激活虚拟环境。

```bash
python3 scripts/dev.py setup   # 第一次运行：建 backend/.venv、装后端依赖、迁移数据库、npm ci
python3 scripts/dev.py         # 迁移数据库、自动导入演示数据，同时启动后端和前端
```

```powershell
# Windows（PowerShell 或 CMD）
py scripts\dev.py setup
py scripts\dev.py
```

启动后：

- 前端：<http://localhost:5173>
- 后端健康检查：<http://127.0.0.1:8000/api/health>
- 接口文档：<http://127.0.0.1:8000/docs>
- 在终端按 **Ctrl+C** 同时停止前后端。

其他子命令和参数：

| 命令 | 作用 |
| --- | --- |
| `python3 scripts/dev.py --no-mock` | 启动，但不导入演示数据 |
| `python3 scripts/dev.py --reset-mock` | 删除并重建演示数据，再启动 |
| `python3 scripts/dev.py --frontend-port 5174` | 换前端端口（后端固定 8000，因为前端 `/api` 代理写死了这个端口） |
| `python3 scripts/dev.py demo-data [--reset]` | 只导入（或重建）演示数据，不启动服务 |
| `python3 scripts/dev.py test` | 运行全部检查和测试 |
| `python3 scripts/dev.py create-user --student-no A0001 --name 张三 --role admin --password Passw0rd` | 创建用户 |

### 演示数据

每次运行 `python3 scripts/dev.py` 都会先执行数据库迁移，再导入 Mock 数据，终端会打印演示账号表（同[演示账号](#演示账号)）。

- 数据包括 17 个用户、4 个自习室、40 个座位（1 个维修中）、16 条开放时段、节假日和考试周日历，近 14 天约 200 条各种状态的预约，以及违规、申诉、闸机进出、登录和操作日志、通知。数据都符合业务规则。
- 已经导入过就自动跳过，不会覆盖你自己的数据。
- 时间相关的状态（使用中、暂离中、明天的预约）以导入时间为准。隔天演示前，建议在开放时段内运行一次 `--reset-mock`。
- 只有 `STUDYROOM_ENV` 是 `dev`（默认）或 `test` 时才会导入，其他环境会拒绝。

### 手动启动后端与前端

后端（`backend/`）：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head               # 建库或升级，默认 backend/data/study_room.db
python -m app.cli seed-mock        # 可选：导入演示数据（--reset 重建）
uvicorn app.main:app --reload      # http://127.0.0.1:8000/api/health
```

前端（`frontend/`，另开一个终端）：

```bash
cd frontend
npm ci
npm run dev                        # http://localhost:5173，/api 代理到 8000 端口
```

### 测试与检查

一条命令全部跑完：`python3 scripts/dev.py test`（ruff、pytest、前端 lint、format:check、build）。

也可以分开跑：

```bash
cd backend && pytest && ruff check . && ruff format --check .
cd frontend && npm run lint && npm run format:check && npm run build
```

### 常见问题

| 问题 | 解决 |
| --- | --- |
| 提示"还没有 backend/.venv"或"前端依赖未安装" | 先运行 `python3 scripts/dev.py setup` |
| 8000 端口被占用 | 关掉占用 8000 的程序（macOS/Linux：`lsof -i :8000`；Windows：`netstat -ano \| findstr :8000`）。后端端口不能改 |
| 5173 端口被占用 | 用 `--frontend-port 5174` 换端口 |
| `npm ci` 报错或前端启动失败 | 检查 `node -v` 是否在 20 以上 |
| Windows 上找不到 `python3` | 用 `py scripts\dev.py` |
| 后端拒绝启动，提示 HMAC 密钥 | `STUDYROOM_ENV` 被设成了 `dev`、`test` 以外的值。本地开发不要设置它（默认 `dev`），或设为 `dev` |
| 想清空数据重来 | 停掉服务，删除 `backend/data/study_room.db`（以及同目录的 `-wal`、`-shm` 文件），再运行 `python3 scripts/dev.py`；只重建演示数据用 `--reset-mock` |

## 目录结构

```text
study-room/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # 路由：认证、预约、闸机、管理端、报表、运维等
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # 请求和响应模型
│   │   ├── services/        # 业务逻辑
│   │   ├── cli.py           # 命令行：create-user、seed-mock、backup、purge-logs 等
│   │   ├── mock_data.py     # 演示数据生成
│   │   └── main.py          # 应用入口
│   ├── migrations/          # Alembic 迁移
│   ├── tests/               # pytest 测试
│   ├── .env.example         # 环境变量示例
│   └── pyproject.toml
├── frontend/                # Vue 3 + Vite 前端
│   └── src/
│       ├── api/  components/  router/  assets/
│       └── views/           # 页面：登录、首页、预约、签到、违规、通知、管理端、运维
├── scripts/dev.py           # 跨平台一键脚本
├── docs/                    # 已知限制、预约模块进度
├── .github/workflows/ci.yml # CI
├── CONTRIBUTING.md
└── LICENSE
```

## 配置（环境变量）

配置都用前缀为 `STUDYROOM_` 的环境变量覆盖，示例见 `backend/.env.example`。本地开发不用设置任何变量。

| 变量 | 说明 |
| --- | --- |
| `STUDYROOM_ENV` | 运行环境，默认 `dev`；测试用 `test`，部署设为 `prod` 等其他值。 |
| `STUDYROOM_GATE_HMAC_SECRET` | 门禁脱敏用户键的 HMAC 密钥。`STUDYROOM_ENV` 不是 `dev`/`test` 时必须设置为独立随机值，否则后端拒绝启动。 |
| `STUDYROOM_LOGIN_MAX_FAILURES` | 连续登录失败锁定阈值，默认 `5`；`0` 关闭锁定。 |
| `STUDYROOM_LOGIN_LOCKOUT_MINUTES` | 登录锁定分钟数，默认 `15`。 |
| `STUDYROOM_BACKUP_INTERVAL_SECONDS` | 定时备份间隔（秒），默认 `0`（关闭）；生产可设 `86400`。CLI `python -m app.cli backup` 仍可用。 |
| `STUDYROOM_LOG_PURGE_INTERVAL_SECONDS` | 定时日志清理间隔（秒），默认 `0`；保留天数见 `STUDYROOM_LOG_RETENTION_DAYS`（默认 180，约一学期）。CLI `python -m app.cli purge-logs` 仍可用。 |

## CI 与分支规则

- 每次推送和 PR 都会触发 GitHub Actions（`.github/workflows/ci.yml`）：后端 ruff 和 pytest（Python 3.11），前端 lint、format:check 和 build（Node 20）。
- `main` 受保护：改动必须走 Pull Request，CI 通过，并由 CODEOWNERS（@dorian0326）审核后 squash 合并。详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 相关文档

- [docs/limitations.md](./docs/limitations.md)：实现和需求文档的有意差异（门禁是模拟的、并发控制方式、未做压测等）
- [docs/reservation-progress.md](./docs/reservation-progress.md)：Issue #10–#16 预约模块后端阶段交付记录（历史文档）
- [CONTRIBUTING.md](./CONTRIBUTING.md)：协作和提交规范

## 许可证

[MIT](./LICENSE) © 2026 Dorian Zhang
