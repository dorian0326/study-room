"""Migrate and boot an isolated local backend, then stop only its own process."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
OUT = Path(__file__).resolve().parent
PYTHON = BACKEND / ".venv/Scripts/python.exe"


def main():
    with tempfile.TemporaryDirectory(prefix="audit-smoke-", dir=BACKEND / ".venv") as temporary:
        env = os.environ.copy()
        env.update({"STUDYROOM_DATABASE_URL": "sqlite:///" + (Path(temporary) / "smoke.db").as_posix(), "STUDYROOM_ENV": "test", "STUDYROOM_RESERVATION_SWEEP_INTERVAL_SECONDS": "0", "STUDYROOM_BACKUP_INTERVAL_SECONDS": "0", "STUDYROOM_LOG_PURGE_INTERVAL_SECONDS": "0"})
        with (OUT / "startup-smoke-server.txt").open("w", encoding="utf-8") as log:
            migration = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT)
            if migration.returncode:
                raise RuntimeError("Isolated migration failed")
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            process = subprocess.Popen([str(PYTHON), "-X", "utf8", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                base = f"http://127.0.0.1:{port}"
                health = None
                for _ in range(60):
                    if process.poll() is not None:
                        raise RuntimeError("Uvicorn exited before readiness")
                    try:
                        with urlopen(base + "/api/health", timeout=1) as response:
                            health = {"status": response.status, "body": json.load(response)}
                        break
                    except OSError:
                        time.sleep(0.25)
                if health is None:
                    raise RuntimeError("Backend readiness timeout")
                with urlopen(base + "/openapi.json", timeout=5) as response:
                    schema = json.load(response)
                routes = [{"method": method.upper(), "path": path, "operation_id": operation.get("operationId")} for path, methods in schema["paths"].items() for method, operation in methods.items() if method in {"get", "post", "put", "patch", "delete"}]
                try:
                    urlopen(base + "/api/rooms", timeout=5)
                    unauthenticated_status = 200
                except HTTPError as error:
                    unauthenticated_status = error.code
                result = {"database": "new temporary database under backend/.venv; migrated to head; removed after process shutdown", "migration_exit": migration.returncode, "health": health, "unauthenticated_rooms_status": unauthenticated_status, "routes": routes}
                assert health["status"] == 200 and unauthenticated_status == 401
                (OUT / "startup-smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps({"health": health, "unauthenticated_rooms_status": unauthenticated_status, "api_operations": len(routes)}, ensure_ascii=False, indent=2))
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
