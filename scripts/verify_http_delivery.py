"""Actual HTTP flow, 200-client load, and isolated SQLite snapshot recovery."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
from threading import Barrier
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    import httpx
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    evidence = ROOT / "evidence/20261125"
    evidence.mkdir(parents=True, exist_ok=True)
    # Keep fixture paths out of tracked source and never target the user's DB.
    with tempfile.TemporaryDirectory(
        prefix="course-http-", ignore_cleanup_errors=True
    ) as temp:
        db_path = Path(temp) / "http.db"
        os.environ.update(
            {
                "STUDYROOM_DATABASE_URL": "sqlite:///" + db_path.as_posix(),
                "STUDYROOM_ENV": "test",
                "STUDYROOM_BCRYPT_ROUNDS": "4",
                "STUDYROOM_RESERVATION_SWEEP_INTERVAL_SECONDS": "0",
                "STUDYROOM_BACKUP_DIR": str(Path(temp) / "backups"),
            }
        )
        from app.db import engine
        from app.models import Role, User, StudyRoom, Seat, OpeningSchedule
        from app.models import enums as E
        from app.security import hash_password
        from app.timeutil import now
        from app.services.backup import create_backup, restore_backup
        from datetime import time as daytime

        cfg = Config(str(ROOT / "backend/alembic.ini"))
        cfg.set_main_option("script_location", str(ROOT / "backend/migrations"))
        with engine.connect() as connection:
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
        with Session(engine) as session:
            roles = {r.name: r for r in session.scalars(select(Role))}
            hashed = hash_password("Course1234")
            for i in range(200):
                session.add(
                    User(
                        student_no=f"LOAD{i:04}",
                        name="合成负载用户",
                        password_hash=hashed,
                        roles=[roles[E.RoleName.USER]],
                    )
                )
            session.add(
                User(
                    student_no="HTTPADMIN",
                    name="合成管理员",
                    password_hash=hashed,
                    roles=[roles[E.RoleName.ADMIN]],
                )
            )
            session.add(
                User(
                    student_no="HTTPOPS1",
                    name="合成运维",
                    password_hash=hashed,
                    roles=[roles[E.RoleName.OPS]],
                )
            )
            room = StudyRoom(name="HTTP隔离室", capacity=3)
            seats = [
                Seat(room=room, code=str(i), zone_type=E.ZoneType.QUIET)
                for i in (1, 2, 3)
            ]
            session.add_all([room, *seats])
            session.flush()
            for kind in E.DayType:
                session.add(
                    OpeningSchedule(
                        room_id=room.id,
                        day_type=kind,
                        open_time=daytime(6),
                        close_time=daytime(23, 30),
                    )
                )
            session.commit()
            seat_id = seats[0].id
            race_seat_id = seats[1].id
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        with (evidence / "http-server.txt").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=ROOT / "backend",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            try:
                client = httpx.Client(
                    base_url=f"http://127.0.0.1:{port}",
                    timeout=60,
                    limits=httpx.Limits(
                        max_connections=250, max_keepalive_connections=220
                    ),
                    trust_env=False,
                )
                for _ in range(80):
                    try:
                        if client.get("/api/health").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.25)
                steps = []

                def expect(name, response, code):
                    steps.append(
                        {"name": name, "status": response.status_code, "expected": code}
                    )
                    assert response.status_code == code, (
                        name,
                        response.status_code,
                        response.text,
                    )
                    return response

                def login(name):
                    r = expect(
                        "login:" + name,
                        client.post(
                            "/api/auth/login",
                            json={"student_no": name, "password": "Course1234"},
                        ),
                        200,
                    )
                    return {"Authorization": "Bearer " + r.json()["access_token"]}

                headers = [login(f"LOAD{i:04}") for i in range(200)]
                admin, ops = login("HTTPADMIN"), login("HTTPOPS1")
                expect("built SPA", client.get("/workflows"), 200)
                expect("unknown API stays 404", client.get("/api/missing"), 404)
                expect("anonymous denied", client.get("/api/rooms"), 401)
                expect(
                    "student admin denied",
                    client.get("/api/admin/reservations", headers=headers[0]),
                    403,
                )
                moment = now()
                start = moment + timedelta(seconds=5)
                if not (6 <= start.hour < 22):
                    raise RuntimeError(
                        "Run HTTP check during the configured 06:00-22:00 window"
                    )
                body = {
                    "seat_id": seat_id,
                    "start_time": start.isoformat(),
                    "end_time": (start + timedelta(hours=1)).isoformat(),
                    "request_key": "http-flow-request-001",
                }
                booking = expect(
                    "create",
                    client.post("/api/reservations", headers=headers[0], json=body),
                    201,
                ).json()
                rid = booking["id"]
                replay = expect(
                    "same key replay",
                    client.post("/api/reservations", headers=headers[0], json=body),
                    201,
                ).json()
                assert replay["id"] == rid
                expect(
                    "blank checkin denied",
                    client.post(
                        f"/api/reservations/{rid}/check-in", headers=headers[0]
                    ),
                    422,
                )
                expect(
                    "checkin",
                    client.post(
                        f"/api/reservations/{rid}/check-in",
                        headers=headers[0],
                        json={"seat_id": seat_id},
                    ),
                    200,
                )
                expect(
                    "temporary leave",
                    client.post(
                        f"/api/reservations/{rid}/temporary-leave", headers=headers[0]
                    ),
                    200,
                )
                expect(
                    "manual return denied",
                    client.post(f"/api/reservations/{rid}/return", headers=headers[0]),
                    409,
                )
                from app.services.gate import user_key_for_gate

                # Leave time may precede start; ENTRY must be after the actual leave, not invented.
                gate_body = {
                    "external_id": "http-gate-001",
                    "source_system": "course-http-mock",
                    "masked_user_key": user_key_for_gate("LOAD0000"),
                    "record_type": "entry",
                    "recorded_at": now().isoformat(),
                    "reservation_id": rid,
                }
                gate = expect(
                    "mock gate return",
                    client.post(
                        "/api/ops/entry-exit/mock", headers=ops, json=gate_body
                    ),
                    200,
                ).json()
                assert gate["sync_status"] == "synced", gate
                expect(
                    "end",
                    client.post(
                        f"/api/reservations/{rid}/end",
                        headers=headers[0],
                        json={"confirm": True},
                    ),
                    200,
                )
                history = expect(
                    "history",
                    client.get("/api/reservations?scope=history", headers=headers[0]),
                    200,
                ).json()
                assert any(
                    row["id"] == rid and row["status"] == "COMPLETED" for row in history
                )
                expect(
                    "notifications",
                    client.get("/api/notifications", headers=headers[0]),
                    200,
                )
                expect(
                    "admin gate denied",
                    client.get("/api/ops/entry-exit/records", headers=admin),
                    403,
                )
                expect(
                    "ops gate audit",
                    client.get("/api/ops/entry-exit/records", headers=ops),
                    200,
                )

                def load_batch(kind):
                    barrier = Barrier(200)

                    def request(i):
                        barrier.wait(timeout=30)
                        t = time.perf_counter()
                        if kind == "read":
                            response = client.get("/api/rooms", headers=headers[i])
                        else:
                            payload = dict(
                                body,
                                seat_id=race_seat_id,
                                request_key=f"http-race-{i:04}",
                                start_time=(start + timedelta(minutes=2)).isoformat(),
                            )
                            response = client.post(
                                "/api/reservations", headers=headers[i], json=payload
                            )
                        return {
                            "client": i,
                            "status": response.status_code,
                            "ms": round((time.perf_counter() - t) * 1000, 3),
                        }

                    with ThreadPoolExecutor(max_workers=200) as pool:
                        rows = list(pool.map(request, range(200)))
                    values = sorted(row["ms"] for row in rows)
                    statuses = {
                        str(code): sum(r["status"] == code for r in rows)
                        for code in sorted({r["status"] for r in rows})
                    }
                    return {
                        "clients": 200,
                        "rounds": 1,
                        "p95_ms": values[189],
                        "max_ms": values[-1],
                        "statuses": statuses,
                        "p95_target_ms": 2000,
                        "p95_pass": values[189] <= 2000,
                        "samples": rows,
                    }

                reads = load_batch("read")
                race = load_batch("write")
                with sqlite3.connect(db_path) as db:
                    winners = db.execute(
                        "SELECT count(*) FROM reservations WHERE seat_id=? AND status='RESERVED'",
                        (race_seat_id,),
                    ).fetchone()[0]
                race["final_reservations"] = winners
                race["zero_oversell_pass"] = (
                    winners == 1 and race["statuses"].get("201", 0) == 1
                )
                expect(
                    "admin report", client.get("/api/admin/reports", headers=admin), 200
                )
                expect(
                    "export xlsx",
                    client.get("/api/admin/reports/export.xlsx", headers=admin),
                    200,
                )
                client.close()
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

        def snapshot():
            with sqlite3.connect(db_path) as db:
                tables = [
                    r[0]
                    for r in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                ]
                return {
                    table: sorted(
                        [list(r) for r in db.execute('SELECT * FROM "' + table + '"')],
                        key=repr,
                    )
                    for table in tables
                }

        before = snapshot()
        backup = create_backup(engine)
        with engine.begin() as conn:
            from sqlalchemy import text

            conn.execute(text("UPDATE study_rooms SET name='after-snapshot-change'"))
        assert snapshot() != before
        t = time.perf_counter()
        restore_backup(engine, backup.name)
        recovered = snapshot()
        recovery = {
            "tables_compared": len(before),
            "all_rows_match_snapshot": recovered == before,
            "restore_seconds": round(time.perf_counter() - t, 4),
            "rpo_zero_proven": False,
            "note": "Stopped isolated server, restored exact snapshot; subsequent changes intentionally absent.",
        }
        result = {
            "environment": "local Windows / webdev_3.12 / one Uvicorn worker / fresh migrated SQLite",
            "http_steps": steps,
            "read_load": reads,
            "write_race": race,
            "recovery": recovery,
            "limitations": [
                "One synthetic 200-client burst; no soak test or production capacity claim",
                "Simulated gate only",
                "No monthly availability or calibrated NTP evidence",
            ],
        }
        (evidence / "http-performance-recovery.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "steps": len(steps),
                    "read_p95_ms": reads["p95_ms"],
                    "write_p95_ms": race["p95_ms"],
                    "write_statuses": race["statuses"],
                    "zero_oversell": race["zero_oversell_pass"],
                    "recovery": recovery,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        engine.dispose()
        assert recovery["all_rows_match_snapshot"] and race["zero_oversell_pass"]


if __name__ == "__main__":
    main()
