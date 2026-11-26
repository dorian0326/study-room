import ast,collections,hashlib,json,platform,re,shutil,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

TASK=Path(__file__).parent
ROOT=Path(r'D:\DATA\university\3_1\Software Engineering\11.26\study-room')
EV=ROOT/'docs/evidence/test/2026-11-26-full-suite'
OUT=ROOT/'outputs/01a2173f-984a-7531-ac16-01a934b53667'
OUT.mkdir(parents=True,exist_ok=True)
backend=json.loads((EV/'backend-case-results.json').read_text(encoding='utf-8'))
front=json.loads((EV/'frontend-vitest.json').read_text(encoding='utf-8'))
sources=json.loads((EV/'backend-source-inventory.json').read_text(encoding='utf-8'))
fsources=json.loads((EV/'frontend-source-inventory.json').read_text(encoding='utf-8'))
concurrency=json.loads((EV/'concurrency-case-results.json').read_text(encoding='utf-8'))
metadata=json.loads((EV/'run-metadata.json').read_text(encoding='utf-8'))
titles={}
title_lines='''
test_non_admin_forbidden|非管理员无法管理资源配置
test_room_crud_and_close|房间创建编辑关闭与删除
test_room_with_seats_cannot_be_deleted|含座位房间不得直接删除
test_opening_schedules|开放时段增删改及边界校验
test_calendar_days|特殊日期校历维护与校验
test_business_settings|业务参数保存与非法值拒绝
test_register_then_login_and_me|注册登录与本人信息查询
test_password_is_stored_hashed|数据库保存密码哈希
test_register_rejects_duplicate_and_bad_input|拒绝重复学号及非法注册输入
test_login_failures_have_clear_messages|登录失败与错误提示
test_login_lockout_after_failures|失败次数达到阈值时锁定登录
test_disabled_account_cannot_login|禁用账号不得登录
test_logout_revokes_token|注销撤销当前会话
test_unauthenticated_and_expired|未认证及过期会话被拒绝
test_change_password|改密校验旧密码并撤销会话
test_reset_password_with_code|通过重置码修改密码
test_reset_code_expires_and_reissue_invalidates_old|重置码过期及重签失效
test_backup_api_ops_only|备份API仅限运维访问
test_backup_rotation_and_restore|备份轮换和数据库恢复
test_status|运行状态接口字段与访问
test_temp_leave_timeout_type|暂离超时使用专用违规类型
test_archive_expired_violations|违规周期到期归档
test_zone_auto_assign|按房间区域自动分配座位
test_facility_filters|座位设施条件筛选
test_close_room_cancels_reservations|关闭房间取消未来预约
test_schedule_change_cancels_conflicting|开放时段调整取消冲突预约
test_health_ok|健康接口与数据库连通
test_server_time_is_utc_plus_8|服务端时间为UTC加8时区
test_sqlite_pragmas_enabled|SQLite外键WAL及忙等待配置
test_login_events_are_logged|登录成功失败和注销留痕
test_login_logs_only_for_ops|登录日志仅运维可读
test_audit_logs_query_filters|审计日志过滤与分页
test_purge_expired_logs|清理到期审计及登录日志
test_seed_is_idempotent_and_reset_rebuilds|演示数据重复导入与重置
test_counts_and_states|演示数据数量及状态组合
test_no_overlaps_and_within_opening_hours|演示预约不重叠且处于开放时间
test_sweeper_finds_nothing_due|演示数据不会被扫尾误处理
test_demo_accounts_can_log_in|演示角色账号可登录
test_refuses_outside_dev|生产环境拒绝导入演示数据
test_dev_script_prepare_db|开发脚本迁移与演示数据准备
test_dev_script_flags|开发脚本命令行参数
test_all_tables_created|迁移创建全部模型表
test_migration_rerunnable_and_reversible|数据库迁移可重复及可逆
test_roles_seeded|数据库初始角色齐全
test_student_no_unique|用户学号唯一约束
test_foreign_keys_enforced|数据库强制外键约束
test_seat_code_unique_within_room|房间内座位编号唯一
test_enum_check_constraint|数据库枚举检查约束
test_invalid_enum_rejected_by_orm|ORM拒绝非法枚举
test_reservation_time_order|数据库拒绝无效预约起止顺序
test_one_active_reservation_per_seat_slot|同座同起点有效预约唯一约束
test_entry_exit_dedup|门禁来源事件号唯一约束
test_datetime_stored_as_utc8|日期时间按北京时间往返存取
test_naive_datetime_rejected|拒绝无时区日期时间入库
test_transaction_rolls_back_all_changes_on_error|业务异常回滚全部事务变化
test_transaction_rolls_back_on_constraint_violation|数据库约束失败回滚事务
test_transaction_commits_on_success|成功事务正常提交
test_db_permission_matrix_matches_code|数据库权限矩阵与代码一致
test_me_lists_permissions|本人接口返回角色权限集合
test_only_admin_can_manage_users|仅管理员能够管理用户
test_admin_promotes_user_and_change_is_logged|管理员角色变更及审计
test_admin_cannot_demote_or_disable_self|管理员不得自降权或自禁用
test_disable_account_logs_out_and_blocks_login|禁用账号撤销会话并拒绝登录
test_admin_issues_reset_code|管理员为目标用户签发重置码
test_cli_create_admin|CLI创建管理员账号
test_room_search_detail_and_interval_states|房间搜索详情及区间座位状态
test_search_invalid_inputs|资源查询拒绝不完整或非法时间
test_calendar_priority_effective_dates_and_closed_room|校历优先级生效日期与关闭房间
test_create_rejects_invalid_times|创建预约拒绝非法时间
test_today_tomorrow_short_duration_and_full_opening_day|当天次日短时段与全天开放预约
test_overlap_person_overlap_adjacent_and_utc_conversion|座位及本人冲突相邻区间与时区转换
test_idempotency_key_required_and_scoped_to_payload_and_user|无键现状及幂等键用户载荷范围
test_change_seat_rechecks_conflicts_and_preserves_original_on_failure|换座重查冲突且失败保留原预约
test_cancel_exact_boundary_and_no_show_mutual_exclusion|取消15分钟边界及未到场违规互斥
test_restricted_user_can_cancel_but_cannot_create_or_change|禁约允许取消但拒绝创建换座
test_checkin_early_boundary|签到窗口前缘边界
test_checkin_late_boundary_no_penalty_inside_window|签到后缘边界与窗内不处罚
test_checkin_identity_seat_repeat_and_state_transitions|签到归属座位重复及状态转换
test_unattended_expiry_worker_and_dedup|无人请求时后台释放及去重
test_lazy_expiry_and_maintenance_preserved|查询补扫释放并保留维护状态
test_owner_privacy_and_ops_permissions|本人预约隔离及运维权限
test_cancel_audit_failure_rolls_back_violation_and_release|取消审计异常回滚违规及释放
test_100_competing_users_only_one_reservation|100线程竞争同座仅一条预约成功
test_concurrent_retries_return_same_id|16线程同键重试仅一次创建
test_write_lock_error_is_retryable_and_same_key_can_recover|写锁繁忙503及同键恢复重试
test_password_policy_rejects_short_or_single_class|密码长度字符类别及字节上限
test_student_no_pattern|学号格式有效及非法输入
test_password_hash_verifies_and_hides_plaintext|密码哈希验证不暴露明文
test_token_digest_is_stable_and_not_the_token|会话摘要稳定且不等于原令牌
test_permission_projection_matches_role_matrix|角色权限投影与组合
test_now_is_shanghai_aware|统一时钟带北京时间时区
test_gate_user_key_does_not_expose_student_no|门禁脱敏键稳定且隐藏学号
test_cancel_classifies_fifteen_minute_boundary|取消15分钟边界分类
test_repeated_cancel_does_not_repeat_violation_or_notification|重复取消不重复违规和通知
test_cancel_rejects_non_reserved_booking|非已预约状态拒绝取消
test_cancel_rejects_started_booking|预约开始后拒绝取消
test_change_seat_preserves_reservation_times|换座保留起止时间
test_only_reserved_booking_can_change|仅未签到预约允许换座
test_overdue_booking_cannot_change|已超窗预约拒绝换座
test_conflicting_target_preserves_original_seat|目标冲突时原座位不变
test_change_request_rejects_time_modification|换座请求拒绝修改时间字段
test_qr_checkin_within_window|扫码及编号在签到窗口内成功
test_qr_seat_must_match_booking|扫码座位必须匹配本人预约
test_checkin_before_window_fails|窗口开放前拒绝签到
test_repeated_qr_checkin_is_idempotent|重复扫码不重复签到
test_no_show_grace_boundary|未签到宽限截止整秒判定
test_booking_end_is_overdue_even_within_grace|预约结束优先于未签到宽限
test_late_checkin_expires_booking|超窗签到触发失效处理
test_expiry_records_no_show_and_releases_seat|失效记录未到场并释放座位
test_expiry_preserves_maintenance_status|失效释放保留座位维护状态
test_expiry_sweep_processes_candidates|到期扫描处理候选预约
test_same_key_and_payload_replays_without_writing|同键同载荷重放不再写入
test_key_cannot_be_reused_for_different_request|幂等键不得跨用户或载荷复用
test_write_transaction_requests_immediate_lock|业务事务请求立即写锁
test_write_errors_become_booking_errors|锁忙及唯一异常映射业务错误
test_unrelated_database_error_is_preserved|无关数据库异常原样抛出
test_create_saves_booking_and_arrival|创建写入预约及到达占位
test_create_rejects_past_or_too_distant_start|创建拒绝过去及超提前期开始时间
test_slot_rejects_closed_hours_or_conflicts|时段检查拒绝关闭或重叠冲突
test_slot_ignores_the_booking_being_modified|换座时冲突检查排除本预约
test_invalid_time_range_is_rejected|模型拒绝零负或跨日区间
test_valid_slot_passes|合法无冲突时段通过检查
test_room_list_contains_room_information|房间列表包含位置容量开放时间
test_empty_room_list|无房间返回空列表
test_search_unknown_room_fails|搜索不存在房间返回404
test_search_available_only|搜索仅可用座位过滤
test_search_passes_room_zone_and_facility_filters|搜索生成房间区域设施筛选条件
test_blocked_seat_keeps_status|维护关闭停用座位保持原状态
test_closed_room_or_outside_opening_hours|房间关闭或非开放时间显示关闭
test_current_booking_determines_status|有效预约映射座位实时状态
test_future_booking_does_not_occupy_seat_now|未来预约不占据当前空闲状态
test_detail_contains_facilities_and_qr_payload|座位详情设施与二维码载荷
'''
for line in title_lines.strip().splitlines():
    k,v=line.split('|',1); titles[k]=v
