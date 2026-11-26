import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(r'D:\DATA\university\3_1\Software Engineering\11.26\study-room')
TASK = Path(__file__).parent
COPY = TASK / 'checkout'
EVIDENCE = ROOT / 'docs/evidence/test/2026-11-26-full-suite'
EVIDENCE.mkdir(parents=True, exist_ok=True)
paths = subprocess.check_output(['git','-c','core.quotepath=false','ls-files','--cached','--others','--exclude-standard'], cwd=ROOT, text=True, encoding='utf-8').splitlines()
manifest=[]
excluded=[]
for name in sorted(set(paths)):
    p=ROOT/name
    if not p.is_file() or name.startswith('docs/evidence/test/2026-11-26-full-suite/'):
        continue
    if p.name.startswith('~$'):
        excluded.append({'path':name,'reason':'Office temporary lock file; unrelated to executable tests'})
        continue
    data=p.read_bytes()
    manifest.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    dest=COPY/name
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(data)
(EVIDENCE/'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(EVIDENCE/'copy-exclusions.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2),encoding='utf-8')
(EVIDENCE/'git-status-before.txt').write_text(subprocess.check_output(['git','-c','core.quotepath=false','status','--short'],cwd=ROOT,text=True,encoding='utf-8'),encoding='utf-8')
subprocess.run(['git','diff','--binary','--output='+str(EVIDENCE/'working-tree-before.patch')],cwd=ROOT,check=True)
meta={'recorded_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_root':str(ROOT),'isolated_copy':str(COPY),'test_data':'repository synthetic fixtures; isolated temporary SQLite; frontend mocked fetch/happy-dom','manifest_files':len(manifest)}
(EVIDENCE/'run-metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
