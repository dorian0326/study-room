"""External evidence collector: does not change application or test assertions."""
import json, threading, os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

DEST=Path(r'D:\DATA\university\3_1\Software Engineering\11.26\study-room\docs\evidence\test\2026-11-26-full-suite')
CASES={}
ACTIVE=None
LOCK=threading.Lock()
ORIGINAL=None
ORIGINAL_CREATE=None

def sanitize(value, key=''):
    if any(x in key.lower() for x in ('password','token','authorization','reset_code','secret','masked_user_key')):
        return '[redacted]'
    if isinstance(value,dict): return {k:sanitize(v,k) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [sanitize(x) for x in value[:8]]+([{'_remaining_items':len(value)-8}] if len(value)>8 else [])
    if isinstance(value,str): return value[:3000]+('...[truncated]' if len(value)>3000 else '')
    return value

def pytest_collection_modifyitems(items):
    for item in items:
        mark=item.get_closest_marker('case')
        CASES[item.nodeid]={'nodeid':item.nodeid,'file':item.location[0],'line':item.location[1]+1,'function':getattr(item,'originalname',None) or item.name.split('[')[0], 'parameters':{k:sanitize(repr(v),k) for k,v in getattr(getattr(item,'callspec',None),'params',{}).items()},'fixtures':item.fixturenames,'case_marker':mark.args[0] if mark and mark.args else None,'phases':[], 'http':[]}

@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    global ORIGINAL, ORIGINAL_CREATE
    from starlette.testclient import TestClient
    ORIGINAL=TestClient.request
    def recorded(client,method,url,*args,**kwargs):
        case=ACTIVE
        response=ORIGINAL(client,method,url,*args,**kwargs)
        if case in CASES:
            content_type=response.headers.get('content-type','')
            try: output=sanitize(response.json()) if 'json' in content_type else {'content_type':content_type,'bytes':len(response.content)}
            except Exception: output={'bytes':len(response.content)}
            record={'method':method,'url':str(url),'status':response.status_code,'request_json':sanitize(kwargs.get('json')),'response':output}
            with LOCK: CASES[case]['http'].append(record)
        return response
    TestClient.request=recorded
    if os.environ.get('CAPTURE_SERVICE_CREATE')=='1':
        from app.services import reservations
        ORIGINAL_CREATE=reservations.create
        def captured_create(*args,**kwargs):
            case=ACTIVE
            record={'user_id':args[1] if len(args)>1 else kwargs.get('user_id')}
            try:
                result,replay=ORIGINAL_CREATE(*args,**kwargs)
                record.update({'outcome':'success','reservation_id':result.id,'replay':replay,'status':str(result.status)})
                return result,replay
            except Exception as exc:
                record.update({'outcome':'error','exception':type(exc).__name__,'status_code':getattr(exc,'status_code',None),'message':str(exc)})
                raise
            finally:
                if case in CASES:
                    with LOCK: CASES[case].setdefault('service_create',[]).append(record)
        reservations.create=captured_create

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    global ACTIVE
    ACTIVE=item.nodeid

def pytest_runtest_logreport(report):
    if report.nodeid not in CASES:return
    data={'when':report.when,'outcome':report.outcome,'duration_seconds':report.duration}
    if report.failed or report.skipped:data['longrepr']=str(report.longrepr)
    CASES[report.nodeid]['phases'].append(data)

def pytest_sessionfinish(session,exitstatus):
    if ORIGINAL:
        from starlette.testclient import TestClient
        TestClient.request=ORIGINAL
    if ORIGINAL_CREATE:
        from app.services import reservations
        reservations.create=ORIGINAL_CREATE
    payload={'recorded_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'exitstatus':int(exitstatus),'capture':'TestClient request/response from actual isolated pytest run; secrets redacted, arrays sampled to 8, long strings truncated at 3000','cases':list(CASES.values())}
    (DEST/os.environ.get('EVIDENCE_CASE_REPORT','backend-case-results.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