ftitles={
'writes and clears the session token':'保存及清除浏览器会话令牌',
'sends the bearer token and returns JSON':'请求携带Bearer并解析JSON',
'returns null for an empty response':'204无正文响应返回null',
'surfaces a string error from the backend':'展示后端字符串错误提示',
'joins field validation messages':'拼接字段校验错误信息',
'uses an object message and keeps the status code':'提取对象错误并保留状态码',
'explains a conflict that has no detail':'缺少详情时提示资源冲突',
'names the HTTP status when the body cannot be read':'响应不可解析时显示HTTP状态',
'stays logged out when there is no token':'无令牌时保持未登录且不请求本人',
'drops a token that the server no longer accepts':'失效会话清除令牌及用户信息',
'stores the user returned by login':'登录后保存会话用户及权限',
'clears the session even when logout fails':'注销请求失败也清理本地会话',
'resolves true only after the user confirms':'确认对话框仅主动确认返回true',
'cancels the dialog that is already open':'打开新对话框取消已有待确认操作',
'returns the typed text, or null when cancelled':'输入框确认返回文本取消返回null',
'shows the shared label for a known status':'状态组件显示已知中文标签',
'keeps an unknown status readable':'状态组件保留未知状态原文',
'shows only the title when there is no action':'空状态组件无操作时仅显示标题',
'links to the next step when an action is given':'空状态组件展示下一步链接',
'uses a saved choice instead of the system theme':'优先使用用户保存主题',
'follows the system when nothing valid is saved':'未保存有效主题时跟随系统',
'toggle stores the choice and stops following the system':'切换主题后保存选择并停止跟随',
'sends an anonymous visitor to login and keeps the target':'未登录访问受保护页跳转并保存目标',
'loads the session once before deciding':'导航前只加载一次未初始化会话',
'blocks a page the signed-in user cannot access':'缺少页面权限时阻止导航',
'allows a page when any required permission matches':'任一允许权限匹配即可导航',
'leaves public pages open':'公共页面不要求登录',
'translates known zones and keeps unknown values':'区域文案翻译及未知值回退',
'accepts either case and falls back to the raw value':'违规文案兼容大小写及未知值',
'joins the facilities a seat actually has':'设施文案仅组合实际具备项目',
}

