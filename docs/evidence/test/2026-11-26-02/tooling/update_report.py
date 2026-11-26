import ast,collections,hashlib,json,re,shutil
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(r'D:\DATA\university\3_1\Software Engineering\11.26\study-room')
TASK=Path(__file__).parent
EV=ROOT/'docs/evidence/test/2026-11-26-defect-recheck'
OLD=ROOT/'docs/evidence/test/2026-11-26-full-suite'
REPORT=ROOT/'docs/单元与集成测试案例及执行报告.md'
baseline=json.loads((OLD/'test-cases.json').read_text(encoding='utf8'))
full=json.loads((EV/'backend-regression-case-results.json').read_text(encoding='utf8'))
target=json.loads((EV/'defects-only-case-results.json').read_text(encoding='utf8'))
fullcmd=json.loads((EV/'backend-regression-command.json').read_text(encoding='utf8'))
targetcmd=json.loads((EV/'defects-only-command.json').read_text(encoding='utf8'))
assert len(full['cases'])==226
def outcome(r):
    if any(p['outcome']=='failed' for p in r['phases']):return '失败'
    if any(p['outcome']=='skipped' for p in r['phases']):return '跳过'
    return '通过' if any(p['phase']=='call' and p['outcome']=='passed' for p in r['phases']) else '未执行'
hist=collections.Counter(outcome(r) for r in full['cases'])
assert hist=={'通过':219,'失败':7},hist
executed=[r for r in target['cases'] if r['phases']]
assert len(executed)==6 and all(outcome(r)=='失败' for r in executed)
by_node={r['nodeid']:r for r in full['cases']}
notice='tests/units/test_defect_no_show_notification.py::test_srs_ac03_no_show_expiry_must_notify_user'
boundary='tests/units/test_defect_checkin_boundary.py::test_srs_ac02_sweep_must_keep_exact_checkin_deadline'
tier='tests/units/test_defect_no_show_penalty.py::test_srs_br095_no_show_must_apply_penalty_tier'
cancel='tests/units/test_defect_cancel_notification_failure.py::test_srs_uc009_notification_failure_must_not_rollback_cancel'
trace='tests/test_case_traceability.py::test_plan_document_lists_every_registered_case'
items=[
 ('TC-BE-221','DEFECT-001',notice,'请求触发超窗失效必须通知本人','SRS AC-03、BR-021、UC-010；FR-030/031；ADR-04/05',
  '合成用户7、预约21、座位11；2026-11-26 09:00～11:00，moment为10:00+08:00，截止09:15；座位reserved，无其他有效预约。',
  'Mock数据库Session；保留真实_expire_due→_expire_one→_record_violation及座位同步，只隔离配置与审计；不使用service_env、不替换通知函数。',
  '调用_expire_due(session,moment)，检查失效数、预约和座位状态、session.add的违规与通知对象。',
  '失效1条，EXPIRED/no_show，座位available，NO_SHOW违规1条归用户7；至少创建一条发给用户7的Notification。',
  '失效、释放与违规断言均已执行通过；失败发生于通知断言，实际新增Notification为0。',
  '周俊博负责失效入口，方梓安负责通知联动，张东岩复核'),
 ('TC-BE-222','DEFECT-002',boundary,'后台扫描应保留签到窗口截止整秒','SRS AC-02、BR-020；ADR-04；GAP-A05',
  'fixture moment=2026-11-26 10:00+08:00；booking.start=11:00、end=12:00；执行扫描时deadline=11:15:00。09:00/09:15为同构说明场景，不是本例实际绝对时刻。',
  'Mock会话、空候选集与事务上下文；保留真实sweep_reservations查询构建，捕获SQLAlchemy比较符和绑定参数；不连接数据库。',
  '调用sweep_reservations(session,deadline)，取真实未到候选查询，提取start_time条件，并将booking.start与绑定截止时间代入比较运算。',
  '截止整秒仍可签到，因此selected_as_no_show应为False，不应纳入未到失效候选。',
  '真实表达式使用<=，代入后selected_as_no_show=True；断言True is False失败。',
  '周俊博、方梓安共同负责；张东岩复核边界'),
]
for i,(count,days) in enumerate([(3,1),(5,2),(7,3)],223):
    items.append((f'TC-BE-{i}','DEFECT-003',f'{tier}[{count}-{days}]',f'未到累计第{count}次应禁约{days}天','SRS BR-095/095a、AC-09；HD-17/19；ADR-07；GAP-A06',
      f'合成用户7；moment=2026-11-26 10:00+08:00；预约开始改为09:00、结束沿夹具12:00；前一条违规由Mock提供，period_start为前一天10:00、period_seq={count-1}。不是在真实库创建{count-1}条历史记录。',
      '保留真实_expire_due→_expire_one→_record_violation，Mock会话及前次违规、配置与审计；不替换处罚逻辑，不使用service_env。',
      '执行请求失效路径，检查新增ViolationRecord序号，再检查新增Restriction数量、归属、ban_days、ACTIVE状态及结束时刻。',
      f'新增NO_SHOW序号{count}，新增Restriction=1条，用户7，ban_days={days}，ACTIVE，end_at=moment+{days}天。',
      f'新增违规类型及period_seq={count}断言通过；新增Restriction=0，数量断言0==1失败；后续天数/状态/截止字段断言因提前失败未执行，不能写成已检查通过。',
      '周俊博负责请求失效，方梓安负责阶梯处罚，张东岩复核'))
