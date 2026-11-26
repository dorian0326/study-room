import json, os, subprocess, sys, time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

TASK=Path(__file__).parent
EVIDENCE=Path(r'D:\DATA\university\3_1\Software Engineering\11.26\study-room\docs\evidence\test\2026-11-26-full-suite')
name=sys.argv[1]
cwd=Path(sys.argv[2])
args=sys.argv[3:]
env=os.environ.copy()
env.update({'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1','STUDYROOM_ENV':'test','NO_COLOR':'1','CI':'true'})
start=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
tick=time.perf_counter()
with (EVIDENCE/(name+'.log')).open('w',encoding='utf-8') as f:
    f.write('COMMAND: '+subprocess.list2cmdline(args)+'\nCWD: '+str(cwd)+'\nSTART: '+start+'\n\n');f.flush()
    process=subprocess.Popen(args,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
    code=process.wait()
    f.write('\nEXIT_CODE: '+str(code)+'\n')
result={'name':name,'command':args,'cwd':str(cwd),'start':start,'end':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'elapsed_seconds':round(time.perf_counter()-tick,3),'exit_code':code,'log':name+'.log'}
(EVIDENCE/(name+'-command.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
sys.exit(code)