def topic(name,file):
    text=(name+' '+file).lower()
    if any(w in text for w in ['gate','entry_exit']):return ('门禁同步与隐私','SRS HD-15/16/30/31/52、NFR-013/014；ADR-06','方梓安','P0')
    if any(w in text for w in ['backup','restore','status','logs','purge']):return ('日志备份与运维','SRS NFR-008/012；ADR-09','张东岩','P1')
    if any(w in text for w in ['permission','auth','password','token','student_no','register','login','logout','account','admin_','role','cli_create']):return ('认证与权限','SRS FR-001～007、NFR-005/011；权限矩阵','张东岩','P0')
    if any(w in text for w in ['appeal','violation','br093','checkout','archive','temp_leave','temporary_leave','current_scope','report','excel','maintenance']):return ('履约纪律与管理','SRS FR-032～043/050～052/060～073；ADR-04/05/07/08','方梓安','P0' if any(w in text for w in ['violation','appeal','timeout','maintenance']) else 'P1')
    if any(w in file for w in ['test_models','test_mock_data','test_health','test_admin_config']):return ('数据模型与配置','SRS FR-070～075、BR-050～053；ADR-02/08','张东岩','P0' if any(w in text for w in ['transaction','constraint','foreign','unique']) else 'P1')
    if any(w in text for w in ['case_traceability','theme','labels','confirm','emptystate','statusbadge','dev_script']):return ('交互与测试支撑','SRS NFR-009/010；测试计划及交互约定','周俊博' if 'confirm' in text else '张东岩','P2')
    return ('查询预约与签到','SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10','周俊博','P0' if any(w in text for w in ['concurr','competing','idempoten','rollback','cancel','checkin','expiry']) else 'P1')

