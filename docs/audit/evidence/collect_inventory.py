"""Phase-one read-only inventory; run from any directory with Python 3.11+."""
import hashlib
import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    srs = ROOT / "需求规格说明书.md"
    teacher = Path("C:/Users/zjb/Downloads/架构设计后确认与分阶段实现操作指引_学生版.md")
    manifest = {
        "captured_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "sources": [{"path": str(p), "sha256": sha(p)} for p in (srs, teacher)],
        "tracked_files": subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines(),
    }
    links = []
    for line, value in enumerate(srs.read_text(encoding="utf-8").splitlines(), 1):
        for target in re.findall(r"\]\(([^)]+)\)", value):
            if not target.startswith(("http:", "https:", "#")):
                target_path = srs.parent / target.split("#")[0]
                links.append({"line": line, "target": target, "exists": target_path.exists()})
    manifest["srs_links"] = links
    manifest["note"] = "Read-only schema and aggregate counts; no user rows, tokens or password hashes exported."
    path = ROOT / "backend/data/study_room.db"
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        schema = {"path": "backend/data/study_room.db", "access": "mode=ro + query_only", "journal_mode": db.execute("PRAGMA journal_mode").fetchone()[0], "integrity_check": db.execute("PRAGMA integrity_check").fetchone()[0], "foreign_key_check": db.execute("PRAGMA foreign_key_check").fetchall(), "alembic_version": db.execute("SELECT version_num FROM alembic_version").fetchall(), "tables": {}}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            schema["tables"][table] = {
                "count": db.execute(f"SELECT count(*) FROM {quoted}").fetchone()[0],
                "columns": db.execute(f"PRAGMA table_info({quoted})").fetchall(),
                "foreign_keys": db.execute(f"PRAGMA foreign_key_list({quoted})").fetchall(),
                "indexes": db.execute(f"PRAGMA index_list({quoted})").fetchall(),
                "ddl": db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0],
            }
        schema["index_ddl"] = db.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name").fetchall()
    finally:
        db.close()
    (OUT / "inventory.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "database-schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"head": manifest["head"], "tables": len(tables), "counts": {k: v["count"] for k, v in schema["tables"].items()}, "version": schema["alembic_version"], "integrity": schema["integrity_check"], "foreign_key_errors": len(schema["foreign_key_check"]), "srs_link_occurrences": len(links), "missing_link_occurrences": sum(not x["exists"] for x in links)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
