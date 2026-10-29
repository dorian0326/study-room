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

## 参与贡献

请先阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)。向 `main` 的改动须经 Pull Request，并由 CODEOWNERS（@dorian0326）审核通过后才能合并。

## 许可证

[MIT](./LICENSE) © 2026 Dorian Zhang