items.append(('TC-BE-226','DEFECT-004',cancel,'通知异常不得回滚预约取消','SRS UC-009异常流程E1、EX-06；FR-022；GAP-A07',
 '合成用户7，moment=10:00+08:00，RESERVED预约11:00～12:00，距离开始一小时，满足正常取消条件。',
 'Mock业务会话和通知故障，复用service_env后恢复真实write_transaction与真实transaction；仅替换Session创建，不将内存状态当作数据库提交。',
 '通知Mock抛RuntimeError("模拟站内通知创建失败")，调用cancel；捕获异常时先核验rollback一次且未commit，再用pytest.fail保留普通失败。',
 '取消应正常返回CANCELLED并commit，rollback不调用；通知失败应独立留存并安排重试。该测试主要验证主事务是否提交，不完整验证重试队列。',
 '通知异常向外传播；真实事务控制调用rollback一次、commit未调用；随后pytest.fail明确记录主业务取消被回滚。',
 '周俊博负责取消，方梓安负责通知补偿，张东岩复核事务'))

records=[]
for ident,defect,node,title,basis,pre,layer,action,expected,actual,owner in items:
    result=by_node[node]
    file='backend/'+node.split('::')[0]
    data=(TASK/'checkout'/file).read_text(encoding='utf-8-sig')
    name=node.split('::')[1].split('[')[0]
    n=next(n for n in ast.walk(ast.parse(data)) if isinstance(n,ast.FunctionDef) and n.name==name)
    fail=next(p['longrepr'] for p in result['phases'] if p['outcome']=='failed')
    assert 'test_srs' in node and 'xfail' not in '\n'.join(ast.unparse(d) for d in n.decorator_list)
    records.append({'id':ident,'defect_id':defect,'nodeid':node,'title':title,'basis':basis,'preconditions':pre,'layer':layer,'actions':action,'expected':expected,'actual':actual,'result':'失败','owner':owner,'source':file,'line':n.lineno,'parameters':result['parameters'],'failure':fail,'duration_seconds':sum(p['duration_seconds'] for p in result['phases'])})
