import json,os
from pathlib import Path
import pytest
CASES={}
def pytest_collection_modifyitems(items):
 for item in items:
  CASES[item.nodeid]={'nodeid':item.nodeid,'file':item.location[0],'line':item.location[1]+1,'parameters':{k:repr(v) for k,v in getattr(getattr(item,'callspec',None),'params',{}).items()},'phases':[]}
def pytest_runtest_logreport(report):
 if report.nodeid not in CASES:return
 r={'phase':report.when,'outcome':report.outcome,'duration_seconds':report.duration}
 if report.failed or report.skipped:r['longrepr']=str(report.longrepr)
 CASES[report.nodeid]['phases'].append(r)
def pytest_sessionfinish(session,exitstatus):
 Path(os.environ['DEFECT_RESULTS_PATH']).write_text(json.dumps({'exit_code':int(exitstatus),'cases':list(CASES.values())},ensure_ascii=False,indent=2),encoding='utf8')
