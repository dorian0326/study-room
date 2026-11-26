import hashlib,json,os,platform,shutil,subprocess,time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(r'D:\DATA\university\3_1\Software Engineering\11.26\study-room')
TASK=Path(__file__).parent
COPY=TASK/'checkout'
EV=ROOT/'docs/evidence/test/2026-11-26-defect-recheck'
PY=Path(r'C:\Users\zjb\AppData\Local\Temp\studyroom-test-evidence-20261126\venv\Scripts\python.exe')
EV.mkdir(parents=True,exist_ok=True)
files=[]
for folder in ['backend/app','backend/tests','backend/migrations','scripts']:
    for src in (ROOT/folder).rglob('*'):
        if not src.is_file() or '__pycache__' in src.parts or src.suffix in ('.pyc','.pyo'):continue
        rel=src.relative_to(ROOT); dest=COPY/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        data=src.read_bytes();dest.write_bytes(data)
        files.append({'path':rel.as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
for name in ['backend/pyproject.toml','backend/alembic.ini','docs/分阶段实现与测试计划.md','docs/软件需求规格说明书.md']:
    src=ROOT/name;dest=COPY/name;dest.parent.mkdir(parents=True,exist_ok=True)
    data=src.read_bytes();dest.write_bytes(data)
    files.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(EV/'source-manifest.json').write_text(json.dumps(files,ensure_ascii=False,indent=2),encoding='utf8')
(EV/'git-status-before.txt').write_text(subprocess.check_output(['git','-c','core.quotepath=false','status','--short'],cwd=ROOT,text=True,encoding='utf8'),encoding='utf8')
subprocess.run(['git','diff','--binary','--output='+str(EV/'working-tree-before.patch')],cwd=ROOT,check=True)
source_archive=['backend/app/services/reservations.py','backend/app/db.py','backend/tests/conftest.py','backend/tests/units/conftest.py','backend/tests/units/缺陷复现说明.md','docs/软件需求规格说明书.md']
source_archive += [p.relative_to(ROOT).as_posix() for p in (ROOT/'backend/tests/units').glob('test_defect_*.py')]
for name in source_archive:
    dest=EV/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(COPY/name,dest)
plugin='''import json,os\nfrom pathlib import Path\nimport pytest\nCASES={}\ndef pytest_collection_modifyitems(items):\n for item in items:\n  CASES[item.nodeid]={'nodeid':item.nodeid,'file':item.location[0],'line':item.location[1]+1,'parameters':{k:repr(v) for k,v in getattr(getattr(item,'callspec',None),'params',{}).items()},'phases':[]}\ndef pytest_runtest_logreport(report):\n if report.nodeid not in CASES:return\n r={'phase':report.when,'outcome':report.outcome,'duration_seconds':report.duration}\n if report.failed or report.skipped:r['longrepr']=str(report.longrepr)\n CASES[report.nodeid]['phases'].append(r)\ndef pytest_sessionfinish(session,exitstatus):\n Path(os.environ['DEFECT_RESULTS_PATH']).write_text(json.dumps({'exit_code':int(exitstatus),'cases':list(CASES.values())},ensure_ascii=False,indent=2),encoding='utf8')\n'''
(TASK/'defect_evidence_plugin.py').write_text(plugin,encoding='utf8')
env=os.environ.copy();env.update({'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(TASK),'STUDYROOM_ENV':'test','NO_COLOR':'1'})
meta={'date':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_root':str(ROOT),'isolated_copy':str(COPY),'python_executable':str(PY),'platform':platform.platform(),'scope':'backend targeted SRS defect tests and complete backend regression; frontend not re-run','modifications':'No changes to business code, tests or assertions; no xfail added. External plugin only records pytest reports.'}
(EV/'run-metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
def run(name,args):
    cmd=[str(PY),'-m','pytest']+args+['-p','defect_evidence_plugin','-p','no:cacheprovider','--junitxml='+str(EV/(name+'-junit.xml'))]
    env['DEFECT_RESULTS_PATH']=str(EV/(name+'-case-results.json'))
    start=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat();tick=time.perf_counter()
    with (EV/(name+'.log')).open('w',encoding='utf8') as log:
        log.write('COMMAND: '+subprocess.list2cmdline(cmd)+'\nCWD: '+str(COPY/'backend')+'\nSTART: '+start+'\n\n');log.flush()
        result=subprocess.run(cmd,cwd=COPY/'backend',env=env,stdout=log,stderr=subprocess.STDOUT)
        log.write('\nEXIT_CODE: '+str(result.returncode)+'\n')
    record={'name':name,'command':cmd,'cwd':str(COPY/'backend'),'start':start,'end':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'elapsed_seconds':round(time.perf_counter()-tick,3),'exit_code':result.returncode,'log':name+'.log'}
    (EV/(name+'-command.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(record,ensure_ascii=False),flush=True)
run('defects-only',['tests/units','-k','test_srs','-vv','--tb=short'])
run('backend-regression',['-vv','--tb=short'])
with (EV/'environment.log').open('w',encoding='utf8') as log:
    subprocess.run([str(PY),'--version'],stdout=log,stderr=subprocess.STDOUT)
    subprocess.run([str(PY),'-m','pip','freeze'],stdout=log,stderr=subprocess.STDOUT)
tools=EV/'tooling';tools.mkdir(exist_ok=True)
for name in ['prepare_and_run.py','defect_evidence_plugin.py']:shutil.copy2(TASK/name,tools/name)