(EV/'defect-cases.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
failures=[r for r in full['cases'] if outcome(r)=='失败']
old_ids={r['nodeid']:r['id'] for r in baseline if r['side']=='后端'}
new_ids={r['nodeid']:r['id'] for r in records}
current=[]
for r in full['cases']:
    current.append({'id':new_ids.get(r['nodeid']) or old_ids[r['nodeid']],'nodeid':r['nodeid'],'result':outcome(r),'parameters':r['parameters'],'source':'backend/'+r['file'].replace('\\','/'),'line':r['line'],'failure':next((p['longrepr'] for p in r['phases'] if p['outcome']=='failed'),None)})
(EV/'current-backend-results.json').write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf8')
summary={'recorded_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'targeted':{'executed':6,'failed':6,'deselected':68,'exit_code':targetcmd['exit_code']},'backend_regression':{'executed':226,'passed':219,'failed':7,'skipped':0,'xfail':0,'exit_code':fullcmd['exit_code']},'business_defects':4,'business_defect_samples':6,'additional_asset_failures':[{'id':'ASSET-001','case_id':old_ids[trace],'nodeid':trace,'reason':'Current stage plan no longer lists TC-LOCAL-001 through TC-LOCAL-010; registry consistency assertion fails.'}],'frontend':{'rerun':False,'historical_passed':30,'evidence':'../2026-11-26-full-suite/frontend-vitest.json'},'historical_run':{'backend_passed':220,'frontend_passed':30,'not_rewritten':True},'commands':{'targeted':targetcmd,'backend':fullcmd}}
(EV/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
for name in ['docs/分阶段实现与测试计划.md','backend/tests/case_registry.py','backend/tests/test_case_traceability.py']:
    dest=EV/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(TASK/'checkout'/name,dest)
shutil.copy2(REPORT,EV/'report-before-update.md')

def esc(s):return str(s).replace('|','\\|').replace('\n','<br>')
section='''## 7. 需求导向缺陷补测与当前结论（2026-11-26）

本节根据用户提供的DEFECT-001～004说明，对工作区已经新增的4个测试文件重新执行；本轮没有创建或修改这些测试，也没有修复业务代码、降低预期、增加xfail或跳过失败。专项与全量均在执行前快照的隔离副本中运行，使用同一现有测试venv。新增样例保留普通失败，便于修复后直接转绿。

### 7.1 运行范围和统计口径

| 运行批次 | 本轮真实结果 | 说明 |
|---|---|---|
| 缺陷专项：tests/units -k test_srs | **6 failed，68 deselected；退出码1** | 4项业务缺陷、6个参数化样例；68项未被选入，不是skipped |
| 当前后端全量 | **219 passed，7 failed；共226项，退出码1** | 六个业务缺陷样例，另含原TC-BE-063的文档追溯失败；没有xfail或skip |
| 前端 | **本次未重跑** | 仍引用原批次30项通过，不写成与本轮后端同次执行 |
| 原250项记录 | 原后端220、前端30通过，保留历史记录 | 新增测试与文档输入已不同，不能继续宣称当前全量全通过 |

专项和全量中的六个失败是同一组六个样例的两次执行，不累计为12个缺陷或12项覆盖。若将本次后端226与历史前端30合看，共256个已登记执行项，结果跨批次，**不能表述为一次256项全量运行**。原Excel仍为250项历史快照，本次未修改Excel；新增与当前状态以本节及本次证据为准。

来源：[专项原始日志](evidence/test/2026-11-26-defect-recheck/defects-only.log)、[专项JUnit](evidence/test/2026-11-26-defect-recheck/defects-only-junit.xml)、[全量日志](evidence/test/2026-11-26-defect-recheck/backend-regression.log)、[全量JUnit](evidence/test/2026-11-26-defect-recheck/backend-regression-junit.xml)。两次均有1条Starlette/httpx依赖弃用警告，与7项失败分别记录。

### 7.2 四项业务缺陷的原因、影响与测试边界

#### DEFECT-001：请求触发的超窗失效漏发站内通知

需求依据SRS AC-03：超窗未签到后预约失效、座位释放、形成违规候选且用户收到通知。测试为`test_defect_no_show_notification.py::test_srs_ac03_no_show_expiry_must_notify_user`，对应TC-BE-221。

实测输入为用户7、2026-11-26 09:00～11:00未签到预约，服务端时刻10:00，超过09:15。失效数、EXPIRED、释放及NO_SHOW违规检查通过；最后通知断言失败，新增通知对象数为0。

`_expire_due`调用`_expire_one`，后者调用`_record_violation`并同步座位；这两处没有创建通知。列表、详情等请求补扫和超窗签到复用该链。完整`sweep_reservations`未到分支有通知，但只选RESERVED；请求链先改EXPIRED后不再进入该未到分支，不能依靠它为同一预约补发。

本例保留真实失效、违规及同步函数，Mock数据库与审计、配置，不使用屏蔽违规逻辑的service_env，不替换通知函数。证明的是该业务路径没有创建通知，不是浏览器送达失败，也未验证真实数据库端到端。

#### DEFECT-002：后台扫描在签到窗口截止时刻提前失效

依据AC-02、BR-020，预约开始后恰好15分钟仍可签到。测试`test_defect_checkin_boundary.py::test_srs_ac02_sweep_must_keep_exact_checkin_deadline`对应TC-BE-222。

用户说明用09:00/09:15举例；实际测试夹具start=11:00、end=12:00、扫描deadline=11:15:00，语义相同。本例捕获`sweep_reservations`真实生成的SQLAlchemy候选条件，比较符为`<=`；使用实际绑定值计算得到selected_as_no_show=True，期望False。

请求路径`_overdue`严格大于窗口后缘才失效，后台却包含等号，存在入口不一致。若后台在截止整秒先执行，仍合法的预约可能被失效并记未到。本测试不连接数据库，不预设Mock返回超时预约；其失败证明查询条件错误，实际并发调度和数据库状态竞态仍需集成测试。

#### DEFECT-003：请求触发的未到违规不执行累计禁约阶梯

依据BR-095/095a、AC-09，第3/5/7次警告对应1/2/3天禁约。测试`test_defect_no_show_penalty.py::test_srs_br095_no_show_must_apply_penalty_tier`的[3-1]、[5-2]、[7-3]对应TC-BE-223～225。

Mock分别提供同周期前一条序号2/4/6的违规，真实执行`_expire_due→_expire_one→_record_violation`。本例开始时刻改为09:00、moment=10:00，结束沿用夹具12:00。三组均新增NO_SHOW，序号正确变为3/5/7；Restriction新增数均为0，数量断言失败。后续禁约天数、状态和截止字段断言未执行，不能称为通过。

原因是该链的`_record_violation`仅保存违规与审计，没有调用纪律服务`violations.record_violation`中的阶梯逻辑；完整扫描不会再把已EXPIRED预约纳入未到分支。此结论限定请求触发路径，不概括为所有违规入口均不处罚。

本例是Mock单元测试，不是在数据库创建2/4/6条历史警告；没有替换处罚逻辑。后续需真实数据库、多入口及重复处理验证，但当前普通断言失败应保留。

#### DEFECT-004：取消时通知失败导致主业务回滚

依据UC-009异常E1、EX-06，通知失败不阻塞主业务，取消应生效且失败通知进入重试。测试`test_defect_cancel_notification_failure.py::test_srs_uc009_notification_failure_must_not_rollback_cancel`对应TC-BE-226。

有效预约11:00～12:00，moment=10:00，正常提前一小时取消。通知Mock抛出异常，测试保留真实write_transaction与transaction，仅将Session对象替换为Mock；真实事务控制调用rollback一次，没有commit，异常向外传播。核验这些调用后，测试通过pytest.fail留下普通失败。

当前cancel在主事务内同步创建通知，没有失败隔离及持久重试安排。ORM内存已被赋CANCELLED不代表数据库提交，本例没有把内存赋值当作成功证据。它验证取消提交语义失败，未完整验证待补通知队列设计；本轮不修复。

### 7.3 额外发现：ASSET-001 文档与测试登记表失配

后端全量还失败于`tests/test_case_traceability.py::test_plan_document_lists_every_registered_case`，沿用原编号TC-BE-063。当前阶段计划正文不再列出TC-LOCAL-001～010的逐项编号，但`case_registry.py`仍登记这些编号，断言实际missing列表为全部10项，预期空列表。

这是**测试资产一致性问题**，不是四项业务缺陷中的第五项，也不是新增第七个业务缺陷样例。原批次TC-BE-063曾通过；本次输入文档改变后失败，两个结果应按快照分开保留。未修改计划、测试或登记表来凑绿。后续应确定是否恢复计划中的真实映射或正式调整追溯约定，并在确认后执行；本轮只记录。

### 7.4 六个失败样例（模板E）

'''
for r in records:
    section+=f"#### {r['id']}／{r['defect_id']} {r['title']}\n\n| 字段 | 内容 |\n|---|---|\n"
    values=[('编号/关联依据',r['id']+'；'+r['defect_id']+'；'+r['basis']),('层级',r['layer']),('场景和风险',r['title']+'；按需求正确行为断言，保留普通失败。'),('前置数据与角色',r['preconditions']),('操作/输入',r['actions']),('预期结果',r['expected']),('预期确认人','责任安排：'+r['owner']+'；预期引用SRS，未虚构独立人工签署日期。'),('实际输出',r['actual']),('执行结果','失败；2026-11-26专项与全量均复现；未修复，不使用xfail。'),('证据',f"[{r['source']}:{r['line']}](../{r['source']})；`{r['nodeid']}`；[defect-cases.json](evidence/test/2026-11-26-defect-recheck/defect-cases.json)；[全量JUnit](evidence/test/2026-11-26-defect-recheck/backend-regression-junit.xml)。")]
    for k,v in values:section+='| '+k+' | '+esc(v)+' |\n'
    section+='\n'
section+='''### 7.5 复现命令、版本与后续处理

依赖齐全时进入backend，可运行：

```powershell
python -m pytest tests/units/test_defect_no_show_notification.py -q
python -m pytest tests/units -k test_srs -q
python -m pytest -vv --tb=short
```

本次实际执行的是后两种范围，并增加外部只读pytest结果采集插件、禁用缓存和JUnit输出。精确命令、目录、时间、环境见[专项命令](evidence/test/2026-11-26-defect-recheck/defects-only-command.json)、[全量命令](evidence/test/2026-11-26-defect-recheck/backend-regression-command.json)和[环境日志](evidence/test/2026-11-26-defect-recheck/environment.log)。单文件命令在本轮没有再单独执行，不重复计数。

代码依HEAD加本地工作区快照，SHA-256及参与测试的阶段计划也已归档。原全绿报告和旧证据不覆盖删除。后续修复需按需求确认、最小修改、针对性失败转绿、受影响回归和交叉审查处理；在实际通过前，缺陷保持已复现／未修复，阶段验收不得直接写成满足相应条款。

本次仅更新本报告并新增[evidence缺陷复测目录](evidence/test/2026-11-26-defect-recheck/README.md)；没有更改业务实现、测试、需求、架构、阶段计划、Excel及历史证据。当前源码结论基于归档快照，不以未连接数据库的单元结果冒充端到端或线上故障。
'''

text=REPORT.read_text(encoding='utf-8-sig')
text=text.replace('| 文档版本 | TEST-REPORT-1.0 |','| 文档版本 | TEST-REPORT-1.1（补充需求导向缺陷复测） |',1)
text=text.replace('| 归档范围 | 后端现有全部pytest、前端全部Vitest；不更改业务代码、测试断言和需求 |','| 归档范围 | 原250项运行快照＋新增6项缺陷样例＋本次后端226项回归；前端本次未重跑，不更改业务代码或断言 |',1)
anchor='## 1. 依据与真实性规则'
notice_text='> **当前结论（2026-11-26补测）**：新增4项业务缺陷、6个普通失败样例已复现；当前后端全量为**219通过、7失败**，另1项为计划文档追溯失配。前端本次未重跑，原30项结果保留历史。原“250项全部通过”只适用于早先输入快照，详细差异及证据见第7章。\n\n'
text=text.replace(anchor,notice_text+anchor,1)
text=text.replace('## 3. 实际执行结果','## 3. 执行结果（分批次保留）',1)
text=text.replace('| 后端全量 | 220 passed；','| 原后端全量快照（新增缺陷测试前） | 220 passed；',1)
text=text.replace('| 前端全量 | 8个文件、30项通过；','| 原前端全量快照（本次未重跑） | 8个文件、30项通过；',1)
table_end='### 3.1 测试层级分布'
latest=f'''### 3.0 本次需求导向补测结果

| 范围 | 实际结果 | 证据 |
|---|---|---|
| 六个缺陷样例专项 | 6 failed，68 deselected；退出码1；命令{targetcmd['elapsed_seconds']:.3f}秒 | [专项日志](evidence/test/2026-11-26-defect-recheck/defects-only.log) |
| 当前后端全量（含新增样例） | 219 passed，7 failed，共226项；退出码1；命令{fullcmd['elapsed_seconds']:.3f}秒 | [回归日志](evidence/test/2026-11-26-defect-recheck/backend-regression.log) |
| 失败构成 | 四项业务缺陷对应六样例；另有原TC-BE-063文档追溯失败 | [本次汇总](evidence/test/2026-11-26-defect-recheck/summary.json) |

以下§3.1层级分布、§3.2并发结果及原250项明细属于早先快照；第7章补充六个需求样例及当前状态，不将跨批次结果伪装为一次运行。原Excel未更新，仍为历史250项。

'''
text=text.replace(table_end,latest+'### 3.1 原250项测试层级分布',1)
text=text.replace('1. 当前断言全通过不代表架构差异全部关闭。','1. 原批次断言全通过不代表架构差异全部关闭；本次已有6项业务需求断言及1项资产追溯检查失败。',1)
text=text.replace('本报告以重新执行的220项为准，不覆盖旧文件、不合并为同一次运行。','原220项和本次226项按各自输入快照保留，不覆盖旧文件、不合并为同一次运行。',1)
text=text.replace('## 4. 用例索引','## 4. 用例索引（原250项及新增样例）',1)
text=re.sub(r'(\| TC-BE-063 \|[^\n]+?\| 测试资产一致性 \| )通过',r'\1原通过；本次失败（ASSET-001）',text,count=1)
index='### 新增失败样例索引\n\n| 编号 | 缺陷 | 测试标题 | 当前状态 |\n|---|---|---|---|\n'
for r in records:index+=f"| {r['id']} | {r['defect_id']} | {r['title']} | 失败，详见§7 |\n"
text=text.replace('## 5. 按模板E整理的全部测试案例',index+'\n## 5. 原250项测试案例的历史运行明细（模板E）',1)
text=text.replace('### TC-BE-063 测试计划文档必须列出登记表中的每个案例编号','### TC-BE-063 测试计划文档必须列出登记表中的每个案例编号\n\n> 下表为原批次通过记录；本次同一测试已失败，见§7.3 ASSET-001。',1)
text=text.rstrip()+'\n\n'+section+'\n'
REPORT.write_text(text,encoding='utf8')

readme='''# 2026-11-26 需求导向缺陷复测证据

## 实际结果

- 专项：6 failed，68 deselected，退出码1。四项业务缺陷，禁约阶梯有三个参数样例。
- 当前后端全量：226项，219 passed、7 failed，退出码1；无skip/xfail。额外失败为原TC-BE-063的计划文档与TC-LOCAL登记失配（ASSET-001）。
- 前端本次未重跑，原30项通过记录仍在[旧证据目录](../2026-11-26-full-suite/README.md)。不把不同输入快照或重复执行相加为一次全量结果。
- 本轮未修改业务代码、测试、断言、阶段计划或旧证据，没有修复缺陷，也没有为了全绿调整预期。

## 目录索引

| 文件 | 内容 |
|---|---|
| defects-only.log / defects-only-junit.xml | 六个需求导向普通失败的完整输出及JUnit |
| backend-regression.log / backend-regression-junit.xml | 226项后端回归结果及七项失败详情 |
| defects-only-case-results.json | 收集阶段74项，实际执行6项；其余68项无运行阶段，为deselected |
| backend-regression-case-results.json | 226项的参数、阶段结果、耗时和原始失败堆栈 |
| defect-cases.json | TC-BE-221～226、DEFECT-001～004及模板E字段 |
| current-backend-results.json | 保留原TC-BE编号的当前226项状态；TC-BE-063由原通过变为本次失败 |
| summary.json | 四项业务缺陷、六个失败样例与额外资产失败的统计区分 |
| *-command.json / environment.log / run-metadata.json | 精确命令、起止时间、退出码、Python和依赖版本 |
| source-manifest.json / working-tree-before.patch / git-status-before.txt | HEAD加未提交代码与文档快照标识 |
| sources/ | 四个缺陷测试、原说明、夹具、关键业务源码、SRS及实际参与测试的阶段计划/登记表快照 |
| report-before-update.md | 更新前报告备份，保留原有手工修改；不是本次最新结论 |
| tooling/ | 外部运行、结果采集与报告更新脚本；采集插件不替换业务逻辑或断言 |
| evidence-manifest.json | 证据SHA-256清单，清单自身不递归计入 |

## 缺陷与边界

1. DEFECT-001：请求失效链未创建通知，用户7通知数0；保持真实失效/违规/座位函数，Mock会话/配置/审计，不使用service_env屏蔽关键逻辑。
2. DEFECT-002：真实候选SQL条件使用<=，签到截止整秒被选中；实际夹具11:00/11:15，与说明09:00/09:15同构。检查查询谓词，不是数据库并发复现。
3. DEFECT-003：同周期序号2/4/6经请求未到变3/5/7，但三个样例Restriction新增0。历史违规由Mock提供，非真实库多行累计；后续天数/状态断言未执行。
4. DEFECT-004：注入通知异常，真实事务控制rollback一次、commit未调用；不能以ORM内存赋值证明取消提交。当前样例未完整验证重试队列实现。
5. ASSET-001：当前计划不含TC-LOCAL-001～010的逐项登记，原一致性测试失败；不是第五项业务缺陷，不自动改计划或删断言消除。

这些是单元测试下真实执行的失败结果，未声明浏览器或真实数据库端到端验证。不得概括为所有超时路径均漏通知或不处罚：完整sweep路径有相应逻辑，但不会再在未到分支处理已EXPIRED预约。

复现：进入backend，在依赖齐全环境执行`python -m pytest tests/units -k test_srs -q`；全量执行`python -m pytest -vv --tb=short`。本次更详细日志参数及JUnit输出以command.json为准。

最新综合说明：[单元与集成测试案例及执行报告](../../../单元与集成测试案例及执行报告.md)第7章。Excel仍为原250项快照，本轮未改动。
'''
(EV/'README.md').write_text(readme,encoding='utf8')
shutil.copy2(TASK/'update_report.py',EV/'tooling/update_report.py')
print(json.dumps({'targeted':summary['targeted'],'current_backend':summary['backend_regression'],'new_case_ids':[r['id'] for r in records],'extra_failure_case':old_ids[trace],'report_characters':len(text)},ensure_ascii=False))