def status(phases):
    if any(x['outcome']=='failed' for x in phases):return '失败'
    if any(x['outcome']=='skipped' for x in phases):return '跳过'
    return '通过' if any(x['when']=='call' and x['outcome']=='passed' for x in phases) else '阻塞'

def compact(s,n=350):
    s=re.sub(r'\s+',' ',s)
    return s if len(s)<=n else s[:n-1]+'…'

def md(s):return str(s).replace('|','\\|').replace('\n','<br>')

source_map={(r['file'].removeprefix('backend/'),r['function']):r for r in sources}
con_map={r['nodeid']:r for r in concurrency['cases']}
records=[]
for i,r in enumerate(backend['cases'],1):
    src=source_map[(r['file'].replace('\\','/'),r['function'])]
    title=titles.get(r['function']) or src['docstring'] or r['function']
    title=title.rstrip('。')
    params=r['parameters']; param_text='；'.join(k+'='+v for k,v in params.items())
    if params:title+='（'+param_text+'）'
    module,basis,owner,priority=topic(r['function'],src['file'])
    if src['file'].startswith('backend/tests/units/') or src['file'].endswith('/test_units.py'):
        layer='单元（Mock隔离）' if '/units/' in src['file'] else '单元（纯函数）'
        pre='合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。' if '/units/' in src['file'] else '纯函数及合成字符串；不建业务数据库。'
        stepname='调用被测函数并核对断言'
    elif 'test_case_traceability.py' in src['file']:
        layer='测试资产一致性';pre='现有case登记表、已收集测试及分阶段计划文档。';stepname='核对登记、标记与文档'
    elif 'test_models.py' in src['file']:
        layer='数据库集成';pre='每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。';stepname='操作临时数据库并验证约束'
    elif '100_competing' in r['function'] or 'concurrent_retries' in r['function']:
        layer='数据库并发集成';pre='临时文件SQLite、独立Session、多线程；不是Mock也不是线上压测。';stepname='并发调用服务并数据库对账'
    elif r['http']:
        layer='接口／数据库集成';pre='本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。';stepname='通过TestClient执行请求并检查数据库'
    elif 'test_mock_data.py' in src['file'] and 'dev_script' in r['function']:
        layer='单元（命令Mock）';pre='开发脚本runner被替换为记录列表；不启动服务或执行真实迁移命令。';stepname='调用脚本解析与准备函数'
    else:
        layer='服务／数据库集成';pre='依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。';stepname='调用服务并核对持久化事实'
    assertions=[a['expression'] for a in src['assertions']]+src['raises_and_mock_asserts']
    expected='；'.join(assertions) or '按测试函数中的异常期望及调用断言核验，见源代码。'
    actions=[a['call'] for a in src['http_actions']]
    if not actions:
        tree=ast.parse(src['source'])
        for child in ast.walk(tree):
            if isinstance(child,ast.Call):
                name=ast.unparse(child.func)
                if name.startswith(('service.','catalog.','dev.','auth_svc.','command.','backup.')) or name in ('password_problem','student_no_valid','hash_password','verify_password','token_digest','permissions_of','roles_for','now','tz','user_key_for_gate'):
                    actions.append(ast.unparse(child))
    recorded_actions=[h for h in r['http'] if '/api/auth/login' not in h['url'] and '/api/auth/register' not in h['url']]
    if recorded_actions:
        steps='完成所列夹具准备后，按脚本顺序执行：'+'；'.join(h['method']+' '+h['url']+('，JSON='+compact(json.dumps(h['request_json'],ensure_ascii=False),260) if h.get('request_json') is not None else '') for h in recorded_actions[:8])
        if len(recorded_actions)>8:steps+=f'；其余{len(recorded_actions)-8}步请求见本例原始证据。'
    else:
        steps='按源函数顺序执行：'+('；'.join(actions[:6]) if actions else '使用所列夹具执行 '+r['function']+'，进行异常、返回值或Mock调用核验。')
    if params:steps+='；本例参数：'+param_text
    result=status(r['phases']);duration=sum(x['duration_seconds'] for x in r['phases'])
    http=r['http'];hist=collections.Counter(x['status'] for x in http)
    actual=f'pytest {result}；setup/call/teardown累计{duration:.3f}s。'
    if http:
        actual+=' 实采HTTP '+str(len(http))+'次，状态分布'+json.dumps(hist,ensure_ascii=False)+'。'
        selected=[x for x in http if '/api/auth/login' not in x['url']][-2:]
        actual+=' '.join(x['method']+' '+x['url']+' → '+str(x['status'])+' '+compact(json.dumps(x['response'],ensure_ascii=False),240) for x in selected)
    else:actual+=' 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。'
    extra=''
    if r['nodeid'] in con_map:
        calls=con_map[r['nodeid']].get('service_create',[])
        successes=[x for x in calls if x['outcome']=='success'];errors=[x for x in calls if x['outcome']=='error']
        extra=f"补采实际服务调用{len(calls)}次：成功{len(successes)}、冲突{sum(x.get('status_code')==409 for x in errors)}，预约ID集合{sorted({x['reservation_id'] for x in successes})}，首次创建{sum(x.get('replay') is False for x in successes)}、重放{sum(x.get('replay') is True for x in successes)}。"
        actual+=' '+extra
    limit='现有断言通过不等于全部业务需求验收。'
    if 'idempotency_key_required' in r['function']:limit+=' 源函数名称含required，但正文测试接受无键创建，按实际断言归档，不声称强制幂等键。'
    if '/units/' in src['file'] and 'concurrency' in src['file']:limit+=' 本文件仅Mock事务/错误分支，不证明真实并发。'
    if 'test_reservation_idempotency_ownership_and_user_limit'==r['function']:limit+=' 所谓user_limit实际覆盖重叠时段单座，不能证明独立日次数额度。'
    if 'report' in r['function']:limit+=' 只证明当前统计实现及导出对应，不证明历史真实现场利用率。'
    records.append({'id':f'TC-BE-{i:03d}','side':'后端','title':title,'module':module,'basis':basis,'owner':owner,'priority':priority,'layer':layer,'preconditions':pre+' 夹具：'+', '.join(src['fixtures']), 'step_name':stepname,'steps':steps,'parameters':params,'expected':expected,'actual':actual,'result':result,'duration_seconds':round(duration,6),'source':src['file'],'line':src['line'],'function':r['function'],'nodeid':r['nodeid'],'legacy_case':r['case_marker'],'evidence':'backend-case-results.json','assertions':assertions,'limit':limit,'http_count':len(http),'http_status_counts':dict(hist),'concurrency_detail':extra})

