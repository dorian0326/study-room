"""Validate local delivery links and build a reproducible source/document package."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = ROOT / "evidence/20261125"
    errors = []
    checked = 0
    for base in (ROOT / "docs", ROOT / "docs/design", ROOT / "docs/testing", ROOT / "docs/requirements"):
        for path in base.glob("*.md"):
            if path.name in {"limitations.md", "reservation-progress.md"}:
                continue  # preserved historical documents have known missing upstream links
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if target.startswith(("http:", "https:", "#")):
                    continue
                checked += 1
                if not (path.parent / target.split("#")[0]).exists():
                    errors.append(f"Broken link {path.relative_to(ROOT)} -> {target}")
    files = []
    for base_name in ("backend", "frontend", "scripts", "docs", "tasks", "evidence", ".github"):
        for path in (ROOT / base_name).rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if any(part in {".venv", "node_modules", "dist", "data", "__pycache__", ".pytest_cache", ".ruff_cache"} or part.endswith(".egg-info") for part in rel.parts):
                continue
            if path.suffix in {".db", ".pyc", ".sqlite3"} or path.name == ".env":
                continue
            if rel.as_posix() == "evidence/20261125/delivery-manifest.json":
                continue
            files.append(path)
    files.extend(path for path in ROOT.iterdir() if path.is_file() and path.name in {"README.md", "CONTRIBUTING.md", "LICENSE", ".gitignore", "需求规格说明书.md"})
    records = [{"path": p.relative_to(ROOT).as_posix(), "bytes":p.stat().st_size,
                "sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
    manifest = {"source_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                "branch":subprocess.check_output(["git","branch","--show-current"],cwd=ROOT,text=True).strip(),
                "working_tree_uncommitted":True,"local_links_checked":checked,"errors":errors,"files":records}
    manifest_path = evidence / "delivery-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if errors:
        print(json.dumps(errors, ensure_ascii=False, indent=2)); raise SystemExit(1)
    output = ROOT / "deliverables"
    output.mkdir(exist_ok=True)
    archive = output / "NAILONG-course-delivery-20261125.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as package:
        for path in files + [manifest_path]:
            package.write(path, "NAILONG-ZIXISHI/" + path.relative_to(ROOT).as_posix())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256.txt").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(json.dumps({"files":len(records)+1,"links_checked":checked,"zip":str(archive),"bytes":archive.stat().st_size,"sha256":digest},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
