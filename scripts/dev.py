#!/usr/bin/env python3
"""本地开发一键脚本（仅用标准库，macOS / Linux / Windows 通用）。

    python scripts/dev.py setup        # 建 backend/.venv、装依赖、迁移数据库、npm ci
    python scripts/dev.py demo-data    # 创建演示账号（仅限本地开发！）
    python scripts/dev.py              # 同 dev：同时启动后端和前端，Ctrl+C 一起退出
    python scripts/dev.py test         # 后端 ruff + pytest，前端 lint/format/build
    python scripts/dev.py create-user --student-no X --name N --role admin --password P

Windows 上用 `py scripts/dev.py ...`。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / ".venv"
IS_WIN = os.name == "nt"
MIN_PY = (3, 11)
MIN_NODE = 20
BACKEND_PORT = 8000  # 前端 vite 代理写死了 8000，因此后端端口不可配置

DEMO_USERS = [
    ("A0000001", "演示管理员", "admin", "Admin1234"),
    ("O0000001", "演示运维", "ops", "Ops12345"),
    ("20260001", "演示学生", "user", "Demo1234"),
]


class DevError(Exception):
    pass


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")


def npm() -> str:
    exe = shutil.which("npm")  # Windows 上会找到 npm.cmd
    if not exe:
        raise DevError("找不到 npm，请先安装 Node.js 20+：https://nodejs.org/")
    return exe


def run(cmd: list, cwd: Path, **kw) -> subprocess.CompletedProcess:
    print(
        f"$ {' '.join(str(c) for c in cmd)}   (in {cwd.relative_to(ROOT) or '.'})",
        flush=True,
    )
    return subprocess.run([str(c) for c in cmd], cwd=cwd, **kw)


def check(cmd: list, cwd: Path) -> None:
    if run(cmd, cwd).returncode != 0:
        raise DevError(f"命令失败：{' '.join(str(c) for c in cmd)}")


def need_venv() -> Path:
    py = venv_python()
    if not py.exists():
        raise DevError("还没有 backend/.venv，请先运行：python scripts/dev.py setup")
    return py


def check_python() -> None:
    if sys.version_info < MIN_PY:
        raise DevError(
            f"需要 Python {MIN_PY[0]}.{MIN_PY[1]}+，当前是 {sys.version.split()[0]}"
        )


def check_node() -> None:
    node = shutil.which("node")
    if not node:
        raise DevError("找不到 node，请先安装 Node.js 20+：https://nodejs.org/")
    out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout
    m = re.match(r"v(\d+)", out.strip())
    if not m or int(m.group(1)) < MIN_NODE:
        raise DevError(f"需要 Node.js {MIN_NODE}+，当前是 {out.strip() or '未知'}")
    npm()


# ---------- 子命令 ----------


def cmd_setup(_: argparse.Namespace) -> int:
    check_python()
    check_node()
    if not venv_python().exists():
        check([sys.executable, "-m", "venv", VENV], BACKEND)
    py = venv_python()
    check([py, "-m", "pip", "install", "-q", "--upgrade", "pip"], BACKEND)
    check([py, "-m", "pip", "install", "-e", ".[dev]"], BACKEND)
    check([py, "-m", "alembic", "upgrade", "head"], BACKEND)
    check([npm(), "ci"], FRONTEND)
    print(
        "\n✔ 环境就绪。可选：python scripts/dev.py demo-data；"
        "然后 python scripts/dev.py dev"
    )
    return 0


def create_user(
    student_no: str, name: str, role: str, password: str
) -> subprocess.CompletedProcess:
    cmd = [need_venv(), "-m", "app.cli", "create-user", "--student-no", student_no]
    cmd += ["--name", name, "--role", role, "--password", password]
    return subprocess.run(
        [str(c) for c in cmd], cwd=BACKEND, capture_output=True, text=True
    )


def cmd_create_user(a: argparse.Namespace) -> int:
    r = create_user(a.student_no, a.name, a.role, a.password)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


def cmd_demo_data(_: argparse.Namespace) -> int:
    print("⚠ 仅限本地开发：创建弱密码演示账号，切勿在生产环境运行。")
    for sno, name, role, pw in DEMO_USERS:
        r = create_user(sno, name, role, pw)
        if r.returncode == 0:
            print(f"  已创建 {sno} / {pw}（{role}）")
        elif "已注册" in r.stderr:
            print(f"  跳过 {sno}：已存在")
        else:
            sys.stderr.write(r.stdout + r.stderr)
            return 1
    return 0


def cmd_test(_: argparse.Namespace) -> int:
    py = need_venv()
    steps = [
        ([py, "-m", "ruff", "check", "."], BACKEND),
        ([py, "-m", "ruff", "format", "--check", "."], BACKEND),
        ([py, "-m", "pytest", "-q"], BACKEND),
        ([npm(), "run", "lint"], FRONTEND),
        ([npm(), "run", "format:check"], FRONTEND),
        ([npm(), "run", "build"], FRONTEND),
    ]
    failed = [
        " ".join(str(c) for c in cmd[1:])
        for cmd, cwd in steps
        if run(cmd, cwd).returncode
    ]
    if failed:
        print("\n✘ 失败：\n  " + "\n  ".join(failed), file=sys.stderr)
        return 1
    print("\n✔ 全部通过")
    return 0


# ---------- dev：同时运行前后端 ----------


def _spawn(cmd: list, cwd: Path) -> subprocess.Popen:
    kw: dict = {}
    if IS_WIN:
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True  # 独立进程组，便于整组结束
    return subprocess.Popen(
        [str(c) for c in cmd],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        **kw,
    )


def _pump(proc: subprocess.Popen, tag: str) -> None:
    for line in proc.stdout:
        print(f"[{tag}] {line}", end="", flush=True)


def _kill_tree(proc: subprocess.Popen) -> None:
    if IS_WIN:
        # 父进程已退出时 taskkill 找不到进程树，只能结束仍存活的部分
        if proc.poll() is None:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True,
            )
    else:
        # 即使组长已退出，组内子进程（如 uvicorn worker）也可能还在，总是整组发信号
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                break
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                proc.poll()  # 回收组长，避免僵尸进程让组看起来仍存活
                try:
                    os.killpg(proc.pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.2)
            else:
                continue
            break
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def _raise_interrupt(*_: object) -> None:
    raise KeyboardInterrupt


def cmd_dev(a: argparse.Namespace) -> int:
    py = need_venv()
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, _raise_interrupt)
    if IS_WIN:
        signal.signal(signal.SIGBREAK, _raise_interrupt)
    if not (FRONTEND / "node_modules").exists():
        raise DevError("前端依赖未安装，请先运行：python scripts/dev.py setup")
    procs = {
        "backend": _spawn(
            [py, "-m", "uvicorn", "app.main:app", "--reload", "--port", BACKEND_PORT],
            BACKEND,
        ),
        "frontend": _spawn(
            [npm(), "run", "dev", "--", "--port", a.frontend_port, "--strictPort"],
            FRONTEND,
        ),
    }
    for tag, p in procs.items():
        threading.Thread(target=_pump, args=(p, tag), daemon=True).start()
    print(
        f"\n  前端：http://localhost:{a.frontend_port}\n"
        f"  后端：http://127.0.0.1:{BACKEND_PORT}/api/health\n"
        f"  接口文档：http://127.0.0.1:{BACKEND_PORT}/docs\n"
        "  按 Ctrl+C 停止\n",
        flush=True,
    )
    code = 0
    try:
        while True:
            dead = [t for t, p in procs.items() if p.poll() is not None]
            if dead:
                print(
                    f"\n[{dead[0]}] 已退出（code {procs[dead[0]].returncode}），"
                    "停止其余进程"
                )
                code = 1
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n正在停止……")
    finally:
        for p in procs.values():
            _kill_tree(p)
    return code


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="dev.py", description="study-room 本地开发脚本")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser(
        "setup", help="创建 venv、安装依赖、迁移数据库、npm ci"
    ).set_defaults(fn=cmd_setup)
    p = sub.add_parser("create-user", help="创建用户（封装 app.cli create-user）")
    p.add_argument("--student-no", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--role", required=True, choices=["admin", "ops", "user"])
    p.add_argument("--password", required=True)
    p.set_defaults(fn=cmd_create_user)
    sub.add_parser("demo-data", help="创建三个演示账号（仅限本地开发）").set_defaults(
        fn=cmd_demo_data
    )
    p = sub.add_parser("dev", help="同时启动后端(8000)和前端（默认命令）")
    p.add_argument("--frontend-port", type=int, default=5173)
    p.set_defaults(fn=cmd_dev)
    sub.add_parser("test", help="运行全部检查与测试").set_defaults(fn=cmd_test)
    return ap


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows GBK 控制台/重定向时不因 ✔⚠ 报错
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    if args.cmd is None:
        args = build_parser().parse_args(["dev"])
    try:
        check_python()
        return args.fn(args)
    except DevError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
