"""Fallback for stalled pip index resolution; install pure wheels into audit venv only."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / "backend/.venv/Lib/site-packages"


def fetch(name):
    with urlopen(f"https://pypi.org/pypi/{name}/json", timeout=30) as response:
        metadata = json.load(response)
    artifact = next(item for item in metadata["urls"] if item["filename"].endswith("py3-none-any.whl"))
    with urlopen(artifact["url"], timeout=30) as response:
        content = response.read()
    import hashlib
    assert hashlib.sha256(content).hexdigest() == artifact["digests"]["sha256"]
    with ZipFile(BytesIO(content)) as wheel:
        for item in wheel.infolist():
            target = (DEST / item.filename).resolve()
            if not target.is_relative_to(DEST.resolve()):
                raise ValueError("Invalid wheel member")
        wheel.extractall(DEST)
    return {"name": name, "version": metadata["info"]["version"], "wheel": artifact["filename"], "sha256": artifact["digests"]["sha256"]}


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch, ["alembic", "pwdlib", "mako"]))
    (Path(__file__).parent / "dependency-wheels.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2), flush=True)