front_results={a['fullName']:a for file in front['testResults'] for a in file['assertionResults']}
for i,src in enumerate(sorted(fsources,key=lambda x:(x['file'],x['line'])),1):
    a=front_results[src['fullName']]
    title=ftitles[src['title']]
    module,basis,owner,priority=topic(src['fullName'],src['file'])
    layer='前端组件单元' if '/components/' in src['file'] else '前端逻辑单元'
    pre='Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。'
    if '/components/' in src['file']:pre+=' Vue Test Utils挂载组件，RouterLink使用stub。'
    actual=f"Vitest {'通过' if a['status']=='passed' else a['status']}；本例耗时{a.get('duration',0):.3f}ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。"
    front_steps='按源测试顺序执行：'+'；'.join(src.get('steps',[]))+'；核对所列expect断言。'
    records.append({'id':f'TC-FE-{i:03d}','side':'前端','title':title,'module':module,'basis':basis,'owner':owner,'priority':priority,'layer':layer,'preconditions':pre,'step_name':'挂载组件并检查DOM' if '/components/' in src['file'] else '执行前端函数与expect断言','steps':front_steps,'parameters':{},'expected':'；'.join(src['assertions']),'actual':actual,'result':'通过' if a['status']=='passed' else '失败','duration_seconds':a.get('duration',0)/1000,'source':src['file'],'line':src['line'],'function':src['title'],'nodeid':src['fullName'],'legacy_case':None,'evidence':'frontend-vitest.json','assertions':src['assertions'],'limit':'happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。','http_count':0,'http_status_counts':{},'concurrency_detail':''})

