"""Build, migrate an independent demo DB, and serve the actual SPA + API.

Run with the user's webdev_3.12 Python. Original study_room.db is never selected.
"""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    backend = ROOT / "backend"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONUTF8": "1",
            "STUDYROOM_DATABASE_URL": "sqlite:///"
            + (backend / "data/course_demo.db").as_posix(),
            "STUDYROOM_ENV": "dev",
            "STUDYROOM_BACKUP_DIR": str(backend / "data/course-backups"),
        }
    )
    if not args.skip_build:
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm:
            raise SystemExit("Node/npm is required to build the frontend")
        subprocess.run([npm, "run", "build"], cwd=ROOT / "frontend", check=True)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend,
        env=env,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "app.cli", "seed-mock"], cwd=backend, env=env, check=True
    )
    if args.prepare_only:
        return
    print(
        f"Course demo: http://127.0.0.1:{args.port}/ (data/course_demo.db)", flush=True
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.port),
        ],
        cwd=backend,
        env=env,
        check=True,
    )


if __name__ == "__main__":
    main()
