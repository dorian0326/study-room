from pathlib import Path
import json,hashlib,re,xml.etree.ElementTree as ET,shutil,platform,subprocess
from openpyxl import load_workbook

ROOT=Path(r'D:/DATA/university/3_1/Software Engineering/11.26/study-room')
TASK=Path(__file__).parent
EV=ROOT/'docs/evidence/test/2026-11-26-full-suite'
cases=json.loads((EV/'test-cases.json').read_text(encoding='utf8'))
manifest=json.loads((EV/'source-manifest.json').read_text(encoding='utf8'))
changed=[]
for x in manifest:
    p=ROOT/x['path']
    digest=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    if digest!=x['sha256']:changed.append({'path':x['path'],'before_sha256':x['sha256'],'after_sha256':digest,'category':'existing-document-edited-during-run' if x['path'].startswith('docs/') else 'source-change'})
assert not [x for x in changed if x['category']=='source-change'],changed
(EV/'source-comparison-after.json').write_text(json.dumps({'checked_files':len(manifest),'original_source_and_tests_unchanged':True,'changed_existing_documents':changed,'note':'These changes were observed in the shared workspace, not produced by the test/document generation scripts; do not overwrite. Tests use the before-run isolated snapshot.'},ensure_ascii=False,indent=2),encoding='utf8')
note='执行结束校验发现三份既有架构／接口文档在共享工作区发生其他编辑变化，已保留，详见source-comparison-after.json；前后端源码及测试内容SHA-256未变化，测试对应执行前隔离快照。'
report=ROOT/'docs/单元与集成测试案例及执行报告.md'
text=report.read_text(encoding='utf8')
anchor='- 本轮Python/Node高于CI配置的Python 3.11/Node 20；本地通过不直接证明CI环境也通过。'
if note not in text:text=text.replace(anchor,anchor+'\n- '+note)
report.write_text(text.rstrip()+'\n',encoding='utf8')
readme=EV/'README.md'
rd=readme.read_text(encoding='utf8')
if note not in rd:rd+='\n'+note+'\n'
readme.write_text(rd.rstrip()+'\n',encoding='utf8')
tooling=EV/'tooling'
for name in ['build_workbook.mjs','verify_and_finalize.py']:
    shutil.copy2(TASK/name,tooling/name)
compile_script=(tooling/'compile_report.py').read_text(encoding='utf8')
compile_script=compile_script.replace(anchor,anchor+'\n- '+note)
(tooling/'compile_report.py').write_text(compile_script,encoding='utf8')

junit=ET.parse(EV/'backend-junit.xml').getroot()
xmlcases=list(junit.iter('testcase'))
front=json.loads((EV/'frontend-vitest.json').read_text(encoding='utf8'))
book=load_workbook(ROOT/'docs/测试用例表.xlsx',data_only=False)
cache=load_workbook(ROOT/'docs/测试用例表.xlsx',data_only=True)
s=book['测试用例表'];index=book['证据索引']
ids=[s.cell(r,2).value for r in range(6,256)]
assert len(cases)==250 and len(set(ids))==250
assert ids==[r['id'] for r in cases]
assert len(xmlcases)==220 and not list(junit.iter('failure')) and not list(junit.iter('error'))
assert front['numPassedTests']==30 and front['numFailedTests']==0
assert all(s.cell(i+6,11).value==r['result'] for i,r in enumerate(cases))
assert all(index.cell(i+6,6).value==r['nodeid'] for i,r in enumerate(cases))
assert s.cell(5,1).value=='序号' and s.cell(5,11).value=='执行结果'
assert cache['测试用例表']['A4'].value.startswith('共250项；通过250项；失败0项')
assert len(re.findall(r'^### TC-(?:BE|FE)-\d{3} ',text,re.M))==250
missing=[]
for p in [report,readme]:
    for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
        if not link.startswith(('http://','https://','#')) and not (p.parent/link).exists():missing.append(link)
assert not missing,missing
copies=[ROOT/'docs/测试用例表.xlsx',ROOT/'outputs/01a2173f-984a-7531-ac16-01a934b53667/测试用例表.xlsx']
assert copies[0].read_bytes()==copies[1].read_bytes()
result={'backend_junit_cases':len(xmlcases),'frontend_passed':front['numPassedTests'],'report_cases':250,'excel_rows':len(ids),'worksheets':book.sheetnames,'summary_cached':cache['测试用例表']['A4'].value,'filter_tables':list(s.tables)+list(index.tables),'freeze':{'main':s.freeze_panes,'index':index.freeze_panes},'date':str(cache['测试用例表']['I3'].value),'source_files_hash_checked':len(manifest),'application_and_test_files_changed':[],'existing_documents_edited_during_run':[x['path'] for x in changed],'missing_local_links':missing,'xlsx_sha256':hashlib.sha256(copies[0].read_bytes()).hexdigest(),'xlsx_bytes':copies[0].stat().st_size,'visual_review':'Both worksheets rendered and inspected; increased row heights after checking wrapped text.'}
(EV/'deliverable-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
files=[]
for p in sorted(EV.rglob('*')):
    if p.is_file() and p.name!='evidence-manifest.json':
        data=p.read_bytes();files.append({'path':p.relative_to(EV).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(EV/'evidence-manifest.json').write_text(json.dumps(files,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