for r in records:
    r['expected_brief']=compact(r['expected'],340)
    r['steps_brief']=compact(r['steps'],360)
    r['preconditions_brief']=compact(r['preconditions'],250)
    r['actual_brief']=compact(r['actual'],380)

(EV/'test-cases.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
summary={'backend':dict(collections.Counter(r['result'] for r in records if r['side']=='后端')),'frontend':dict(collections.Counter(r['result'] for r in records if r['side']=='前端')),'total':len(records),'backend_functions':len(sources),'frontend_functions':len(fsources),'backend_files':len({x['file'] for x in sources}),'frontend_files':len({x['file'] for x in fsources}),'layers':dict(collections.Counter(r['layer'] for r in records)),'http_requests_captured':sum(r['http_count'] for r in records),'commands':{name:json.loads((EV/(name+'-command.json')).read_text(encoding='utf-8')) for name in ['backend-tests','frontend-tests','concurrency-evidence','frontend-checks']}}
(EV/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')

parts=['''# 智能自习室管理预约系统单元与集成测试案例及执行报告

| 项目 | 内容 |
|---|---|
| 文档版本 | TEST-REPORT-1.0 |
| 项目名称 | 智能自习室管理预约系统 |
| 队名 | 全网呼叫奶家人 |
| 测试组织负责人 | 张东岩（测试整合责任安排） |
| 小组人员 | 周俊博（队长）、张东岩、方梓安 |
| 执行日期 | 2026-11-26，Asia/Shanghai |
| 实际执行方式 | Codex工具在本机隔离副本自动运行，非人工逐条操作，不代签成员验收 |
| 代码参照 | HEAD 671ca454a8fd4a69e0c7f619a5f540d277b930c0＋本地未提交内容，详见SHA-256清单及差异补丁 |
| 归档范围 | 后端现有全部pytest、前端全部Vitest；不更改业务代码、测试断言和需求 |

## 1. 依据与真实性规则

测试案例按[教师指引](架构设计后确认与分阶段实现操作指引_学生版.md)模板E整理，覆盖编号、依据、层级、场景、前置、操作、预期、确认责任、执行结果及证据。需求依据为[SRS](软件需求规格说明书.md)，架构依据为[基线](软件架构设计方案_基线版.md)与[确认记录](架构确认与决策记录.md)，接口依据为[接口与关键设计说明书](接口与关键设计说明书.md)。

测试输入来自仓库既有合成夹具与参数，不包含真实学生、真实门禁或运行站点写入。这里的“实际输出”来自本轮真实执行结果；合成业务数据不等于编造执行结果。Mock结果只用于相应单元测试，真实文件SQLite测试与Mock测试分别标层级。

每个参数化执行项独立编号，后端TC-BE、前端TC-FE是本次文档整理编号；原TC-LOCAL标记保留对应，不替换原GitHub任务与TC-IF设计索引。Excel一行对应一个执行项，正文提供全部断言及来源。编写人列表示本次用例文档整理责任，按团队分工安排，不认定原测试代码的Git作者。预期来自既有测试断言，尚无本次独立业务预期签署；各例列责任人而不伪造确认日期。

## 2. 执行环境与隔离

- Windows；Python 3.13.5，隔离venv按backend/pyproject.toml依赖下限安装，完整版本见backend-environment.log。
- Node.js v22.18.0，npm 10.9.3；前端npm ci按仓库package-lock.json安装，版本见frontend-environment.log。
- 应用配置STUDYROOM_ENV=test；数据库由conftest在临时目录创建，每例api_db运行真实Alembic迁移；bcrypt测试成本4，预约/备份/日志后台定时器关闭。
- 原工作区没有安装齐依赖、前端无node_modules；本轮将源文件复制到外部临时目录，安装及运行发生在副本；不向原工程写依赖、缓存或数据。
- 原目录有一个Office临时锁文件，复制时排除，详见copy-exclusions.json；它不是测试代码，不影响测试集合。
- 证据采集插件在进程内包装TestClient请求，按例记录真实响应并脱敏凭证。数组仅保留前8项，长字符串保留前3000字符；完整断言成功以JUnit和pytest结果为准。没有声称保存完整网络抓包或全部数据库快照。
- 本轮Python/Node高于CI配置的Python 3.11/Node 20；本地通过不直接证明CI环境也通过。
- 执行结束校验发现三份既有架构／接口文档在共享工作区发生其他编辑变化，已保留，详见source-comparison-after.json；前后端源码及测试内容SHA-256未变化，测试对应执行前隔离快照。

## 3. 实际执行结果

''']
parts.append('| 范围 | 执行结果 | 原始证据 |\n|---|---|---|\n')
for name,label,desc,log in [('backend-tests','后端全量','220 passed；1条Starlette/httpx弃用警告','backend-tests.log'),('frontend-tests','前端全量','8个文件、30项通过','frontend-tests.log'),('concurrency-evidence','并发输出补采','2项通过；为服务返回值补采，不计入250个独立用例总数','concurrency-evidence.log'),('frontend-checks','前端ESLint','退出码0；静态检查不计为测试用例','frontend-checks.log')]:
    c=summary['commands'][name]
    parts.append(f"| {label} | {desc}；命令耗时{c['elapsed_seconds']:.3f}s，退出码{c['exit_code']} | [{log}](evidence/test/2026-11-26-full-suite/{log}) |\n")
parts.append(f"\n共**{len(records)}个独立执行项通过**：后端171个源测试函数展开为220项，前端30项。全量后端采集到**{summary['http_requests_captured']}次真实TestClient请求响应**，包含登录/准备及业务请求，不是562个独立用例。pytest内核报告40.88秒；前端Vitest报告1.92秒；表中命令耗时还含启动和证据输出。\n\n")
parts.append('### 3.1 测试层级分布\n\n| 层级 | 执行项 |\n|---|---:|\n')
for k,v in summary['layers'].items():parts.append(f'| {k} | {v} |\n')
parts.append('''
### 3.2 并发与幂等的实测值

| 场景 | 补采实际输出 | 验证范围 |
|---|---|---|
| 100线程、100个合成用户抢同座同区间 | 100次服务调用，成功1次、409冲突99次；成功预约ID集合为[1]；测试数据库断言预约总数为1 | 临时文件SQLite、Barrier同步、每线程独立Session；不是200在线用户/P95性能测试 |
| 16线程同用户同键重试 | 16次服务调用均返回成功；首次创建1次、重放15次；预约ID集合[1]；数据库断言总数1 | 真实多Session重试；不证明所有业务写接口均幂等 |

逐次返回值位于[concurrency-case-results.json](evidence/test/2026-11-26-full-suite/concurrency-case-results.json)。补采重跑了上述两项以获取实际值，不把重跑计为新增覆盖。

### 3.3 解释边界与未执行项

1. 当前断言全通过不代表架构差异全部关闭。空正文签到、无门禁主动返回、版本乐观锁缺失、通知失败补偿、两条违规路径和截止整秒冲突，仍按基线DISC/GAP记录处理；已有测试可能仅描述当前实现。
2. 后端test_acceptance_cases.py虽名为acceptance，其本轮性质是本地接口/数据库自动化场景测试，不是人工阶段验收。前端happy-dom、Mock fetch及组件挂载不是浏览器端到端或真实移动端验证。
3. 未进行真实门禁联调、200并发/P95压测、整月可用率、可信NTP偏差、介质损坏RPO=0、真实摄像头/扫码及跨浏览器测试。
4. 无代码覆盖率报告，不能从测试数推导行/分支覆盖率。既有test_case_traceability只证明TC-LOCAL编号存在、被标记，并不证明业务需求完整覆盖。
5. 原有evidence/2026-11-26-tests.md记载152项旧结果，无原始输出可与本轮一一核对；本报告以重新执行的220项为准，不覆盖旧文件、不合并为同一次运行。
6. 警告是Starlette提示httpx TestClient弃用，测试仍通过；未为消警告修改依赖声明或代码。

## 4. 用例索引

| 编号 | 标题 | 层级 | 状态 | 源测试 |
|---|---|---|---|---|
''')
for r in records:parts.append(f"| {r['id']} | {md(r['title'])} | {r['layer']} | {r['result']} | [{r['source']}:{r['line']}](../{r['source']}) |\n")
parts.append('\n## 5. 按模板E整理的全部测试案例\n\n参数化值来自pytest callspec；所有断言表达式直接提取源码。实际输出只陈述运行器状态与实采HTTP/服务值；没有逐值采集的单元返回不填造快照。\n\n')
for r in records:
    parts.append(f"### {r['id']} {r['title']}\n\n| 字段 | 内容 |\n|---|---|\n")
    fields=[('编号/关联依据',r['id']+'；'+r['basis']+('；原标记'+r['legacy_case'] if r['legacy_case'] else '')),('层级',r['layer']),('场景和风险',r['title']+'；'+r['limit']),('前置数据与角色',r['preconditions']),('操作/输入',r['steps']+('；参数：'+json.dumps(r['parameters'],ensure_ascii=False) if r['parameters'] else '')),('预期结果','；'.join(r['assertions']) or r['expected']),('预期确认人','责任安排：'+r['owner']+'；本次按既有断言整理，尚未独立签署业务预期，不填写虚构确认日期。'),('实际输出',r['actual']),('执行结果',r['result']+'；2026-11-26本机自动运行；优先级'+r['priority']+'（本次风险分级）。'),('证据',f"[{r['source']}:{r['line']}](../{r['source']})；`{r['nodeid']}`；[{r['evidence']}](evidence/test/2026-11-26-full-suite/{r['evidence']})按nodeid/fullName定位；版本及环境见本报告§2。")]
    for k,v in fields:parts.append('| '+k+' | '+md(v)+' |\n')
    parts.append('\n')
parts.append('''## 6. 证据与复现

证据入口为[evidence/test/2026-11-26-full-suite/README.md](evidence/test/2026-11-26-full-suite/README.md)。包含全量日志、JUnit、Vitest JSON、逐例HTTP与并发服务输出、环境安装记录、源码SHA-256、未提交补丁、用例数据及采集脚本。

复现时以本轮source-manifest和补丁定位代码，使用合成数据与隔离临时SQLite；按环境版本准备依赖后在backend执行pytest、在frontend执行npm test。外部证据采集插件只增加记录，不改变业务与断言；具体命令和工作目录见各-command.json。标准测试无需采集插件也能运行，但不会产出逐例HTTP记录。

文档整理负责人按团队分工落实，实际执行者为本机自动化工具；交叉复核与课程验收由真实参与成员后续据实记录。本报告不代签。
''')
(ROOT/'docs/单元与集成测试案例及执行报告.md').write_text(''.join(parts),encoding='utf-8')

readme='''# 2026-11-26 全量测试证据

本目录为本次重新执行生成，未沿用旧汇总中的通过数。源代码与测试断言未修改，测试在外部隔离副本运行。

| 证据 | 用途 |
|---|---|
| backend-tests.log / backend-junit.xml | 220项pytest原始输出、逐项结果和警告 |
| backend-case-results.json | 每例参数、夹具、阶段状态及562次实采TestClient响应；凭证脱敏，数组/字符串按采集说明截断 |
| frontend-tests.log / frontend-vitest.json | 8文件30项前端测试原始结果 |
| concurrency-evidence.log / concurrency-junit.xml / concurrency-case-results.json | 两项补采与116次实际服务返回；不重复计入250项 |
| frontend-checks.log | ESLint静态检查，不计测试数 |
| *-command.json | 精确命令、工作目录、起止时间、耗时、退出码 |
| backend-install.log / frontend-install.log | 隔离依赖准备记录 |
| backend-environment.log / frontend-environment.log | 本轮依赖实际版本 |
| source-manifest.json / working-tree-before.patch / git-status-before.txt | 测试前源文件SHA-256、未提交差异及Git状态 |
| copy-exclusions.json | 非测试Office锁文件排除记录 |
| backend-source-inventory.json / frontend-source-inventory.json | 源函数、参数装饰器、源码断言与位置 |
| test-cases.json / summary.json | 文档和Excel共同使用的250条结果、汇总及追溯数据 |
| tooling/ | 本轮运行/采集脚本副本；含本机路径，换环境需调整路径 |
| evidence-manifest.json | 最终证据文件的SHA-256清单，清单自身不递归计算 |

实际结果：后端220通过、前端30通过；两项并发补采通过。100线程实际成功1/冲突99；16线程同键首次创建1/重放15。未声明真实门禁、200并发性能、跨浏览器、RPO=0或人工阶段验收通过。

总体报告：[单元与集成测试案例及执行报告](../../../单元与集成测试案例及执行报告.md)。Excel和报告使用TC-BE/TC-FE编号逐项映射；原TC-LOCAL标记在用例数据保留。

运行时插件包装TestClient请求及补采时的service.create，调用真实原函数并保留返回/异常，不变更断言。单元测试没有独立返回快照时，仅记运行器通过与源码预期，不填造实际数据。HTTP记录不等同完整网络抓包或数据库导出。
'''
(EV/'README.md').write_text(readme,encoding='utf-8')
tooling=EV/'tooling';tooling.mkdir(exist_ok=True)
for name in ['prepare.py','run_command.py','evidence_pytest_plugin.py','frontend_inventory.mjs','compile_report.py']:
    shutil.copy2(TASK/name,tooling/name)
print(json.dumps(summary,ensure_ascii=False,indent=2))
