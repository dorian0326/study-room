"""Check audit outputs, source preservation, evidence counts and local links."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "docs/audit"
OUT = Path(__file__).resolve().parent


def main():
    required = ["老师任务要求清单.md", "项目现状分析报告.md", "需求追踪矩阵.md", "文档缺失与问题清单.md", "后续实施计划.md"]
    errors = []
    for name in required:
        p = AUDIT / name
        if not p.is_file() or not p.read_text(encoding="utf-8").startswith("# "):
            errors.append("Missing or untitled output: " + name)
    manifest = json.loads((OUT / "inventory.json").read_text(encoding="utf-8"))
    for source in manifest["sources"]:
        p = Path(source["path"])
        if hashlib.sha256(p.read_bytes()).hexdigest() != source["sha256"]:
            errors.append("Original source changed: " + str(p))
    if subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", "backend", "frontend", "scripts", "README.md", "CONTRIBUTING.md"], cwd=ROOT, capture_output=True).returncode:
        errors.append("Existing tracked application files changed")
    link_count = 0
    for p in AUDIT.rglob("*.md"):
        content = p.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if target.startswith(("http:", "https:", "#")):
                continue
            link_count += 1
            if not (p.parent / target.split("#")[0]).exists():
                errors.append(f"Broken audit link: {p.name}: {target}")
        for number, line in enumerate(content.splitlines(), 1):
            if line.startswith("|") and not line.endswith("|"):
                errors.append(f"Malformed table: {p.name}:{number}")
    counts = {}
    for name in ("pytest-existing", "pytest-audit", "pytest-controls"):
        suites = ElementTree.parse(OUT / (name + ".xml")).getroot().findall("testsuite")
        counts[name] = {key: sum(int(s.get(key, "0")) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    expected = {"pytest-existing": (116, 2, 0), "pytest-audit": (10, 10, 0), "pytest-controls": (2, 0, 0)}
    for name, (tests, failures, failures_setup) in expected.items():
        row = counts[name]
        if (row["tests"], row["failures"], row["errors"]) != (tests, failures, failures_setup):
            errors.append("Unexpected result counts: " + name)
    schema = json.loads((OUT / "database-schema.json").read_text(encoding="utf-8"))
    with sqlite3.connect((ROOT / "backend/data/study_room.db").as_uri() + "?mode=ro", uri=True) as db:
        for table, prior in schema["tables"].items():
            quoted = '"' + table.replace('"', '""') + '"'
            if db.execute(f"SELECT count(*) FROM {quoted}").fetchone()[0] != prior["count"]:
                errors.append("Original database row count changed: " + table)
    result = {"required_documents": required, "local_audit_links_checked": link_count, "original_sources_unchanged": True if not any("source changed" in e for e in errors) else False, "test_counts": counts, "errors": errors}
    (OUT / "delivery-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
