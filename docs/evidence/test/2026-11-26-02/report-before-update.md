# 智能自习室管理预约系统单元与集成测试案例及执行报告

| 项目 | 内容 |
|---|---|
| 文档版本 | TEST-REPORT-1.0 |
| 项目名称 | 智能自习室管理预约系统 |
| 队名 | 全网呼叫奶家人 |
| 测试组织负责人 | 张东岩（测试整合责任安排） |
| 小组人员 | 周俊博、张东岩、方梓安 |
| 执行日期 | 2026-11-26，Asia/Shanghai |
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
- 证据采集插件在进程内包装TestClient请求，按例记录真实响应并脱敏凭证。数组仅保留前8项，长字符串保留前3000字符；完整断言成功以JUnit和pytest结果为准。没有声称保存完整网络抓包或全部数据库快照。
- 执行结束校验发现三份既有架构／接口文档在共享工作区发生其他编辑变化，已保留，详见source-comparison-after.json；前后端源码及测试内容SHA-256未变化，测试对应执行前隔离快照。

## 3. 实际执行结果

| 范围 | 执行结果 | 原始证据 |
|---|---|---|
| 后端全量 | 220 passed；1条Starlette/httpx弃用警告；命令耗时50.362s，退出码0 | [backend-tests.log](evidence/test/2026-11-26-full-suite/backend-tests.log) |
| 前端全量 | 8个文件、30项通过； | [frontend-tests.log](evidence/test/2026-11-26-full-suite/frontend-tests.log) |
| 并发输出补采 | 2项通过；为服务返回值补采，不计入250个独立用例总数； | [concurrency-evidence.log](evidence/test/2026-11-26-full-suite/concurrency-evidence.log) |
| 前端ESLint | 退出码0；静态检查不计为测试用例； | [frontend-checks.log](evidence/test/2026-11-26-full-suite/frontend-checks.log) |

### 3.1 测试层级分布

| 层级 | 执行项 |
|---|---:|
| 接口／数据库集成 | 107 |
| 服务／数据库集成 | 14 |
| 测试资产一致性 | 2 |
| 单元（命令Mock） | 2 |
| 数据库集成 | 18 |
| 数据库并发集成 | 2 |
| 单元（纯函数） | 7 |
| 单元（Mock隔离） | 68 |
| 前端逻辑单元 | 26 |
| 前端组件单元 | 4 |

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
| TC-BE-001 | 同一座位重叠时段不能并行成功；相邻区间允许 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:117](../backend/tests/test_acceptance_cases.py) |
| TC-BE-002 | 同键同请求重放返回同一预约；不同载荷或用户复用同键返回冲突 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:128](../backend/tests/test_acceptance_cases.py) |
| TC-BE-003 | 未登录访问受保护接口返回 401 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:142](../backend/tests/test_acceptance_cases.py) |
| TC-BE-004 | 普通学生访问管理接口返回 403 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:149](../backend/tests/test_acceptance_cases.py) |
| TC-BE-005 | 使用他人预约或通知 ID 不能读取或修改数据，列表也只返回本人记录 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:162](../backend/tests/test_acceptance_cases.py) |
| TC-BE-006 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T05:59:00+08:00'；end='2026-11-02T08:00:00+08:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py) |
| TC-BE-007 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T22:00:00+08:00'；end='2026-11-02T23:31:00+08:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py) |
| TC-BE-008 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T23:00:00+08:00'；end='2026-11-03T01:00:00+08:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py) |
| TC-BE-009 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-01T09:00:00+08:00'；end='2026-11-01T10:00:00+08:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py) |
| TC-BE-010 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T09:00:00+08:00'；end='2026-11-02T09:00:00+08:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py) |
| TC-BE-011 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T09:00:00'；end='2026-11-02T10:00:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py) |
| TC-BE-012 | 短于 30 分钟的合法时段不应被时长规则拒绝 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:214](../backend/tests/test_acceptance_cases.py) |
| TC-BE-013 | 临时离开超时只释放一次，并至多生成一条违规和一条通知 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:222](../backend/tests/test_acceptance_cases.py) |
| TC-BE-014 | 开始前 15 分钟边界内取消记违规，边界外为正常取消（minutes=16；late=False） | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:253](../backend/tests/test_acceptance_cases.py) |
| TC-BE-015 | 开始前 15 分钟边界内取消记违规，边界外为正常取消（minutes=15；late=True） | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:253](../backend/tests/test_acceptance_cases.py) |
| TC-BE-016 | 开始前 15 分钟边界内取消记违规，边界外为正常取消（minutes=1；late=True） | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:253](../backend/tests/test_acceptance_cases.py) |
| TC-BE-017 | 被禁约用户仍可取消已有预约，但不能新建或改座 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:271](../backend/tests/test_acceptance_cases.py) |
| TC-BE-018 | 申诉只能关联本人，并受期限限制 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:297](../backend/tests/test_acceptance_cases.py) |
| TC-BE-019 | 审核通过时解除禁约，并在同一流程里通知申请人 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:339](../backend/tests/test_acceptance_cases.py) |
| TC-BE-020 | 座位进入维护后取消尚未开始的预约；正在使用的预约不被中断 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:381](../backend/tests/test_acceptance_cases.py) |
| TC-BE-021 | 只有授权角色可管理；非法开放时间或参数不改变已保存值 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:422](../backend/tests/test_acceptance_cases.py) |
| TC-BE-022 | JSON 与 XLSX 使用一致的统计区间和口径；日期倒置或超范围拒绝 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:457](../backend/tests/test_acceptance_cases.py) |
| TC-BE-023 | 只有运维角色可以创建和查看备份 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:517](../backend/tests/test_acceptance_cases.py) |
| TC-BE-024 | 备份轮换后仍可完整性恢复；监控接口只返回定义字段 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:538](../backend/tests/test_acceptance_cases.py) |
| TC-BE-025 | 同一外部事件重放不重复入账 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:587](../backend/tests/test_acceptance_cases.py) |
| TC-BE-026 | 延迟事件和已结束预约上的事件只关联记录，不复活或结束预约 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:618](../backend/tests/test_acceptance_cases.py) |
| TC-BE-027 | 超过临时离开期限后的入馆事件不恢复使用中状态 | 接口／数据库集成 | 通过 | [backend/tests/test_acceptance_cases.py:657](../backend/tests/test_acceptance_cases.py) |
| TC-BE-028 | 非管理员无法管理资源配置 | 接口／数据库集成 | 通过 | [backend/tests/test_admin_config.py:27](../backend/tests/test_admin_config.py) |
| TC-BE-029 | 房间创建编辑关闭与删除 | 接口／数据库集成 | 通过 | [backend/tests/test_admin_config.py:36](../backend/tests/test_admin_config.py) |
| TC-BE-030 | 含座位房间不得直接删除 | 接口／数据库集成 | 通过 | [backend/tests/test_admin_config.py:57](../backend/tests/test_admin_config.py) |
| TC-BE-031 | 开放时段增删改及边界校验 | 接口／数据库集成 | 通过 | [backend/tests/test_admin_config.py:66](../backend/tests/test_admin_config.py) |
| TC-BE-032 | 特殊日期校历维护与校验 | 接口／数据库集成 | 通过 | [backend/tests/test_admin_config.py:94](../backend/tests/test_admin_config.py) |
| TC-BE-033 | 业务参数保存与非法值拒绝 | 接口／数据库集成 | 通过 | [backend/tests/test_admin_config.py:105](../backend/tests/test_admin_config.py) |
| TC-BE-034 | 验证预约请求幂等、本人数据隔离以及同一用户的有效预约上限 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:80](../backend/tests/test_assigned_workflows.py) |
| TC-BE-035 | 验证临时离开超过 30 分钟后释放预约，且重复扫描不会重复处罚 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:139](../backend/tests/test_assigned_workflows.py) |
| TC-BE-036 | 验证预约开始前 15 分钟内取消时生成违规和站内结果通知 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:170](../backend/tests/test_assigned_workflows.py) |
| TC-BE-037 | 验证门禁迟到回调关联预约、提醒本人并保持预约状态不变 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:199](../backend/tests/test_assigned_workflows.py) |
| TC-BE-038 | 验证状态不匹配的门禁入馆事件进入人工处理而不复活已完成预约 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:243](../backend/tests/test_assigned_workflows.py) |
| TC-BE-039 | 验证管理员批准申诉后解除有效禁约并向申请人发送站内通知 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:277](../backend/tests/test_assigned_workflows.py) |
| TC-BE-040 | 验证座位置为维护时会取消未开始预约并向预约人发送站内通知 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:332](../backend/tests/test_assigned_workflows.py) |
| TC-BE-041 | 验证完整座位编辑接口改为维护状态时执行相同的预约取消规则 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:360](../backend/tests/test_assigned_workflows.py) |
| TC-BE-042 | 验证管理员报表按开放座位计算计划时长并生成 Excel 文件 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:386](../backend/tests/test_assigned_workflows.py) |
| TC-BE-043 | 使用中未声明临时离开即出馆：超时结束并记录未声明离开违规 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:430](../backend/tests/test_assigned_workflows.py) |
| TC-BE-044 | 临时离开期间出馆保留座位；30 分钟内入馆恢复使用中，且不产生违规 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:461](../backend/tests/test_assigned_workflows.py) |
| TC-BE-045 | 超过 30 分钟临时离开期限后的入馆事件不恢复座位，转入人工核验 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:512](../backend/tests/test_assigned_workflows.py) |
| TC-BE-046 | 已取消的未来预约只出现在历史列表，不出现在当前预约 | 接口／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:538](../backend/tests/test_assigned_workflows.py) |
| TC-BE-047 | 生产环境沿用默认门禁密钥时配置校验失败；dev/test 或自定义密钥可通过 | 服务／数据库集成 | 通过 | [backend/tests/test_assigned_workflows.py:553](../backend/tests/test_assigned_workflows.py) |
| TC-BE-048 | 注册登录与本人信息查询 | 接口／数据库集成 | 通过 | [backend/tests/test_auth.py:18](../backend/tests/test_auth.py) |
| TC-BE-049 | 数据库保存密码哈希 | 接口／数据库集成 | 通过 | [backend/tests/test_auth.py:31](../backend/tests/test_auth.py) |
| TC-BE-050 | 拒绝重复学号及非法注册输入 | 接口／数据库集成 | 通过 | [backend/tests/test_auth.py:38](../backend/tests/test_auth.py) |
| TC-BE-051 | 登录失败与错误提示 | 接口／数据库集成 | 通过 | [backend/tests/test_auth.py:55](../backend/tests/test_auth.py) |
| TC-BE-052 | 失败次数达到阈值时锁定登录 | 接口／数据库集成 | 通过 | [backend/tests/test_auth.py:68](../backend/tests/test_auth.py) |
| TC-BE-053 | 禁用账号不得登录 | 接口／数据库集成 | 通过 | [backend/tests/test_auth.py:84](../backend/tests/test_auth.py) |
| TC-BE-054 | 注销撤销当前会话 | 接口／数据库集成 | 通过 | [backend/tests/test_auth.py:90](../backend/tests/test_auth.py) |
| TC-BE-055 | 未认证及过期会话被拒绝 | 接口／数据库集成 | 通过 | [backend/tests/test_auth.py:97](../backend/tests/test_auth.py) |
| TC-BE-056 | 改密校验旧密码并撤销会话 | 接口／数据库集成 | 通过 | [backend/tests/test_auth.py:107](../backend/tests/test_auth.py) |
| TC-BE-057 | 通过重置码修改密码 | 接口／数据库集成 | 通过 | [backend/tests/test_auth.py:127](../backend/tests/test_auth.py) |
| TC-BE-058 | 重置码过期及重签失效 | 接口／数据库集成 | 通过 | [backend/tests/test_auth.py:142](../backend/tests/test_auth.py) |
| TC-BE-059 | 备份API仅限运维访问 | 接口／数据库集成 | 通过 | [backend/tests/test_backup_monitoring.py:18](../backend/tests/test_backup_monitoring.py) |
| TC-BE-060 | 备份轮换和数据库恢复 | 服务／数据库集成 | 通过 | [backend/tests/test_backup_monitoring.py:33](../backend/tests/test_backup_monitoring.py) |
| TC-BE-061 | 运行状态接口字段与访问 | 接口／数据库集成 | 通过 | [backend/tests/test_backup_monitoring.py:53](../backend/tests/test_backup_monitoring.py) |
| TC-BE-062 | 登记表中的每个案例都必须至少有一个带 case 标记的测试 | 测试资产一致性 | 通过 | [backend/tests/test_case_traceability.py:19](../backend/tests/test_case_traceability.py) |
| TC-BE-063 | 测试计划文档必须列出登记表中的每个案例编号 | 测试资产一致性 | 通过 | [backend/tests/test_case_traceability.py:26](../backend/tests/test_case_traceability.py) |
| TC-BE-064 | 两次未签退合并为 1 次计入警告；第三次再合并 | 服务／数据库集成 | 通过 | [backend/tests/test_gaps.py:62](../backend/tests/test_gaps.py) |
| TC-BE-065 | 暂离超时使用专用违规类型 | 服务／数据库集成 | 通过 | [backend/tests/test_gaps.py:114](../backend/tests/test_gaps.py) |
| TC-BE-066 | 违规周期到期归档 | 服务／数据库集成 | 通过 | [backend/tests/test_gaps.py:144](../backend/tests/test_gaps.py) |
| TC-BE-067 | 按房间区域自动分配座位 | 接口／数据库集成 | 通过 | [backend/tests/test_gaps.py:167](../backend/tests/test_gaps.py) |
| TC-BE-068 | 座位设施条件筛选 | 接口／数据库集成 | 通过 | [backend/tests/test_gaps.py:188](../backend/tests/test_gaps.py) |
| TC-BE-069 | 关闭房间取消未来预约 | 接口／数据库集成 | 通过 | [backend/tests/test_gaps.py:210](../backend/tests/test_gaps.py) |
| TC-BE-070 | 开放时段调整取消冲突预约 | 接口／数据库集成 | 通过 | [backend/tests/test_gaps.py:239](../backend/tests/test_gaps.py) |
| TC-BE-071 | 健康接口与数据库连通 | 接口／数据库集成 | 通过 | [backend/tests/test_health.py:10](../backend/tests/test_health.py) |
| TC-BE-072 | 服务端时间为UTC加8时区 | 服务／数据库集成 | 通过 | [backend/tests/test_health.py:19](../backend/tests/test_health.py) |
| TC-BE-073 | SQLite外键WAL及忙等待配置 | 服务／数据库集成 | 通过 | [backend/tests/test_health.py:25](../backend/tests/test_health.py) |
| TC-BE-074 | 登录成功失败和注销留痕 | 接口／数据库集成 | 通过 | [backend/tests/test_logs.py:18](../backend/tests/test_logs.py) |
| TC-BE-075 | 登录日志仅运维可读 | 接口／数据库集成 | 通过 | [backend/tests/test_logs.py:35](../backend/tests/test_logs.py) |
| TC-BE-076 | 审计日志过滤与分页 | 接口／数据库集成 | 通过 | [backend/tests/test_logs.py:55](../backend/tests/test_logs.py) |
| TC-BE-077 | 清理到期审计及登录日志 | 服务／数据库集成 | 通过 | [backend/tests/test_logs.py:82](../backend/tests/test_logs.py) |
| TC-BE-078 | 演示数据重复导入与重置 | 服务／数据库集成 | 通过 | [backend/tests/test_mock_data.py:42](../backend/tests/test_mock_data.py) |
| TC-BE-079 | 演示数据数量及状态组合 | 服务／数据库集成 | 通过 | [backend/tests/test_mock_data.py:51](../backend/tests/test_mock_data.py) |
| TC-BE-080 | 演示预约不重叠且处于开放时间 | 服务／数据库集成 | 通过 | [backend/tests/test_mock_data.py:78](../backend/tests/test_mock_data.py) |
| TC-BE-081 | 演示数据不会被扫尾误处理 | 服务／数据库集成 | 通过 | [backend/tests/test_mock_data.py:110](../backend/tests/test_mock_data.py) |
| TC-BE-082 | 演示角色账号可登录 | 接口／数据库集成 | 通过 | [backend/tests/test_mock_data.py:118](../backend/tests/test_mock_data.py) |
| TC-BE-083 | 生产环境拒绝导入演示数据 | 服务／数据库集成 | 通过 | [backend/tests/test_mock_data.py:127](../backend/tests/test_mock_data.py) |
| TC-BE-084 | 开发脚本迁移与演示数据准备 | 单元（命令Mock） | 通过 | [backend/tests/test_mock_data.py:140](../backend/tests/test_mock_data.py) |
| TC-BE-085 | 开发脚本命令行参数 | 单元（命令Mock） | 通过 | [backend/tests/test_mock_data.py:160](../backend/tests/test_mock_data.py) |
| TC-BE-086 | 迁移创建全部模型表 | 数据库集成 | 通过 | [backend/tests/test_models.py:76](../backend/tests/test_models.py) |
| TC-BE-087 | 数据库迁移可重复及可逆 | 数据库集成 | 通过 | [backend/tests/test_models.py:83](../backend/tests/test_models.py) |
| TC-BE-088 | 迁移与 ORM 模型一致（等同 alembic check） | 数据库集成 | 通过 | [backend/tests/test_models.py:96](../backend/tests/test_models.py) |
| TC-BE-089 | 数据库初始角色齐全 | 数据库集成 | 通过 | [backend/tests/test_models.py:101](../backend/tests/test_models.py) |
| TC-BE-090 | 用户学号唯一约束 | 数据库集成 | 通过 | [backend/tests/test_models.py:109](../backend/tests/test_models.py) |
| TC-BE-091 | 数据库强制外键约束 | 数据库集成 | 通过 | [backend/tests/test_models.py:117](../backend/tests/test_models.py) |
| TC-BE-092 | 房间内座位编号唯一 | 数据库集成 | 通过 | [backend/tests/test_models.py:123](../backend/tests/test_models.py) |
| TC-BE-093 | 数据库枚举检查约束 | 数据库集成 | 通过 | [backend/tests/test_models.py:130](../backend/tests/test_models.py) |
| TC-BE-094 | ORM拒绝非法枚举 | 数据库集成 | 通过 | [backend/tests/test_models.py:140](../backend/tests/test_models.py) |
| TC-BE-095 | 数据库拒绝无效预约起止顺序 | 数据库集成 | 通过 | [backend/tests/test_models.py:145](../backend/tests/test_models.py) |
| TC-BE-096 | 同座同起点有效预约唯一约束 | 数据库集成 | 通过 | [backend/tests/test_models.py:156](../backend/tests/test_models.py) |
| TC-BE-097 | 门禁来源事件号唯一约束 | 数据库集成 | 通过 | [backend/tests/test_models.py:176](../backend/tests/test_models.py) |
| TC-BE-098 | 日期时间按北京时间往返存取 | 数据库集成 | 通过 | [backend/tests/test_models.py:194](../backend/tests/test_models.py) |
| TC-BE-099 | 拒绝无时区日期时间入库 | 数据库集成 | 通过 | [backend/tests/test_models.py:208](../backend/tests/test_models.py) |
| TC-BE-100 | 业务异常回滚全部事务变化 | 数据库集成 | 通过 | [backend/tests/test_models.py:219](../backend/tests/test_models.py) |
| TC-BE-101 | 数据库约束失败回滚事务 | 数据库集成 | 通过 | [backend/tests/test_models.py:231](../backend/tests/test_models.py) |
| TC-BE-102 | 成功事务正常提交 | 数据库集成 | 通过 | [backend/tests/test_models.py:241](../backend/tests/test_models.py) |
| TC-BE-103 | BEGIN IMMEDIATE 一开始就持有写锁：另一连接的写事务在 busy_timeout 后失败 | 数据库集成 | 通过 | [backend/tests/test_models.py:248](../backend/tests/test_models.py) |
| TC-BE-104 | 数据库权限矩阵与代码一致 | 服务／数据库集成 | 通过 | [backend/tests/test_permissions.py:11](../backend/tests/test_permissions.py) |
| TC-BE-105 | 本人接口返回角色权限集合 | 接口／数据库集成 | 通过 | [backend/tests/test_permissions.py:22](../backend/tests/test_permissions.py) |
| TC-BE-106 | 仅管理员能够管理用户 | 接口／数据库集成 | 通过 | [backend/tests/test_permissions.py:29](../backend/tests/test_permissions.py) |
| TC-BE-107 | 管理员角色变更及审计 | 接口／数据库集成 | 通过 | [backend/tests/test_permissions.py:39](../backend/tests/test_permissions.py) |
| TC-BE-108 | 管理员不得自降权或自禁用 | 接口／数据库集成 | 通过 | [backend/tests/test_permissions.py:59](../backend/tests/test_permissions.py) |
| TC-BE-109 | 禁用账号撤销会话并拒绝登录 | 接口／数据库集成 | 通过 | [backend/tests/test_permissions.py:69](../backend/tests/test_permissions.py) |
| TC-BE-110 | 管理员为目标用户签发重置码 | 接口／数据库集成 | 通过 | [backend/tests/test_permissions.py:85](../backend/tests/test_permissions.py) |
| TC-BE-111 | CLI创建管理员账号 | 接口／数据库集成 | 通过 | [backend/tests/test_permissions.py:101](../backend/tests/test_permissions.py) |
| TC-BE-112 | 房间搜索详情及区间座位状态 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:94](../backend/tests/test_reservations.py) |
| TC-BE-113 | 资源查询拒绝不完整或非法时间（query='date=2026-11-02'） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:146](../backend/tests/test_reservations.py) |
| TC-BE-114 | 资源查询拒绝不完整或非法时间（query='start_time=09:00&end_time=10:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:146](../backend/tests/test_reservations.py) |
| TC-BE-115 | 资源查询拒绝不完整或非法时间（query='date=2026-11-02&start_time=23:00&end_time=01:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:146](../backend/tests/test_reservations.py) |
| TC-BE-116 | 资源查询拒绝不完整或非法时间（query='zone_type=unknown'） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:146](../backend/tests/test_reservations.py) |
| TC-BE-117 | 校历优先级生效日期与关闭房间 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:150](../backend/tests/test_reservations.py) |
| TC-BE-118 | 创建预约拒绝非法时间（start='2026-11-02T05:59:00+08:00'；end='2026-11-02T08:00:00+08:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py) |
| TC-BE-119 | 创建预约拒绝非法时间（start='2026-11-02T22:00:00+08:00'；end='2026-11-02T23:31:00+08:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py) |
| TC-BE-120 | 创建预约拒绝非法时间（start='2026-11-02T23:00:00+08:00'；end='2026-11-03T01:00:00+08:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py) |
| TC-BE-121 | 创建预约拒绝非法时间（start='2026-11-04T09:00:00+08:00'；end='2026-11-04T10:00:00+08:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py) |
| TC-BE-122 | 创建预约拒绝非法时间（start='2026-11-02T09:00:00+08:00'；end='2026-11-02T09:00:00+08:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py) |
| TC-BE-123 | 创建预约拒绝非法时间（start='2026-11-02T09:00:00'；end='2026-11-02T10:00:00'） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py) |
| TC-BE-124 | 当天次日短时段与全天开放预约 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:187](../backend/tests/test_reservations.py) |
| TC-BE-125 | 座位及本人冲突相邻区间与时区转换 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:196](../backend/tests/test_reservations.py) |
| TC-BE-126 | 无键现状及幂等键用户载荷范围 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:208](../backend/tests/test_reservations.py) |
| TC-BE-127 | 换座重查冲突且失败保留原预约 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:236](../backend/tests/test_reservations.py) |
| TC-BE-128 | 取消15分钟边界及未到场违规互斥（minutes=16；late=False） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:256](../backend/tests/test_reservations.py) |
| TC-BE-129 | 取消15分钟边界及未到场违规互斥（minutes=15；late=True） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:256](../backend/tests/test_reservations.py) |
| TC-BE-130 | 取消15分钟边界及未到场违规互斥（minutes=1；late=True） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:256](../backend/tests/test_reservations.py) |
| TC-BE-131 | 禁约允许取消但拒绝创建换座 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:276](../backend/tests/test_reservations.py) |
| TC-BE-132 | 签到窗口前缘边界（minute=44；second=59；success=False） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:303](../backend/tests/test_reservations.py) |
| TC-BE-133 | 签到窗口前缘边界（minute=45；second=0；success=True） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:303](../backend/tests/test_reservations.py) |
| TC-BE-134 | 签到后缘边界与窗内不处罚（minute=0；microsecond=0；success=True） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:315](../backend/tests/test_reservations.py) |
| TC-BE-135 | 签到后缘边界与窗内不处罚（minute=15；microsecond=0；success=True） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:315](../backend/tests/test_reservations.py) |
| TC-BE-136 | 签到后缘边界与窗内不处罚（minute=15；microsecond=1；success=False） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:315](../backend/tests/test_reservations.py) |
| TC-BE-137 | 签到后缘边界与窗内不处罚（minute=16；microsecond=0；success=False） | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:315](../backend/tests/test_reservations.py) |
| TC-BE-138 | 签到归属座位重复及状态转换 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:332](../backend/tests/test_reservations.py) |
| TC-BE-139 | 无人请求时后台释放及去重 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:353](../backend/tests/test_reservations.py) |
| TC-BE-140 | 查询补扫释放并保留维护状态 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:382](../backend/tests/test_reservations.py) |
| TC-BE-141 | 本人预约隔离及运维权限 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:393](../backend/tests/test_reservations.py) |
| TC-BE-142 | 取消审计异常回滚违规及释放 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:414](../backend/tests/test_reservations.py) |
| TC-BE-143 | 100线程竞争同座仅一条预约成功 | 数据库并发集成 | 通过 | [backend/tests/test_reservations.py:431](../backend/tests/test_reservations.py) |
| TC-BE-144 | 16线程同键重试仅一次创建 | 数据库并发集成 | 通过 | [backend/tests/test_reservations.py:462](../backend/tests/test_reservations.py) |
| TC-BE-145 | 写锁繁忙503及同键恢复重试 | 接口／数据库集成 | 通过 | [backend/tests/test_reservations.py:476](../backend/tests/test_reservations.py) |
| TC-BE-146 | 密码长度字符类别及字节上限 | 单元（纯函数） | 通过 | [backend/tests/test_units.py:18](../backend/tests/test_units.py) |
| TC-BE-147 | 学号格式有效及非法输入 | 单元（纯函数） | 通过 | [backend/tests/test_units.py:26](../backend/tests/test_units.py) |
| TC-BE-148 | 密码哈希验证不暴露明文 | 单元（纯函数） | 通过 | [backend/tests/test_units.py:34](../backend/tests/test_units.py) |
| TC-BE-149 | 会话摘要稳定且不等于原令牌 | 单元（纯函数） | 通过 | [backend/tests/test_units.py:42](../backend/tests/test_units.py) |
| TC-BE-150 | 角色权限投影与组合 | 单元（纯函数） | 通过 | [backend/tests/test_units.py:49](../backend/tests/test_units.py) |
| TC-BE-151 | 统一时钟带北京时间时区 | 单元（纯函数） | 通过 | [backend/tests/test_units.py:61](../backend/tests/test_units.py) |
| TC-BE-152 | 门禁脱敏键稳定且隐藏学号 | 单元（纯函数） | 通过 | [backend/tests/test_units.py:67](../backend/tests/test_units.py) |
| TC-BE-153 | 取消15分钟边界分类（seconds=901；late=False） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_cancel_reservation.py:13](../backend/tests/units/test_cancel_reservation.py) |
| TC-BE-154 | 取消15分钟边界分类（seconds=900；late=True） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_cancel_reservation.py:13](../backend/tests/units/test_cancel_reservation.py) |
| TC-BE-155 | 取消15分钟边界分类（seconds=899；late=True） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_cancel_reservation.py:13](../backend/tests/units/test_cancel_reservation.py) |
| TC-BE-156 | 重复取消不重复违规和通知 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_cancel_reservation.py:33](../backend/tests/units/test_cancel_reservation.py) |
| TC-BE-157 | 非已预约状态拒绝取消（status=<ReservationStatus.ACTIVE: 'ACTIVE'>） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_cancel_reservation.py:47](../backend/tests/units/test_cancel_reservation.py) |
| TC-BE-158 | 非已预约状态拒绝取消（status=<ReservationStatus.EXPIRED: 'EXPIRED'>） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_cancel_reservation.py:47](../backend/tests/units/test_cancel_reservation.py) |
| TC-BE-159 | 预约开始后拒绝取消（seconds=0） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_cancel_reservation.py:56](../backend/tests/units/test_cancel_reservation.py) |
| TC-BE-160 | 预约开始后拒绝取消（seconds=-1） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_cancel_reservation.py:56](../backend/tests/units/test_cancel_reservation.py) |
| TC-BE-161 | 换座保留起止时间 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_change_seat.py:15](../backend/tests/units/test_change_seat.py) |
| TC-BE-162 | 仅未签到预约允许换座（status=<ReservationStatus.ACTIVE: 'ACTIVE'>） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_change_seat.py:31](../backend/tests/units/test_change_seat.py) |
| TC-BE-163 | 仅未签到预约允许换座（status=<ReservationStatus.CANCELLED: 'CANCELLED'>） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_change_seat.py:31](../backend/tests/units/test_change_seat.py) |
| TC-BE-164 | 已超窗预约拒绝换座 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_change_seat.py:39](../backend/tests/units/test_change_seat.py) |
| TC-BE-165 | 目标冲突时原座位不变 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_change_seat.py:46](../backend/tests/units/test_change_seat.py) |
| TC-BE-166 | 换座请求拒绝修改时间字段 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_change_seat.py:55](../backend/tests/units/test_change_seat.py) |
| TC-BE-167 | 扫码及编号在签到窗口内成功（offset=-900；arrival_status=<ArrivalStatus.EARLY: 'early'>；use_code=False） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-168 | 扫码及编号在签到窗口内成功（offset=-900；arrival_status=<ArrivalStatus.EARLY: 'early'>；use_code=True） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-169 | 扫码及编号在签到窗口内成功（offset=0；arrival_status=<ArrivalStatus.ON_TIME: 'on_time'>；use_code=False） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-170 | 扫码及编号在签到窗口内成功（offset=0；arrival_status=<ArrivalStatus.ON_TIME: 'on_time'>；use_code=True） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-171 | 扫码及编号在签到窗口内成功（offset=900；arrival_status=<ArrivalStatus.LATE: 'late'>；use_code=False） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-172 | 扫码及编号在签到窗口内成功（offset=900；arrival_status=<ArrivalStatus.LATE: 'late'>；use_code=True） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-173 | 扫码座位必须匹配本人预约 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:37](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-174 | 窗口开放前拒绝签到 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:44](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-175 | 重复扫码不重复签到 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:51](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-176 | 未签到宽限截止整秒判定（offset=900；expected=False） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:58](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-177 | 未签到宽限截止整秒判定（offset=901；expected=True） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:58](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-178 | 预约结束优先于未签到宽限 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:62](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-179 | 超窗签到触发失效处理 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:67](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-180 | 失效记录未到场并释放座位 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:77](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-181 | 失效释放保留座位维护状态 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:91](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-182 | 到期扫描处理候选预约（count=0） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:99](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-183 | 到期扫描处理候选预约（count=2） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_checkin_expiry.py:99](../backend/tests/units/test_checkin_expiry.py) |
| TC-BE-184 | 同键同载荷重放不再写入 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_concurrency_idempotency.py:14](../backend/tests/units/test_concurrency_idempotency.py) |
| TC-BE-185 | 幂等键不得跨用户或载荷复用（other_user=True；other_payload=False） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_concurrency_idempotency.py:33](../backend/tests/units/test_concurrency_idempotency.py) |
| TC-BE-186 | 幂等键不得跨用户或载荷复用（other_user=False；other_payload=True） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_concurrency_idempotency.py:33](../backend/tests/units/test_concurrency_idempotency.py) |
| TC-BE-187 | 业务事务请求立即写锁 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_concurrency_idempotency.py:48](../backend/tests/units/test_concurrency_idempotency.py) |
| TC-BE-188 | 锁忙及唯一异常映射业务错误（failure=OperationalError('(builtins.Exception) database is locked')；code=503） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_concurrency_idempotency.py:71](../backend/tests/units/test_concurrency_idempotency.py) |
| TC-BE-189 | 锁忙及唯一异常映射业务错误（failure=OperationalError('(builtins.Exception) database is busy')；code=503） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_concurrency_idempotency.py:71](../backend/tests/units/test_concurrency_idempotency.py) |
| TC-BE-190 | 锁忙及唯一异常映射业务错误（failure=IntegrityError('(builtins.Exception) unique constraint')；code=409） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_concurrency_idempotency.py:71](../backend/tests/units/test_concurrency_idempotency.py) |
| TC-BE-191 | 无关数据库异常原样抛出 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_concurrency_idempotency.py:79](../backend/tests/units/test_concurrency_idempotency.py) |
| TC-BE-192 | 创建写入预约及到达占位 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_create_reservation.py:14](../backend/tests/units/test_create_reservation.py) |
| TC-BE-193 | 创建拒绝过去及超提前期开始时间（offset=datetime.timedelta(days=-1, seconds=86340)） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_create_reservation.py:33](../backend/tests/units/test_create_reservation.py) |
| TC-BE-194 | 创建拒绝过去及超提前期开始时间（offset=datetime.timedelta(days=2)） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_create_reservation.py:33](../backend/tests/units/test_create_reservation.py) |
| TC-BE-195 | 时段检查拒绝关闭或重叠冲突（covered=False；overlaps=False；own_conflict=False；code=422） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_create_reservation.py:46](../backend/tests/units/test_create_reservation.py) |
| TC-BE-196 | 时段检查拒绝关闭或重叠冲突（covered=True；overlaps=True；own_conflict=False；code=409） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_create_reservation.py:46](../backend/tests/units/test_create_reservation.py) |
| TC-BE-197 | 时段检查拒绝关闭或重叠冲突（covered=True；overlaps=False；own_conflict=True；code=409） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_create_reservation.py:46](../backend/tests/units/test_create_reservation.py) |
| TC-BE-198 | 换座时冲突检查排除本预约 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_create_reservation.py:57](../backend/tests/units/test_create_reservation.py) |
| TC-BE-199 | 模型拒绝零负或跨日区间（minutes=0） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_create_reservation.py:64](../backend/tests/units/test_create_reservation.py) |
| TC-BE-200 | 模型拒绝零负或跨日区间（minutes=-1） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_create_reservation.py:64](../backend/tests/units/test_create_reservation.py) |
| TC-BE-201 | 模型拒绝零负或跨日区间（minutes=1440） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_create_reservation.py:64](../backend/tests/units/test_create_reservation.py) |
| TC-BE-202 | 合法无冲突时段通过检查 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_create_reservation.py:69](../backend/tests/units/test_create_reservation.py) |
| TC-BE-203 | 房间列表包含位置容量开放时间 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_room_search.py:11](../backend/tests/units/test_room_search.py) |
| TC-BE-204 | 无房间返回空列表 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_room_search.py:26](../backend/tests/units/test_room_search.py) |
| TC-BE-205 | 搜索不存在房间返回404 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_room_search.py:30](../backend/tests/units/test_room_search.py) |
| TC-BE-206 | 搜索仅可用座位过滤（available_only=False；expected=[11, 12]） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_room_search.py:39](../backend/tests/units/test_room_search.py) |
| TC-BE-207 | 搜索仅可用座位过滤（available_only=True；expected=[11]） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_room_search.py:39](../backend/tests/units/test_room_search.py) |
| TC-BE-208 | 搜索生成房间区域设施筛选条件（flag=True） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_room_search.py:57](../backend/tests/units/test_room_search.py) |
| TC-BE-209 | 搜索生成房间区域设施筛选条件（flag=False） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_room_search.py:57](../backend/tests/units/test_room_search.py) |
| TC-BE-210 | 维护关闭停用座位保持原状态（status=<SeatStatus.MAINTENANCE: 'maintenance'>） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_seat_detail.py:12](../backend/tests/units/test_seat_detail.py) |
| TC-BE-211 | 维护关闭停用座位保持原状态（status=<SeatStatus.CLOSED: 'closed'>） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_seat_detail.py:12](../backend/tests/units/test_seat_detail.py) |
| TC-BE-212 | 维护关闭停用座位保持原状态（status=<SeatStatus.DISABLED: 'disabled'>） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_seat_detail.py:12](../backend/tests/units/test_seat_detail.py) |
| TC-BE-213 | 房间关闭或非开放时间显示关闭（room_open=False；covered=True） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_seat_detail.py:19](../backend/tests/units/test_seat_detail.py) |
| TC-BE-214 | 房间关闭或非开放时间显示关闭（room_open=True；covered=False） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_seat_detail.py:19](../backend/tests/units/test_seat_detail.py) |
| TC-BE-215 | 有效预约映射座位实时状态（status=None；expected=<SeatStatus.AVAILABLE: 'available'>） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_seat_detail.py:36](../backend/tests/units/test_seat_detail.py) |
| TC-BE-216 | 有效预约映射座位实时状态（status=<ReservationStatus.RESERVED: 'RESERVED'>；expected=<SeatStatus.RESERVED: 'reserved'>） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_seat_detail.py:36](../backend/tests/units/test_seat_detail.py) |
| TC-BE-217 | 有效预约映射座位实时状态（status=<ReservationStatus.ACTIVE: 'ACTIVE'>；expected=<SeatStatus.IN_USE: 'in_use'>） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_seat_detail.py:36](../backend/tests/units/test_seat_detail.py) |
| TC-BE-218 | 有效预约映射座位实时状态（status=<ReservationStatus.TEMP_LEAVE: 'TEMP_LEAVE'>；expected=<SeatStatus.IN_USE: 'in_use'>） | 单元（Mock隔离） | 通过 | [backend/tests/units/test_seat_detail.py:36](../backend/tests/units/test_seat_detail.py) |
| TC-BE-219 | 未来预约不占据当前空闲状态 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_seat_detail.py:46](../backend/tests/units/test_seat_detail.py) |
| TC-BE-220 | 座位详情设施与二维码载荷 | 单元（Mock隔离） | 通过 | [backend/tests/units/test_seat_detail.py:52](../backend/tests/units/test_seat_detail.py) |
| TC-FE-001 | 保存及清除浏览器会话令牌 | 前端逻辑单元 | 通过 | [frontend/src/api/client.test.js:20](../frontend/src/api/client.test.js) |
| TC-FE-002 | 请求携带Bearer并解析JSON | 前端逻辑单元 | 通过 | [frontend/src/api/client.test.js:29](../frontend/src/api/client.test.js) |
| TC-FE-003 | 204无正文响应返回null | 前端逻辑单元 | 通过 | [frontend/src/api/client.test.js:42](../frontend/src/api/client.test.js) |
| TC-FE-004 | 展示后端字符串错误提示 | 前端逻辑单元 | 通过 | [frontend/src/api/client.test.js:47](../frontend/src/api/client.test.js) |
| TC-FE-005 | 拼接字段校验错误信息 | 前端逻辑单元 | 通过 | [frontend/src/api/client.test.js:58](../frontend/src/api/client.test.js) |
| TC-FE-006 | 提取对象错误并保留状态码 | 前端逻辑单元 | 通过 | [frontend/src/api/client.test.js:69](../frontend/src/api/client.test.js) |
| TC-FE-007 | 缺少详情时提示资源冲突 | 前端逻辑单元 | 通过 | [frontend/src/api/client.test.js:85](../frontend/src/api/client.test.js) |
| TC-FE-008 | 响应不可解析时显示HTTP状态 | 前端逻辑单元 | 通过 | [frontend/src/api/client.test.js:90](../frontend/src/api/client.test.js) |
| TC-FE-009 | 无令牌时保持未登录且不请求本人 | 前端逻辑单元 | 通过 | [frontend/src/auth.test.js:21](../frontend/src/auth.test.js) |
| TC-FE-010 | 失效会话清除令牌及用户信息 | 前端逻辑单元 | 通过 | [frontend/src/auth.test.js:30](../frontend/src/auth.test.js) |
| TC-FE-011 | 登录后保存会话用户及权限 | 前端逻辑单元 | 通过 | [frontend/src/auth.test.js:39](../frontend/src/auth.test.js) |
| TC-FE-012 | 注销请求失败也清理本地会话 | 前端逻辑单元 | 通过 | [frontend/src/auth.test.js:53](../frontend/src/auth.test.js) |
| TC-FE-013 | 空状态组件无操作时仅显示标题 | 前端组件单元 | 通过 | [frontend/src/components/EmptyState.test.js:11](../frontend/src/components/EmptyState.test.js) |
| TC-FE-014 | 空状态组件展示下一步链接 | 前端组件单元 | 通过 | [frontend/src/components/EmptyState.test.js:20](../frontend/src/components/EmptyState.test.js) |
| TC-FE-015 | 状态组件显示已知中文标签 | 前端组件单元 | 通过 | [frontend/src/components/StatusBadge.test.js:7](../frontend/src/components/StatusBadge.test.js) |
| TC-FE-016 | 状态组件保留未知状态原文 | 前端组件单元 | 通过 | [frontend/src/components/StatusBadge.test.js:13](../frontend/src/components/StatusBadge.test.js) |
| TC-FE-017 | 确认对话框仅主动确认返回true | 前端逻辑单元 | 通过 | [frontend/src/confirm.test.js:6](../frontend/src/confirm.test.js) |
| TC-FE-018 | 打开新对话框取消已有待确认操作 | 前端逻辑单元 | 通过 | [frontend/src/confirm.test.js:17](../frontend/src/confirm.test.js) |
| TC-FE-019 | 输入框确认返回文本取消返回null | 前端逻辑单元 | 通过 | [frontend/src/confirm.test.js:28](../frontend/src/confirm.test.js) |
| TC-FE-020 | 区域文案翻译及未知值回退 | 前端逻辑单元 | 通过 | [frontend/src/labels.test.js:6](../frontend/src/labels.test.js) |
| TC-FE-021 | 违规文案兼容大小写及未知值 | 前端逻辑单元 | 通过 | [frontend/src/labels.test.js:16](../frontend/src/labels.test.js) |
| TC-FE-022 | 设施文案仅组合实际具备项目 | 前端逻辑单元 | 通过 | [frontend/src/labels.test.js:25](../frontend/src/labels.test.js) |
| TC-FE-023 | 未登录访问受保护页跳转并保存目标 | 前端逻辑单元 | 通过 | [frontend/src/router/guard.test.js:10](../frontend/src/router/guard.test.js) |
| TC-FE-024 | 导航前只加载一次未初始化会话 | 前端逻辑单元 | 通过 | [frontend/src/router/guard.test.js:21](../frontend/src/router/guard.test.js) |
| TC-FE-025 | 缺少页面权限时阻止导航 | 前端逻辑单元 | 通过 | [frontend/src/router/guard.test.js:32](../frontend/src/router/guard.test.js) |
| TC-FE-026 | 任一允许权限匹配即可导航 | 前端逻辑单元 | 通过 | [frontend/src/router/guard.test.js:51](../frontend/src/router/guard.test.js) |
| TC-FE-027 | 公共页面不要求登录 | 前端逻辑单元 | 通过 | [frontend/src/router/guard.test.js:64](../frontend/src/router/guard.test.js) |
| TC-FE-028 | 优先使用用户保存主题 | 前端逻辑单元 | 通过 | [frontend/src/theme.test.js:21](../frontend/src/theme.test.js) |
| TC-FE-029 | 未保存有效主题时跟随系统 | 前端逻辑单元 | 通过 | [frontend/src/theme.test.js:30](../frontend/src/theme.test.js) |
| TC-FE-030 | 切换主题后保存选择并停止跟随 | 前端逻辑单元 | 通过 | [frontend/src/theme.test.js:39](../frontend/src/theme.test.js) |

## 5. 按模板E整理的全部测试案例

参数化值来自pytest callspec；所有断言表达式直接提取源码。实际输出只陈述运行器状态与实采HTTP/服务值；没有逐值采集的单元返回不填造快照。

### TC-BE-001 同一座位重叠时段不能并行成功；相邻区间允许

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-001；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-001 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 同一座位重叠时段不能并行成功；相邻区间允许；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 3, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T10:00:00+08:00", "end_time": "2026-11-02T11:00:00+08:00"} |
| 预期结果 | first.status_code == 201；reserve(client, actors.b, seats.a).status_code == 409；reserve(client, actors.a, seats.c).status_code == 409；reserve(client, actors.b, seats.a, body=adjacent).status_code == 201 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.335s。 实采HTTP 6次，状态分布{"200": 2, "201": 2, "409": 2}。POST /api/reservations → 409 {"detail": "你在该时段已有有效预约"} POST /api/reservations → 201 {"id": 2, "reservation_no": "SR20261102080000551FCD", "user_id": 2, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T10:00:00+08:00", "end_time": "2026-11-02T11:00:00+08:00", "status": "RESERVE… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:117](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_001_overlapping_slot_conflicts_and_adjacent_slot_succeeds`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-002 同键同请求重放返回同一预约；不同载荷或用户复用同键返回冲突

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-002；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-001 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 同键同请求重放返回同一预约；不同载荷或用户复用同键返回冲突；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 2, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"} |
| 预期结果 | first.status_code == 201 and replay.status_code == 200；replay.headers['Idempotent-Replayed'] == 'true'；replay.json()['id'] == first.json()['id']；count(api_db, Reservation) == 1；reserve(client, actors.a, seats.b, key=key).status_code == 409；reserve(client, actors.b, seats.a, key=key).status_code == 409 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.224s。 实采HTTP 6次，状态分布{"200": 3, "201": 1, "409": 2}。POST /api/reservations → 409 {"detail": "幂等键已被不同请求使用，请重新提交"} POST /api/reservations → 409 {"detail": "幂等键已被不同请求使用，请重新提交"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:128](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_001_idempotency_key_replays_same_reservation`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-003 未登录访问受保护接口返回 401

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-003；SRS FR-001～007、NFR-005/011；权限矩阵；原标记TC-LOCAL-002 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 未登录访问受保护接口返回 401；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/auth/me；GET /api/reservations/current；GET /api/notifications |
| 预期结果 | client.get(path).status_code == 401 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.160s。 实采HTTP 3次，状态分布{"401": 3}。GET /api/reservations/current → 401 {"detail": "请先登录"} GET /api/notifications → 401 {"detail": "请先登录"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:142](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_002_unauthenticated_requests_are_rejected`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-004 普通学生访问管理接口返回 403

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-004；SRS FR-001～007、NFR-005/011；权限矩阵；原标记TC-LOCAL-002 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 普通学生访问管理接口返回 403；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/admin/settings；GET /api/admin/users；POST /api/admin/rooms，JSON={"name": "越权自习室", "location": "图书馆", "capacity": 10} |
| 预期结果 | client.get('/api/admin/settings', headers=actors.a).status_code == 403；client.get('/api/admin/users', headers=actors.a).status_code == 403；created.status_code == 403 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.273s。 实采HTTP 5次，状态分布{"200": 2, "403": 3}。GET /api/admin/users → 403 {"detail": "无权限执行此操作"} POST /api/admin/rooms → 403 {"detail": "无权限执行此操作"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:149](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_002_missing_permission_returns_403`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-005 使用他人预约或通知 ID 不能读取或修改数据，列表也只返回本人记录

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-005；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-002 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 使用他人预约或通知 ID 不能读取或修改数据，列表也只返回本人记录；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；GET /api/reservations/1；POST /api/reservations/1/cancel；PATCH /api/reservations/1/seat，JSON={"seat_id": 2}；GET /api/reservations；GET /api/notifications；POST /api/notifications/2/read |
| 预期结果 | client.get(f'/api/reservations/{rid}', headers=actors.b).status_code == 404；client.post(f'/api/reservations/{rid}/cancel', headers=actors.b).status_code == 404；changed.status_code == 404；all((row['id'] != rid for row in current))；all((item['id'] != note_id for item in listed))；denied.status_code == 404 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.247s。 实采HTTP 9次，状态分布{"200": 4, "201": 1, "404": 4}。GET /api/notifications → 200 [] POST /api/notifications/2/read → 404 {"detail": "通知不存在"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:162](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_002_other_users_reservation_is_invisible`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-006 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T05:59:00+08:00'；end='2026-11-02T08:00:00+08:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-006；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-003 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T05:59:00+08:00'；end='2026-11-02T08:00:00+08:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T05:59:00+08:00", "end_time": "2026-11-02T08:00:00+08:00"}；本例参数：start='2026-11-02T05:59:00+08:00'；end='2026-11-02T08:00:00+08:00'；参数：{"start": "'2026-11-02T05:59:00+08:00'", "end": "'2026-11-02T08:00:00+08:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.196s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": "时段须完整落在自习室开放时间内（06:00–23:30，不跨零点）"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_003_invalid_times_are_rejected[2026-11-02T05:59:00+08:00-2026-11-02T08:00:00+08:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-007 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T22:00:00+08:00'；end='2026-11-02T23:31:00+08:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-007；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-003 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T22:00:00+08:00'；end='2026-11-02T23:31:00+08:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T22:00:00+08:00", "end_time": "2026-11-02T23:31:00+08:00"}；本例参数：start='2026-11-02T22:00:00+08:00'；end='2026-11-02T23:31:00+08:00'；参数：{"start": "'2026-11-02T22:00:00+08:00'", "end": "'2026-11-02T23:31:00+08:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.195s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": "时段须完整落在自习室开放时间内（06:00–23:30，不跨零点）"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_003_invalid_times_are_rejected[2026-11-02T22:00:00+08:00-2026-11-02T23:31:00+08:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-008 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T23:00:00+08:00'；end='2026-11-03T01:00:00+08:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-008；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-003 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T23:00:00+08:00'；end='2026-11-03T01:00:00+08:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T23:00:00+08:00", "end_time": "2026-11-03T01:00:00+08:00"}；本例参数：start='2026-11-02T23:00:00+08:00'；end='2026-11-03T01:00:00+08:00'；参数：{"start": "'2026-11-02T23:00:00+08:00'", "end": "'2026-11-03T01:00:00+08:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.188s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": "Value error, 预约不可跨零点"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_003_invalid_times_are_rejected[2026-11-02T23:00:00+08:00-2026-11-03T01:00:00+08:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-009 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-01T09:00:00+08:00'；end='2026-11-01T10:00:00+08:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-009；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-003 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-01T09:00:00+08:00'；end='2026-11-01T10:00:00+08:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-01T09:00:00+08:00", "end_time": "2026-11-01T10:00:00+08:00"}；本例参数：start='2026-11-01T09:00:00+08:00'；end='2026-11-01T10:00:00+08:00'；参数：{"start": "'2026-11-01T09:00:00+08:00'", "end": "'2026-11-01T10:00:00+08:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.191s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": "预约开始时间不能早于当前时间"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_003_invalid_times_are_rejected[2026-11-01T09:00:00+08:00-2026-11-01T10:00:00+08:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-010 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T09:00:00+08:00'；end='2026-11-02T09:00:00+08:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-010；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-003 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T09:00:00+08:00'；end='2026-11-02T09:00:00+08:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T09:00:00+08:00"}；本例参数：start='2026-11-02T09:00:00+08:00'；end='2026-11-02T09:00:00+08:00'；参数：{"start": "'2026-11-02T09:00:00+08:00'", "end": "'2026-11-02T09:00:00+08:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.191s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": "Value error, 开始时间必须早于结束时间"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_003_invalid_times_are_rejected[2026-11-02T09:00:00+08:00-2026-11-02T09:00:00+08:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-011 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T09:00:00'；end='2026-11-02T10:00:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-011；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-003 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝（start='2026-11-02T09:00:00'；end='2026-11-02T10:00:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00", "end_time": "2026-11-02T10:00:00"}；本例参数：start='2026-11-02T09:00:00'；end='2026-11-02T10:00:00'；参数：{"start": "'2026-11-02T09:00:00'", "end": "'2026-11-02T10:00:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.186s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": [{"type": "value_error", "loc": ["body", "start_time"], "msg": "Value error, 预约时间必须包含时区", "input": "2026-11-02T09:00:00", "ctx": {"error": {}}}, {"type": "value_error", "loc": ["body", "end_time"], "msg": "Value error, 预约时间必须包含时… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:206](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_003_invalid_times_are_rejected[2026-11-02T09:00:00-2026-11-02T10:00:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-012 短于 30 分钟的合法时段不应被时长规则拒绝

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-012；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-003 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 短于 30 分钟的合法时段不应被时长规则拒绝；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T09:10:00+08:00"} |
| 预期结果 | reserve(client, actors.a, seats.a, body=short).status_code == 201 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.203s。 实采HTTP 3次，状态分布{"200": 2, "201": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261102050000588FB9", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T09:10:00+08:00", "status": "RESERVE… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:214](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_003_short_but_valid_interval_is_allowed`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-013 临时离开超时只释放一次，并至多生成一条违规和一条通知

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-013；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08；原标记TC-LOCAL-004 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 临时离开超时只释放一次，并至多生成一条违规和一条通知；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/check-in；POST /api/reservations/1/temporary-leave |
| 预期结果 | client.post(f'/api/reservations/{rid}/check-in', headers=actors.a).status_code == 200；left.status_code == 200；first['temp_leave'] == 1；second['temp_leave'] == 0；saved.status == E.ReservationStatus.TIMED_OUT；[row.violation_type for row in violations] == [E.ViolationType.TEMP_LEAVE_TIMEOUT]；notice is not None |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.246s。 实采HTTP 5次，状态分布{"200": 4, "201": 1}。POST /api/reservations/1/check-in → 200 {"id": 1, "reservation_no": "SR20261102080000EBD723", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "ACTIVE"… POST /api/reservations/1/temporary-leave → 200 {"id": 1, "reservation_no": "SR20261102080000EBD723", "user_id": 1, "room_id": 1, "seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "TEMP_LEAVE", "created_at": "2026-11-26T19:18:57.… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:222](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_004_temp_leave_timeout_releases_once_with_one_violation`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-014 开始前 15 分钟边界内取消记违规，边界外为正常取消（minutes=16；late=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-014；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08；原标记TC-LOCAL-005 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 开始前 15 分钟边界内取消记违规，边界外为正常取消（minutes=16；late=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db, minutes, late |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/cancel；本例参数：minutes=16；late=False；参数：{"minutes": "16", "late": "False"} |
| 预期结果 | response.status_code == 200；response.json()['cancel_type'] == ('late' if late else 'normal')；len(rows) == int(late)；s.get(Seat, seats.a).status == E.SeatStatus.AVAILABLE；rows[0].violation_type == E.ViolationType.LATE_CANCEL |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.390s。 实采HTTP 4次，状态分布{"200": 3, "201": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR202611020800005B5D40", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR202611020800005B5D40", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:253](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_005_cancel_boundary_records_late_violation[16-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-015 开始前 15 分钟边界内取消记违规，边界外为正常取消（minutes=15；late=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-015；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08；原标记TC-LOCAL-005 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 开始前 15 分钟边界内取消记违规，边界外为正常取消（minutes=15；late=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db, minutes, late |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/cancel；本例参数：minutes=15；late=True；参数：{"minutes": "15", "late": "True"} |
| 预期结果 | response.status_code == 200；response.json()['cancel_type'] == ('late' if late else 'normal')；len(rows) == int(late)；s.get(Seat, seats.a).status == E.SeatStatus.AVAILABLE；rows[0].violation_type == E.ViolationType.LATE_CANCEL |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.221s。 实采HTTP 4次，状态分布{"200": 3, "201": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR2026110208000038A7F3", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR2026110208000038A7F3", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:253](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_005_cancel_boundary_records_late_violation[15-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-016 开始前 15 分钟边界内取消记违规，边界外为正常取消（minutes=1；late=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-016；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08；原标记TC-LOCAL-005 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 开始前 15 分钟边界内取消记违规，边界外为正常取消（minutes=1；late=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db, minutes, late |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/cancel；本例参数：minutes=1；late=True；参数：{"minutes": "1", "late": "True"} |
| 预期结果 | response.status_code == 200；response.json()['cancel_type'] == ('late' if late else 'normal')；len(rows) == int(late)；s.get(Seat, seats.a).status == E.SeatStatus.AVAILABLE；rows[0].violation_type == E.ViolationType.LATE_CANCEL |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.238s。 实采HTTP 4次，状态分布{"200": 3, "201": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261102080000FAB797", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR20261102080000FAB797", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:253](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_005_cancel_boundary_records_late_violation[1-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-017 被禁约用户仍可取消已有预约，但不能新建或改座

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-017；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-005 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 被禁约用户仍可取消已有预约，但不能新建或改座；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；PATCH /api/reservations/1/seat，JSON={"seat_id": 2}；POST /api/reservations/1/cancel；POST /api/reservations，JSON={"seat_id": 2, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"} |
| 预期结果 | changed.status_code == 403；client.post(f'/api/reservations/{rid}/cancel', headers=actors.a).status_code == 200；reserve(client, actors.a, seats.b).status_code == 403 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.231s。 实采HTTP 6次，状态分布{"200": 3, "201": 1, "403": 2}。POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR202611020800007E6458", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… POST /api/reservations → 403 {"detail": "当前处于禁约期，解除时间：2026-11-03T08:00:00+08:00"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:271](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_005_restricted_user_may_cancel_but_not_book`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-018 申诉只能关联本人，并受期限限制

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-018；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08；原标记TC-LOCAL-005 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 申诉只能关联本人，并受期限限制；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, api_db, clock |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/appeals，JSON={"violation_id": 1, "reason": "不是我的记录"}；POST /api/appeals，JSON={"violation_id": 2, "reason": "已经超过七天"}；POST /api/appeals，JSON={"violation_id": 1, "reason": "门禁设备异常导致签到失败"} |
| 预期结果 | foreign.status_code == 404；expired.status_code == 409；own.status_code == 201 |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.203s。 实采HTTP 5次，状态分布{"200": 2, "404": 1, "409": 1, "201": 1}。POST /api/appeals → 409 {"detail": "该违规已超过申诉期限"} POST /api/appeals → 201 {"id": 1, "user_id": 1, "violation_id": 1, "reason": "门禁设备异常导致签到失败", "evidence": null, "deadline": "2026-11-09T08:00:00+08:00", "reviewer_id": null, "result": null, "reviewed_at": null, "review_comment": null} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:297](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_005_appeal_is_owner_only_and_within_deadline`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-019 审核通过时解除禁约，并在同一流程里通知申请人

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-019；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08；原标记TC-LOCAL-005 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 审核通过时解除禁约，并在同一流程里通知申请人；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, admin, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/appeals，JSON={"violation_id": 3, "reason": "门禁设备异常导致签到失败"}；PATCH /api/admin/appeals/1，JSON={"result": "approved", "review_comment": "核验后确认设备异常"} |
| 预期结果 | submitted.status_code == 201；reviewed.status_code == 200；restriction.status == E.RestrictionStatus.LIFTED；notice is not None；'已通过' in notice.content |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.227s。 实采HTTP 5次，状态分布{"200": 4, "201": 1}。POST /api/appeals → 201 {"id": 1, "user_id": 1, "violation_id": 3, "reason": "门禁设备异常导致签到失败", "evidence": null, "deadline": "2026-12-03T19:20:58.819399+08:00", "reviewer_id": null, "result": null, "reviewed_at": null, "review_comment": null} PATCH /api/admin/appeals/1 → 200 {"id": 1, "user_id": 1, "violation_id": 3, "reason": "门禁设备异常导致签到失败", "evidence": null, "deadline": "2026-12-03T19:20:58.819399+08:00", "reviewer_id": 3, "result": "approved", "reviewed_at": "2026-11-26T19:18:58.872802+08:00", "review_comme… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:339](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_005_approved_appeal_lifts_restriction_and_notifies`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-020 座位进入维护后取消尚未开始的预约；正在使用的预约不被中断

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-020；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08；原标记TC-LOCAL-006 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 座位进入维护后取消尚未开始的预约；正在使用的预约不被中断；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, admin, api_db, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 2, "start_time": "2026-11-02T12:00:00+08:00", "end_time": "2026-11-02T13:00:00+08:00"}；POST /api/reservations/1/check-in；PATCH /api/admin/rooms/1/seats/1/status，JSON={"status": "maintenance", "reason": "设备检修"}；PATCH /api/admin/rooms/1/seats/2/status，JSON={"status": "maintenance", "reason": "设备检修"} |
| 预期结果 | client.post(f'/api/reservations/{active_id}/check-in', headers=actors.a).status_code == 200；active.status == E.ReservationStatus.ACTIVE；pending.status == E.ReservationStatus.ADMIN_CANCELLED；notice is not None；'不提供补偿' in notice.content；{row.target_id for row in audits} == {str(seats.a), str(seats.b)}；response.status_code == 200 |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.266s。 实采HTTP 8次，状态分布{"200": 6, "201": 2}。PATCH /api/admin/rooms/1/seats/1/status → 200 {"code": "A01", "zone_type": "quiet", "has_power": true, "by_window": false, "accessible": false, "status": "maintenance", "id": 1, "room_id": 1, "cancelled_reservations": 0} PATCH /api/admin/rooms/1/seats/2/status → 200 {"code": "A02", "zone_type": "discussion", "has_power": false, "by_window": false, "accessible": false, "status": "maintenance", "id": 2, "room_id": 1, "cancelled_reservations": 1} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:381](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_006_maintenance_cancels_pending_but_not_active`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-021 只有授权角色可管理；非法开放时间或参数不改变已保存值

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-021；SRS FR-001～007、NFR-005/011；权限矩阵；原标记TC-LOCAL-007 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 只有授权角色可管理；非法开放时间或参数不改变已保存值；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, admin |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/admin/settings；GET /api/admin/settings；PUT /api/admin/settings，JSON={"advance_booking_days": 1, "max_active_reservations": 1, "checkin_open_before_minutes": 15, "no_show_after_minutes": 15, "late_cancel_minutes": 15, "temp_leave_minutes": 0, "missed_checkout_merge": 2, "violation_window_days": 14, "penalty_base_threshold": 3,…；GET /api/admin/settings；POST /api/admin/rooms，JSON={"name": "配置自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "05:30", "close_time": "22:00"}；GET /api/admin/rooms/1/schedules；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "08:00", "close_time": "22:00"} |
| 预期结果 | client.get('/api/admin/settings', headers=actors.a).status_code == 403；rejected.status_code == 422；client.get('/api/admin/settings', headers=admin).json() == before；room.status_code == 201；bad.status_code == 422；client.get(url, headers=admin).json() == []；ok.status_code == 201 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.240s。 实采HTTP 11次，状态分布{"200": 6, "403": 1, "422": 2, "201": 2}。GET /api/admin/rooms/1/schedules → 200 [] POST /api/admin/rooms/1/schedules → 201 {"day_type": "weekday", "open_time": "08:00:00", "close_time": "22:00:00", "effective_from": null, "effective_to": null, "enabled": true, "id": 1, "room_id": 1} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:422](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_007_only_admin_can_change_config_and_invalid_input_is_noop`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-022 JSON 与 XLSX 使用一致的统计区间和口径；日期倒置或超范围拒绝

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-022；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08；原标记TC-LOCAL-008 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | JSON 与 XLSX 使用一致的统计区间和口径；日期倒置或超范围拒绝；现有断言通过不等于全部业务需求验收。 只证明当前统计实现及导出对应，不证明历史真实现场利用率。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "报表自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekend", "open_time": "06:00", "close_time": "23:00"}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/seats，JSON={"code": "A02", "zone_type": "quiet", "status": "maintenance"}；GET /api/admin/reports；GET /api/admin/reports/export.xlsx；GET /api/admin/reports；GET /api/admin/reports |
| 预期结果 | room.status_code == 201；schedule.status_code == 201；seat.status_code == 201；closed.status_code == 201；report.status_code == 200；body['utilization']['available_hours'] == 17.0；exported.status_code == 200；rows['开始日期'] == body['period']['start']；rows['结束日期'] == body['period']['end']；rows['可用时长（座位小时）'] == body['utilization']['available_hours']；rows['利用率'] == body['utilization']['rate']；inverted.status_code == 422；too_long.status_code == 422 |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.470s。 实采HTTP 9次，状态分布{"200": 3, "201": 4, "422": 2}。GET /api/admin/reports → 422 {"detail": "开始日期不能晚于结束日期"} GET /api/admin/reports → 422 {"detail": "报告时间范围最多为一年"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:457](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_008_report_json_and_xlsx_share_the_same_scope`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-023 只有运维角色可以创建和查看备份

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-023；SRS NFR-008/012；ADR-09；原标记TC-LOCAL-009 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 只有运维角色可以创建和查看备份；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login, tmp_path, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/ops/backups；POST /api/ops/backups；POST /api/ops/backups；GET /api/ops/backups；GET /api/ops/backups |
| 预期结果 | client.post('/api/ops/backups', headers=student).status_code == 403；client.post('/api/ops/backups', headers=admin).status_code == 403；created.status_code == 201；client.get('/api/ops/backups', headers=student).status_code == 403；names == [created.json()['name']] |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.210s。 实采HTTP 8次，状态分布{"200": 4, "403": 3, "201": 1}。GET /api/ops/backups → 403 {"detail": "无权限执行此操作"} GET /api/ops/backups → 200 [{"name": "study_room-20261126-191900-043921.db", "size_bytes": 229376, "created_at": 1795691940.0505078}] |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:517](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_009_backup_requires_ops_role`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-024 备份轮换后仍可完整性恢复；监控接口只返回定义字段

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-024；SRS NFR-008/012；ADR-09；原标记TC-LOCAL-009 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 备份轮换后仍可完整性恢复；监控接口只返回定义字段；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, api_db, make_user, login, tmp_path, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/ops/status |
| 预期结果 | first not in list_backups()；latest in list_backups()；status.status_code == 200；set(status.json()) == {'uptime_seconds', 'database', 'users', 'active_sessions', 'latest_backup', 'requests'}；s.scalar(select(func.count()).select_from(User)) == 2 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.205s。 实采HTTP 2次，状态分布{"200": 2}。GET /api/ops/status → 200 {"uptime_seconds": 6, "database": {"size_bytes": 4096, "wal_bytes": 745752}, "users": 3, "active_sessions": 1, "latest_backup": {"name": "study_room-20261126-191900-200219.db", "size_bytes": 229376, "created_at": 1795691940.2028766}, "requ… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:538](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_009_backup_rotation_restore_and_status`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-025 同一外部事件重放不重复入账

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-025；SRS HD-15/16/30/31/52、NFR-013/014；ADR-06；原标记TC-LOCAL-010 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 同一外部事件重放不重复入账；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, api_db, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"} |
| 预期结果 | first['duplicate'] is False；duplicate['duplicate'] is True；len(records) == 1 |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.220s。 实采HTTP 3次，状态分布{"200": 2, "201": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR202611020800002BF8D9", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:587](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_010_duplicate_gate_event_is_not_counted_twice`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-026 延迟事件和已结束预约上的事件只关联记录，不复活或结束预约

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-026；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10；原标记TC-LOCAL-010 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 延迟事件和已结束预约上的事件只关联记录，不复活或结束预约；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, api_db, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"} |
| 预期结果 | late['sync_status'] == 'late'；late['manual_appeal_required'] is True；saved.status == E.ReservationStatus.RESERVED；unmatched['sync_status'] == 'unmatched'；unmatched['manual_appeal_required'] is True；saved.status == E.ReservationStatus.COMPLETED |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.302s。 实采HTTP 3次，状态分布{"200": 2, "201": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR2026110208000018F425", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:618](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_010_delayed_and_unmatched_events_need_manual_review`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-027 超过临时离开期限后的入馆事件不恢复使用中状态

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-027；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08；原标记TC-LOCAL-010 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 超过临时离开期限后的入馆事件不恢复使用中状态；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, api_db, clock, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/check-in；POST /api/reservations/1/temporary-leave |
| 预期结果 | client.post(f'/api/reservations/{rid}/check-in', headers=actors.a).status_code == 200；client.post(f'/api/reservations/{rid}/temporary-leave', headers=actors.a).status_code == 200；result['sync_status'] == 'unmatched'；saved.status == E.ReservationStatus.TEMP_LEAVE |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.644s。 实采HTTP 5次，状态分布{"200": 4, "201": 1}。POST /api/reservations/1/check-in → 200 {"id": 1, "reservation_no": "SR20261102080000ECCF23", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "ACTIVE"… POST /api/reservations/1/temporary-leave → 200 {"id": 1, "reservation_no": "SR20261102080000ECCF23", "user_id": 1, "room_id": 1, "seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "TEMP_LEAVE", "created_at": "2026-11-26T19:19:01.… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_acceptance_cases.py:657](../backend/tests/test_acceptance_cases.py)；`tests/test_acceptance_cases.py::test_case_010_entry_after_temp_leave_window_is_not_applied`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-028 非管理员无法管理资源配置

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-028；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 非管理员无法管理资源配置；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "图书馆 301", "location": "图书馆三楼", "capacity": 80, "facilities": "插座"}；GET /api/admin/settings；POST /api/admin/rooms，JSON={"name": "图书馆 301", "location": "图书馆三楼", "capacity": 80, "facilities": "插座"}；GET /api/admin/settings |
| 预期结果 | client.post('/api/admin/rooms', headers=h, json=ROOM).status_code == 403；client.get('/api/admin/settings', headers=h).status_code == 403 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.190s。 实采HTTP 6次，状态分布{"200": 2, "403": 4}。POST /api/admin/rooms → 403 {"detail": "无权限执行此操作"} GET /api/admin/settings → 403 {"detail": "无权限执行此操作"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_admin_config.py:27](../backend/tests/test_admin_config.py)；`tests/test_admin_config.py::test_non_admin_forbidden`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-029 房间创建编辑关闭与删除

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-029；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 房间创建编辑关闭与删除；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "图书馆 301", "location": "图书馆三楼", "capacity": 80, "facilities": "插座"}；POST /api/admin/rooms，JSON={"name": "图书馆 301", "location": "图书馆三楼", "capacity": 80, "facilities": "插座"}；PUT /api/admin/rooms/1，JSON={"name": "图书馆 301", "location": "图书馆三楼", "capacity": 60, "facilities": "插座"}；PATCH /api/admin/rooms/1/status，JSON={"status": "closed"}；GET /api/admin/rooms；DELETE /api/admin/rooms/1；DELETE /api/admin/rooms/1 |
| 预期结果 | r.status_code == 201 and r.json()['status'] == 'open'；client.post('/api/admin/rooms', headers=admin, json=ROOM).status_code == 409；r.json()['capacity'] == 60；r.json()['status'] == 'closed'；[x['id'] for x in client.get('/api/admin/rooms', headers=admin).json()] == [rid]；client.delete(f'/api/admin/rooms/{rid}', headers=admin).status_code == 204；client.delete(f'/api/admin/rooms/{rid}', headers=admin).status_code == 404；len(logs) == 3 and all((log.op_type == 'admin_action' for log in logs))；json.loads(logs[1].before_value)['capacity'] == 80；json.loads(logs[1].after_value)['capacity'] == 60；len(_logs(api_db, 'study_room_status')) == 1 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.273s。 实采HTTP 8次，状态分布{"200": 4, "201": 1, "409": 1, "204": 1, "404": 1}。DELETE /api/admin/rooms/1 → 204 {"bytes": 0} DELETE /api/admin/rooms/1 → 404 {"detail": "自习室不存在"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_admin_config.py:36](../backend/tests/test_admin_config.py)；`tests/test_admin_config.py::test_room_crud_and_close`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-030 含座位房间不得直接删除

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-030；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 含座位房间不得直接删除；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "图书馆 301", "location": "图书馆三楼", "capacity": 80, "facilities": "插座"}；DELETE /api/admin/rooms/1 |
| 预期结果 | r.status_code == 409 and '关闭' in r.json()['detail'] |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.191s。 实采HTTP 3次，状态分布{"200": 1, "201": 1, "409": 1}。POST /api/admin/rooms → 201 {"name": "图书馆 301", "location": "图书馆三楼", "floor": null, "capacity": 80, "facilities": "插座", "remark": null, "id": 1, "status": "open"} DELETE /api/admin/rooms/1 → 409 {"detail": "该自习室已有座位或预约记录，请改为关闭"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_admin_config.py:57](../backend/tests/test_admin_config.py)；`tests/test_admin_config.py::test_room_with_seats_cannot_be_deleted`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-031 开放时段增删改及边界校验

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-031；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 开放时段增删改及边界校验；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "图书馆 301", "location": "图书馆三楼", "capacity": 80, "facilities": "插座"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "08:00", "close_time": "22:00"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "05:30", "close_time": "22:00"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "08:00", "close_time": "23:45"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "08:00", "close_time": "07:00"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "holiday", "open_time": "08:00", "close_time": "22:00", "effective_from": "2026-10-01", "effective_to": "2026-10-07"}；PUT /api/admin/rooms/1/schedules/1，JSON={"day_type": "weekday", "open_time": "08:00", "close_time": "23:00"}；GET /api/admin/rooms/1/schedules；其余2步请求见本例原始证据。 |
| 预期结果 | r.status_code == 201；client.post(url, headers=admin, json={**ok, 'open_time': '05:30'}).status_code == 422；client.post(url, headers=admin, json={**ok, 'close_time': '23:45'}).status_code == 422；client.post(url, headers=admin, json={**ok, 'close_time': '07:00'}).status_code == 422；client.post(url, headers=admin, json=holiday).status_code == 201；r.json()['close_time'] == '23:00:00'；len(client.get(url, headers=admin).json()) == 2；client.delete(f'{url}/{sid}', headers=admin).status_code == 204；client.put(f'{url}/{sid}', headers=admin, json=ok).status_code == 404；len(_logs(api_db, 'opening_schedule')) == 4 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.241s。 实采HTTP 11次，状态分布{"200": 3, "201": 3, "422": 3, "204": 1, "404": 1}。DELETE /api/admin/rooms/1/schedules/1 → 204 {"bytes": 0} PUT /api/admin/rooms/1/schedules/1 → 404 {"detail": "开放时段不存在"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_admin_config.py:66](../backend/tests/test_admin_config.py)；`tests/test_admin_config.py::test_opening_schedules`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-032 特殊日期校历维护与校验

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-032；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 特殊日期校历维护与校验；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：PUT /api/admin/calendar/2026-10-01，JSON={"day": "2026-10-01", "day_type": "holiday", "note": "国庆"}；PUT /api/admin/calendar/2026-10-01，JSON={"day": "2026-10-01", "day_type": "weekday", "note": "国庆"}；GET /api/admin/calendar；DELETE /api/admin/calendar/2026-10-01 |
| 预期结果 | client.put('/api/admin/calendar/2026-10-01', headers=admin, json=body).status_code == 200；client.put('/api/admin/calendar/2026-10-01', headers=admin, json=body2).status_code == 422；client.get('/api/admin/calendar', headers=admin).json()[0]['note'] == '国庆'；client.delete('/api/admin/calendar/2026-10-01', headers=admin).status_code == 204 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.176s。 实采HTTP 5次，状态分布{"200": 3, "422": 1, "204": 1}。GET /api/admin/calendar → 200 [{"day": "2026-10-01", "day_type": "holiday", "note": "国庆"}] DELETE /api/admin/calendar/2026-10-01 → 204 {"bytes": 0} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_admin_config.py:94](../backend/tests/test_admin_config.py)；`tests/test_admin_config.py::test_calendar_days`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-033 业务参数保存与非法值拒绝

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-033；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 业务参数保存与非法值拒绝；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/admin/settings；PUT /api/admin/settings，JSON={"advance_booking_days": 1, "max_active_reservations": 1, "checkin_open_before_minutes": 15, "no_show_after_minutes": 20, "late_cancel_minutes": 15, "temp_leave_minutes": 30, "missed_checkout_merge": 2, "violation_window_days": 14, "penalty_base_threshold": 3…；GET /api/admin/settings；PUT /api/admin/settings，JSON={"advance_booking_days": 1, "max_active_reservations": 1, "checkin_open_before_minutes": 15, "no_show_after_minutes": 20, "late_cancel_minutes": 15, "temp_leave_minutes": 0, "missed_checkout_merge": 2, "violation_window_days": 14, "penalty_base_threshold": 3,…；PUT /api/admin/settings，JSON={"advance_booking_days": 1, "max_active_reservations": 1, "checkin_open_before_minutes": 15, "no_show_after_minutes": 20, "late_cancel_minutes": 15, "temp_leave_minutes": 30, "missed_checkout_merge": 2, "violation_window_days": 14, "penalty_base_threshold": 3…；PUT /api/admin/settings，JSON={"advance_booking_days": 1, "max_active_reservations": 1, "checkin_open_before_minutes": 15, "no_show_after_minutes": 20, "late_cancel_minutes": 15, "temp_leave_minutes": 30, "missed_checkout_merge": 2, "violation_window_days": 14, "penalty_base_threshold": 3…；POST /api/admin/rooms，JSON={"name": "图书馆 301", "location": "图书馆三楼", "capacity": 80, "facilities": "插座"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:30", "close_time": "22:00"} |
| 预期结果 | s['no_show_after_minutes'] == 15 and s['penalty_base_threshold'] == 3；s['opening_earliest'] == '06:00:00'；r.status_code == 200 and r.json()['no_show_after_minutes'] == 20；client.get('/api/admin/settings', headers=admin).json()['no_show_after_minutes'] == 20；client.put('/api/admin/settings', headers=admin, json={**s, 'temp_leave_minutes': 0}).status_code == 422；client.put('/api/admin/settings', headers=admin, json={**s, 'unknown': 1}).status_code == 422；json.loads(log.before_value) == {'no_show_after_minutes': 15}；json.loads(log.after_value) == {'no_show_after_minutes': 20}；r.status_code == 422 and '07:00' in r.json()['detail'] |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.391s。 实采HTTP 9次，状态分布{"200": 5, "422": 3, "201": 1}。POST /api/admin/rooms → 201 {"name": "图书馆 301", "location": "图书馆三楼", "floor": null, "capacity": 80, "facilities": "插座", "remark": null, "id": 1, "status": "open"} POST /api/admin/rooms/1/schedules → 422 {"detail": "开放时段须在 07:00–23:30 之间"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_admin_config.py:105](../backend/tests/test_admin_config.py)；`tests/test_admin_config.py::test_business_settings`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-034 验证预约请求幂等、本人数据隔离以及同一用户的有效预约上限

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-034；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 验证预约请求幂等、本人数据隔离以及同一用户的有效预约上限；现有断言通过不等于全部业务需求验收。 所谓user_limit实际覆盖重叠时段单座，不能证明独立日次数额度。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:00", "close_time": "23:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "request_key": "request-key-001"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "request_key": "request-key-001"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"}；POST /api/admin/rooms/1/seats，JSON={"code": "A02", "zone_type": "quiet", "status": "available"}；POST /api/reservations，JSON={"seat_id": 2, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"}；其余1步请求见本例原始证据。 |
| 预期结果 | retry.status_code == 201；retry.json()['id'] == first['id']；conflict.status_code == 409；new_seat.status_code == 201；too_many.status_code == 409；all((row['user_id'] != first['user_id'] for row in hidden.json())) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.273s。 实采HTTP 12次，状态分布{"200": 4, "201": 6, "409": 2}。POST /api/reservations → 409 {"detail": "你在该时段已有有效预约"} GET /api/reservations → 200 [] |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:80](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_reservation_idempotency_ownership_and_user_limit`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-035 验证临时离开超过 30 分钟后释放预约，且重复扫描不会重复处罚

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-035；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 验证临时离开超过 30 分钟后释放预约，且重复扫描不会重复处罚；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login, api_db, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:00", "close_time": "23:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"}；POST /api/reservations/1/check-in；POST /api/reservations/1/temporary-leave |
| 预期结果 | check_in.status_code == 200；leave.status_code == 200；leave.json()['status'] == E.ReservationStatus.TEMP_LEAVE.value；first_scan['temp_leave'] == 1；second_scan['temp_leave'] == 0；saved.status == E.ReservationStatus.TIMED_OUT；len(violations) == 1 |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.273s。 实采HTTP 8次，状态分布{"200": 4, "201": 4}。POST /api/reservations/1/check-in → 200 {"id": 1, "reservation_no": "SR20261126191903F615F4", "user_id": 2, "room_id": 1, "room_name": "流程验收自习室", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "ACTI… POST /api/reservations/1/temporary-leave → 200 {"id": 1, "reservation_no": "SR20261126191903F615F4", "user_id": 2, "room_id": 1, "seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "TEMP_LEAVE", "created_at": "2026-11-26T19:19:03.… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:139](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_temporary_leave_timeout_creates_one_violation`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-036 验证预约开始前 15 分钟内取消时生成违规和站内结果通知

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-036；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 验证预约开始前 15 分钟内取消时生成违规和站内结果通知；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login, api_db, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:00", "close_time": "23:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"}；POST /api/reservations/1/cancel |
| 预期结果 | response.status_code == 200；saved.status == E.ReservationStatus.CANCELLED；saved.cancel_type == E.CancelType.LATE；violation.violation_type == E.ViolationType.LATE_CANCEL；notice is not None |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.254s。 实采HTTP 7次，状态分布{"200": 3, "201": 4}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR2026112619190399D0FE", "user_id": 2, "room_id": 1, "room_name": "流程验收自习室", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "RESE… POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR2026112619190399D0FE", "user_id": 2, "room_id": 1, "room_name": "流程验收自习室", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "CANC… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:170](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_late_cancellation_records_violation_and_notice`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-037 验证门禁迟到回调关联预约、提醒本人并保持预约状态不变

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-037；SRS HD-15/16/30/31/52、NFR-013/014；ADR-06 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 验证门禁迟到回调关联预约、提醒本人并保持预约状态不变；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login, api_db, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:00", "close_time": "23:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"} |
| 预期结果 | result['sync_status'] == 'late'；result['reservation_id'] == reservation_data['id']；result['manual_appeal_required'] is True；duplicate['duplicate'] is True；saved_reservation.status == E.ReservationStatus.RESERVED；gate_record.reservation_id == reservation_data['id']；len(notices) == 1 |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.240s。 实采HTTP 6次，状态分布{"200": 2, "201": 4}。POST /api/admin/rooms/1/schedules → 201 {"day_type": "weekday", "open_time": "06:00:00", "close_time": "23:00:00", "effective_from": null, "effective_to": null, "enabled": true, "id": 1, "room_id": 1} POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261126191903610724", "user_id": 2, "room_id": 1, "room_name": "流程验收自习室", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "RESE… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:199](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_late_gate_event_is_linked_not_applied_and_notifies_user`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-038 验证状态不匹配的门禁入馆事件进入人工处理而不复活已完成预约

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-038；SRS HD-15/16/30/31/52、NFR-013/014；ADR-06 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 验证状态不匹配的门禁入馆事件进入人工处理而不复活已完成预约；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login, api_db, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:00", "close_time": "23:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"} |
| 预期结果 | result['sync_status'] == 'unmatched'；result['manual_appeal_required'] is True；reservation.status == E.ReservationStatus.COMPLETED；record.reservation_id == reservation.id |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.233s。 实采HTTP 6次，状态分布{"200": 2, "201": 4}。POST /api/admin/rooms/1/schedules → 201 {"day_type": "weekday", "open_time": "06:00:00", "close_time": "23:00:00", "effective_from": null, "effective_to": null, "enabled": true, "id": 1, "room_id": 1} POST /api/reservations → 201 {"id": 1, "reservation_no": "SR2026112619190426849B", "user_id": 2, "room_id": 1, "room_name": "流程验收自习室", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "RESE… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:243](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_gate_entry_cannot_reactivate_completed_reservation`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-039 验证管理员批准申诉后解除有效禁约并向申请人发送站内通知

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-039；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 验证管理员批准申诉后解除有效禁约并向申请人发送站内通知；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/appeals，JSON={"violation_id": 3, "reason": "门禁设备异常导致签到失败"}；PATCH /api/admin/appeals/1，JSON={"result": "approved", "review_comment": "核验后确认设备异常"} |
| 预期结果 | submitted.status_code == 201；reviewed.status_code == 200；appeal.result == E.AppealResult.APPROVED；violation.state == E.ViolationState.ARCHIVED；restriction.status == E.RestrictionStatus.LIFTED；notice is not None；'已通过' in notice.content |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.210s。 实采HTTP 4次，状态分布{"200": 3, "201": 1}。POST /api/appeals → 201 {"id": 1, "user_id": 2, "violation_id": 3, "reason": "门禁设备异常导致签到失败", "evidence": null, "deadline": "2026-12-03T19:21:04.330827+08:00", "reviewer_id": null, "result": null, "reviewed_at": null, "review_comment": null} PATCH /api/admin/appeals/1 → 200 {"id": 1, "user_id": 2, "violation_id": 3, "reason": "门禁设备异常导致签到失败", "evidence": null, "deadline": "2026-12-03T19:21:04.330827+08:00", "reviewer_id": 1, "result": "approved", "reviewed_at": "2026-11-26T19:19:04.388150+08:00", "review_comme… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:277](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_approved_appeal_lifts_restriction_and_notifies_user`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-040 验证座位置为维护时会取消未开始预约并向预约人发送站内通知

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-040；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 验证座位置为维护时会取消未开始预约并向预约人发送站内通知；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:00", "close_time": "23:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"}；PATCH /api/admin/rooms/1/seats/1/status，JSON={"status": "maintenance", "reason": "设备检修"} |
| 预期结果 | response.status_code == 200；saved.status == E.ReservationStatus.ADMIN_CANCELLED；notice is not None；'不提供补偿' in notice.content |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.232s。 实采HTTP 7次，状态分布{"200": 3, "201": 4}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261126191904ACDBE0", "user_id": 2, "room_id": 1, "room_name": "流程验收自习室", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "RESE… PATCH /api/admin/rooms/1/seats/1/status → 200 {"code": "A01", "zone_type": "quiet", "has_power": false, "by_window": false, "accessible": false, "status": "maintenance", "id": 1, "room_id": 1, "cancelled_reservations": 1} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:332](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_maintenance_cancels_pending_reservation_and_notifies`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-041 验证完整座位编辑接口改为维护状态时执行相同的预约取消规则

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-041；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 验证完整座位编辑接口改为维护状态时执行相同的预约取消规则；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:00", "close_time": "23:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"}；PUT /api/admin/rooms/1/seats/1，JSON={"code": "A01", "zone_type": "quiet", "has_power": false, "by_window": false, "accessible": false, "status": "maintenance"} |
| 预期结果 | response.status_code == 200；saved.status == E.ReservationStatus.ADMIN_CANCELLED |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.500s。 实采HTTP 7次，状态分布{"200": 3, "201": 4}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR202611261919052C43BD", "user_id": 2, "room_id": 1, "room_name": "流程验收自习室", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "RESE… PUT /api/admin/rooms/1/seats/1 → 200 {"code": "A01", "zone_type": "quiet", "has_power": false, "by_window": false, "accessible": false, "status": "maintenance", "id": 1, "room_id": 1} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:360](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_full_seat_update_to_maintenance_also_cancels_bookings`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-042 验证管理员报表按开放座位计算计划时长并生成 Excel 文件

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-042；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 验证管理员报表按开放座位计算计划时长并生成 Excel 文件；现有断言通过不等于全部业务需求验收。 只证明当前统计实现及导出对应，不证明历史真实现场利用率。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekend", "open_time": "06:00", "close_time": "23:00"}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；GET /api/admin/reports；GET /api/admin/reports/export.xlsx |
| 预期结果 | schedule.status_code == 201；seat.status_code == 201；report.status_code == 200；report.json()['utilization']['available_hours'] == 17.0；exported.status_code == 200；exported.headers['content-type'].startswith('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.232s。 实采HTTP 6次，状态分布{"200": 3, "201": 3}。GET /api/admin/reports → 200 {"period": {"start": "2026-11-28", "end": "2026-11-28"}, "definition": {"utilization": "已签到预约的预约时长 / 开放且非维护座位的计划开放时长", "peak": "按预约开始日期和小时统计预约数量", "violations": "按违规发生日期和类型统计系统记录条数"}, "utilization": {"booked_hours": 0, "available_hours": 1… GET /api/admin/reports/export.xlsx → 200 {"content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "bytes": 6584} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:386](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_report_endpoint_returns_supply_hours_and_excel`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-043 使用中未声明临时离开即出馆：超时结束并记录未声明离开违规

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-043；SRS HD-15/16/30/31/52、NFR-013/014；ADR-06 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 使用中未声明临时离开即出馆：超时结束并记录未声明离开违规；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login, api_db, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:00", "close_time": "23:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"} |
| 预期结果 | result['sync_status'] == 'synced'；reservation.status == E.ReservationStatus.TIMED_OUT；[v.violation_type for v in violations] == [E.ViolationType.LEFT_UNDECLARED] |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.246s。 实采HTTP 6次，状态分布{"200": 2, "201": 4}。POST /api/admin/rooms/1/schedules → 201 {"day_type": "weekday", "open_time": "06:00:00", "close_time": "23:00:00", "effective_from": null, "effective_to": null, "enabled": true, "id": 1, "room_id": 1} POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261126191905DBC3F1", "user_id": 2, "room_id": 1, "room_name": "流程验收自习室", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "RESE… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:430](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_gate_exit_while_active_without_leave_times_out_with_violation`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-044 临时离开期间出馆保留座位；30 分钟内入馆恢复使用中，且不产生违规

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-044；SRS HD-15/16/30/31/52、NFR-013/014；ADR-06 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 临时离开期间出馆保留座位；30 分钟内入馆恢复使用中，且不产生违规；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login, api_db, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:00", "close_time": "23:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"}；POST /api/reservations/1/check-in；POST /api/reservations/1/temporary-leave |
| 预期结果 | client.post(f"/api/reservations/{data['id']}/check-in", headers=headers).status_code == 200；client.post(f"/api/reservations/{data['id']}/temporary-leave", headers=headers).status_code == 200；back['sync_status'] == 'synced'；reservation.status == E.ReservationStatus.ACTIVE；reservation.temp_leave_state == E.TempLeaveState.RETURNED；violations == []；out['sync_status'] == 'synced'；reservation.status == E.ReservationStatus.TEMP_LEAVE；reservation.temp_leave_state == E.TempLeaveState.WAITING |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.259s。 实采HTTP 8次，状态分布{"200": 4, "201": 4}。POST /api/reservations/1/check-in → 200 {"id": 1, "reservation_no": "SR202611261919050B78E2", "user_id": 2, "room_id": 1, "room_name": "流程验收自习室", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "ACTI… POST /api/reservations/1/temporary-leave → 200 {"id": 1, "reservation_no": "SR202611261919050B78E2", "user_id": 2, "room_id": 1, "seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "TEMP_LEAVE", "created_at": "2026-11-26T19:19:05.… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:461](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_gate_exit_during_temp_leave_keeps_seat_and_entry_resumes`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-045 超过 30 分钟临时离开期限后的入馆事件不恢复座位，转入人工核验

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-045；SRS HD-15/16/30/31/52、NFR-013/014；ADR-06 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 超过 30 分钟临时离开期限后的入馆事件不恢复座位，转入人工核验；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login, api_db, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:00", "close_time": "23:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"}；POST /api/reservations/1/check-in；POST /api/reservations/1/temporary-leave |
| 预期结果 | result['sync_status'] == 'unmatched'；reservation.status == E.ReservationStatus.TEMP_LEAVE |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.333s。 实采HTTP 8次，状态分布{"200": 4, "201": 4}。POST /api/reservations/1/check-in → 200 {"id": 1, "reservation_no": "SR20261126191906053C2F", "user_id": 2, "room_id": 1, "room_name": "流程验收自习室", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "ACTI… POST /api/reservations/1/temporary-leave → 200 {"id": 1, "reservation_no": "SR20261126191906053C2F", "user_id": 2, "room_id": 1, "seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "TEMP_LEAVE", "created_at": "2026-11-26T19:19:06.… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:512](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_gate_entry_after_temp_leave_window_is_not_applied`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-046 已取消的未来预约只出现在历史列表，不出现在当前预约

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-046；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 已取消的未来预约只出现在历史列表，不出现在当前预约；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, admin_headers, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/admin/rooms，JSON={"name": "流程验收自习室", "location": "图书馆", "capacity": 20}；POST /api/admin/rooms/1/seats，JSON={"code": "A01", "zone_type": "quiet", "status": "available"}；POST /api/admin/rooms/1/schedules，JSON={"day_type": "weekday", "open_time": "06:00", "close_time": "23:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00"}；POST /api/reservations/1/cancel；GET /api/reservations?scope=current；GET /api/reservations?scope=history |
| 预期结果 | cancel.status_code == 200；data['id'] not in [row['id'] for row in current]；data['id'] in [row['id'] for row in history] |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.287s。 实采HTTP 9次，状态分布{"200": 5, "201": 4}。GET /api/reservations?scope=current → 200 [] GET /api/reservations?scope=history → 200 [{"id": 1, "reservation_no": "SR20261126191906EBA207", "user_id": 2, "room_id": 1, "seat_id": 1, "start_time": "2026-11-27T08:00:00+08:00", "end_time": "2026-11-27T09:00:00+08:00", "status": "CANCELLED", "created_at": "2026-11-26T19:19:06.… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:538](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_current_scope_excludes_cancelled_future_reservation`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-047 生产环境沿用默认门禁密钥时配置校验失败；dev/test 或自定义密钥可通过

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-047；SRS HD-15/16/30/31/52、NFR-013/014；ADR-06 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 生产环境沿用默认门禁密钥时配置校验失败；dev/test 或自定义密钥可通过；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：monkeypatch |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_default_gate_secret_rejected_outside_dev，进行异常、返回值或Mock调用核验。 |
| 预期结果 | Settings(env='test').env == 'test'；Settings(env='prod', gate_hmac_secret='x' * 32).env == 'prod'；pytest.raises(ValidationError) |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.003s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_assigned_workflows.py:553](../backend/tests/test_assigned_workflows.py)；`tests/test_assigned_workflows.py::test_default_gate_secret_rejected_outside_dev`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-048 注册登录与本人信息查询

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-048；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 注册登录与本人信息查询；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/auth/me |
| 预期结果 | r.status_code == 201；r.json()['roles'] == ['user']；'password' not in r.text；r.status_code == 200；me.json()['student_no'] == '20260001' |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.148s。 实采HTTP 3次，状态分布{"201": 1, "200": 2}。POST /api/auth/register → 201 {"id": 1, "student_no": "20260001", "name": "张三", "department": null, "contact": null, "status": "normal", "roles": ["user"], "permissions": ["reservation:own", "room:read"]} GET /api/auth/me → 200 {"id": 1, "student_no": "20260001", "name": "张三", "department": null, "contact": null, "status": "normal", "roles": ["user"], "permissions": ["reservation:own", "room:read"]} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_auth.py:18](../backend/tests/test_auth.py)；`tests/test_auth.py::test_register_then_login_and_me`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-049 数据库保存密码哈希

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-049；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 数据库保存密码哈希；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, api_db |
| 操作/输入 | 按源函数顺序执行：client.post('/api/auth/register', json=REG) |
| 预期结果 | h != 'secret123' and h.startswith('$2') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.144s。 实采HTTP 1次，状态分布{"201": 1}。POST /api/auth/register → 201 {"id": 1, "student_no": "20260001", "name": "张三", "department": null, "contact": null, "status": "normal", "roles": ["user"], "permissions": ["reservation:own", "room:read"]} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_auth.py:31](../backend/tests/test_auth.py)；`tests/test_auth.py::test_password_is_stored_hashed`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-050 拒绝重复学号及非法注册输入

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-050；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 拒绝重复学号及非法注册输入；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client |
| 操作/输入 | 按源函数顺序执行：client.post('/api/auth/register', json=REG)；client.post('/api/auth/register', json=REG)；client.post('/api/auth/register', json={**REG, 'student_no': 'a-b'})；client.post('/api/auth/register', json={**REG, 'student_no': '20260002', 'password': 'short1'})；client.post('/api/auth/register', json={**REG, 'student_no': '20260002', 'password': 'onlyletters'}) |
| 预期结果 | r.status_code == 409 and r.json()['detail']['message'] == '该学号已注册'；r.json()['detail']['code'] == 'invalid_student_no'；r.json()['detail']['code'] == 'weak_password'；r.status_code == 422 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.146s。 实采HTTP 5次，状态分布{"201": 1, "409": 1, "422": 3}。POST /api/auth/register → 422 {"detail": {"code": "weak_password", "message": "密码至少 8 位"}} POST /api/auth/register → 422 {"detail": {"code": "weak_password", "message": "密码须同时包含字母和数字"}} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_auth.py:38](../backend/tests/test_auth.py)；`tests/test_auth.py::test_register_rejects_duplicate_and_bad_input`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-051 登录失败与错误提示

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-051；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 登录失败与错误提示；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_login_failures_have_clear_messages，进行异常、返回值或Mock调用核验。 |
| 预期结果 | r.status_code == 401；r.json()['detail']['message'] == '学号或密码错误'；r.json()['detail']['code'] == 'invalid_credentials'；r.status_code == 401；r.json()['detail']['message'] == '学号或密码错误'；r.json()['detail']['code'] == 'invalid_credentials' |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.164s。 实采HTTP 2次，状态分布{"401": 2}。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_auth.py:55](../backend/tests/test_auth.py)；`tests/test_auth.py::test_login_failures_have_clear_messages`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-052 失败次数达到阈值时锁定登录

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-052；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 失败次数达到阈值时锁定登录；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, monkeypatch |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_login_lockout_after_failures，进行异常、返回值或Mock调用核验。 |
| 预期结果 | locked.status_code == 429；locked.json()['detail']['code'] == 'login_locked'；_login(client).status_code == 429；_login(client, password='wrong1234').status_code == 401 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.422s。 实采HTTP 5次，状态分布{"401": 3, "429": 2}。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_auth.py:68](../backend/tests/test_auth.py)；`tests/test_auth.py::test_login_lockout_after_failures`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-053 禁用账号不得登录

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-053；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 禁用账号不得登录；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_disabled_account_cannot_login，进行异常、返回值或Mock调用核验。 |
| 预期结果 | r.status_code == 403 and r.json()['detail']['code'] == 'account_disabled' |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.137s。 实采HTTP 1次，状态分布{"403": 1}。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_auth.py:84](../backend/tests/test_auth.py)；`tests/test_auth.py::test_disabled_account_cannot_login`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-054 注销撤销当前会话

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-054；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 注销撤销当前会话；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/auth/logout；GET /api/auth/me |
| 预期结果 | client.post('/api/auth/logout', headers=h).status_code == 204；client.get('/api/auth/me', headers=h).status_code == 401 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.157s。 实采HTTP 3次，状态分布{"200": 1, "204": 1, "401": 1}。POST /api/auth/logout → 204 {"bytes": 0} GET /api/auth/me → 401 {"detail": "登录已失效，请重新登录"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_auth.py:90](../backend/tests/test_auth.py)；`tests/test_auth.py::test_logout_revokes_token`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-055 未认证及过期会话被拒绝

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-055；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 未认证及过期会话被拒绝；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/auth/me；GET /api/auth/me |
| 预期结果 | client.get('/api/auth/me').status_code == 401；client.get('/api/auth/me', headers=h).status_code == 401 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.152s。 实采HTTP 3次，状态分布{"401": 2, "200": 1}。GET /api/auth/me → 401 {"detail": "请先登录"} GET /api/auth/me → 401 {"detail": "登录已失效，请重新登录"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_auth.py:97](../backend/tests/test_auth.py)；`tests/test_auth.py::test_unauthenticated_and_expired`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-056 改密校验旧密码并撤销会话

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-056；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 改密校验旧密码并撤销会话；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/auth/change-password，JSON={"old_password": "[redacted]", "new_password": "[redacted]"}；POST /api/auth/change-password，JSON={"old_password": "[redacted]", "new_password": "[redacted]"}；GET /api/auth/me |
| 预期结果 | r.status_code == 400；r.status_code == 204；client.get('/api/auth/me', headers=h).status_code == 401；_login(client).status_code == 401；_login(client, password='newpass123').status_code == 200 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.200s。 实采HTTP 6次，状态分布{"200": 2, "400": 1, "204": 1, "401": 2}。POST /api/auth/change-password → 204 {"bytes": 0} GET /api/auth/me → 401 {"detail": "登录已失效，请重新登录"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_auth.py:107](../backend/tests/test_auth.py)；`tests/test_auth.py::test_change_password`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-057 通过重置码修改密码

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-057；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 通过重置码修改密码；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/auth/reset-password，JSON={"student_no": "20260001", "reset_code": "[redacted]", "new_password": "[redacted]"}；POST /api/auth/reset-password，JSON={"student_no": "20260001", "reset_code": "[redacted]", "new_password": "[redacted]"}；POST /api/auth/reset-password，JSON={"student_no": "20260001", "reset_code": "[redacted]", "new_password": "[redacted]"} |
| 预期结果 | client.post('/api/auth/reset-password', json=body).status_code == 400；client.post('/api/auth/reset-password', json=body).status_code == 204；_login(client, password='reset1234').status_code == 200；client.post('/api/auth/reset-password', json=body).status_code == 400 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.185s。 实采HTTP 4次，状态分布{"400": 2, "204": 1, "200": 1}。POST /api/auth/reset-password → 204 {"bytes": 0} POST /api/auth/reset-password → 400 {"detail": {"code": "invalid_reset_code", "message": "重置码无效或已过期"}} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_auth.py:127](../backend/tests/test_auth.py)；`tests/test_auth.py::test_reset_password_with_code`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-058 重置码过期及重签失效

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-058；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 重置码过期及重签失效；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/auth/reset-password，JSON={"student_no": "20260001", "reset_code": "[redacted]", "new_password": "[redacted]"}；POST /api/auth/reset-password，JSON={"student_no": "20260001", "reset_code": "[redacted]", "new_password": "[redacted]"} |
| 预期结果 | client.post('/api/auth/reset-password', json=body).status_code == 400；client.post('/api/auth/reset-password', json=body).status_code == 400 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.157s。 实采HTTP 2次，状态分布{"400": 2}。POST /api/auth/reset-password → 400 {"detail": {"code": "invalid_reset_code", "message": "重置码无效或已过期"}} POST /api/auth/reset-password → 400 {"detail": {"code": "invalid_reset_code", "message": "重置码无效或已过期"}} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_auth.py:142](../backend/tests/test_auth.py)；`tests/test_auth.py::test_reset_code_expires_and_reissue_invalidates_old`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-059 备份API仅限运维访问

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-059；SRS NFR-008/012；ADR-09 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 备份API仅限运维访问；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/ops/backups；POST /api/ops/backups；GET /api/ops/backups；GET /api/ops/audit-logs |
| 预期结果 | client.post('/api/ops/backups', headers=login('A0000001', 'secret123')).status_code == 403；r.status_code == 201 and r.json()['size_bytes'] > 0；names == [r.json()['name']]；logs['total'] == 1 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.232s。 实采HTTP 6次，状态分布{"200": 4, "403": 1, "201": 1}。GET /api/ops/backups → 200 [{"name": "study_room-20261126-191908-706924.db", "size_bytes": 229376, "created_at": 1795691948.7140632}] GET /api/ops/audit-logs → 200 {"total": 1, "items": [{"id": 1, "operator_id": 2, "operator_student_no": "O0000001", "op_type": "admin_action", "target_type": "backup", "target_id": "study_room-20261126-191908-706924.db", "occurred_at": "2026-11-26T19:19:08.717263+08:00… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_backup_monitoring.py:18](../backend/tests/test_backup_monitoring.py)；`tests/test_backup_monitoring.py::test_backup_api_ops_only`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-060 备份轮换和数据库恢复

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-060；SRS NFR-008/012；ADR-09 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 备份轮换和数据库恢复；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：api_db, make_user |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_backup_rotation_and_restore，进行异常、返回值或Mock调用核验。 |
| 预期结果 | len(list_backups()) == 3 and first not in list_backups()；s.scalar(select(func.count()).select_from(User)) == 2；s.scalar(select(func.count()).select_from(User)) == 2；pytest.raises(FileNotFoundError) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.178s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_backup_monitoring.py:33](../backend/tests/test_backup_monitoring.py)；`tests/test_backup_monitoring.py::test_backup_rotation_and_restore`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-061 运行状态接口字段与访问

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-061；SRS NFR-008/012；ADR-09 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 运行状态接口字段与访问；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/ops/status；GET /api/ops/status |
| 预期结果 | client.get('/api/ops/status', headers=login('A0000001', 'secret123')).status_code == 403；data['users'] == 2 and data['active_sessions'] == 2；data['database']['size_bytes'] > 0 and data['latest_backup'] is None；data['requests']['requests'] == 3 and data['requests']['by_status']['4xx'] == 1 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.186s。 实采HTTP 4次，状态分布{"200": 3, "403": 1}。GET /api/ops/status → 403 {"detail": "无权限执行此操作"} GET /api/ops/status → 200 {"uptime_seconds": 15, "database": {"size_bytes": 4096, "wal_bytes": 506792}, "users": 2, "active_sessions": 2, "latest_backup": null, "requests": {"requests": 3, "by_status": {"2xx": 2, "4xx": 1}, "avg_ms": 13.4, "max_ms": 24.62}} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_backup_monitoring.py:53](../backend/tests/test_backup_monitoring.py)；`tests/test_backup_monitoring.py::test_status`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-062 登记表中的每个案例都必须至少有一个带 case 标记的测试

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-062；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 测试资产一致性 |
| 场景和风险 | 登记表中的每个案例都必须至少有一个带 case 标记的测试；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 现有case登记表、已收集测试及分阶段计划文档。 夹具：request |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_every_registered_case_has_at_least_one_test，进行异常、返回值或Mock调用核验。 |
| 预期结果 | set(CASES) <= marked；marked <= set(CASES) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_case_traceability.py:19](../backend/tests/test_case_traceability.py)；`tests/test_case_traceability.py::test_every_registered_case_has_at_least_one_test`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-063 测试计划文档必须列出登记表中的每个案例编号

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-063；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 测试资产一致性 |
| 场景和风险 | 测试计划文档必须列出登记表中的每个案例编号；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 现有case登记表、已收集测试及分阶段计划文档。 夹具： |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_plan_document_lists_every_registered_case，进行异常、返回值或Mock调用核验。 |
| 预期结果 | missing == [] |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_case_traceability.py:26](../backend/tests/test_case_traceability.py)；`tests/test_case_traceability.py::test_plan_document_lists_every_registered_case`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-064 两次未签退合并为 1 次计入警告；第三次再合并

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-064；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 两次未签退合并为 1 次计入警告；第三次再合并；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：api_db, make_user, clock |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_br093_no_checkout_merge，进行异常、返回值或Mock调用核验。 |
| 预期结果 | v1.is_offset is True；v1.period_seq == 0；v2.is_offset is False；v2.period_seq == 1；v3.is_offset is True；v3.period_seq == 0；len(counted) == 1 |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.135s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_gaps.py:62](../backend/tests/test_gaps.py)；`tests/test_gaps.py::test_br093_no_checkout_merge`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-065 暂离超时使用专用违规类型

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-065；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 暂离超时使用专用违规类型；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：api_db, make_user, clock, room_seats |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_temp_leave_timeout_type，进行异常、返回值或Mock调用核验。 |
| 预期结果 | counts['temp_leave'] == 1；v is not None；v.violation_type == E.ViolationType.TEMP_LEAVE_TIMEOUT |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.148s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_gaps.py:114](../backend/tests/test_gaps.py)；`tests/test_gaps.py::test_temp_leave_timeout_type`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-066 违规周期到期归档

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-066；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 违规周期到期归档；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：api_db, make_user, clock |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_archive_expired_violations，进行异常、返回值或Mock调用核验。 |
| 预期结果 | n == 1；v.state == E.ViolationState.ARCHIVED |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.126s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_gaps.py:144](../backend/tests/test_gaps.py)；`tests/test_gaps.py::test_archive_expired_violations`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-067 按房间区域自动分配座位

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-067；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 按房间区域自动分配座位；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login, room_seats, clock |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"room_id": 1, "zone_type": "quiet", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "request_key": "a2ab2460d494466d860c66009c81f291"}；POST /api/reservations，JSON={"room_id": 1, "zone_type": "quiet", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "request_key": "9c942314875b4df6a009fd9b54930479"} |
| 预期结果 | r.status_code == 201；r.json()['seat_id'] == room_seats.q1；r2.status_code == 201；r2.json()['seat_id'] == room_seats.q2 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.546s。 实采HTTP 4次，状态分布{"200": 2, "201": 2}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261102080000AD8DE1", "user_id": 1, "room_id": 1, "room_name": "缺口自习室", "seat_id": 1, "seat_code": "Q01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERV… POST /api/reservations → 201 {"id": 2, "reservation_no": "SR202611020800004AC6A4", "user_id": 2, "room_id": 1, "room_name": "缺口自习室", "seat_id": 2, "seat_code": "Q02", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERV… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_gaps.py:167](../backend/tests/test_gaps.py)；`tests/test_gaps.py::test_zone_auto_assign`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-068 座位设施条件筛选

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-068；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 座位设施条件筛选；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login, room_seats, clock |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/seats；GET /api/seats |
| 预期结果 | ids == {room_seats.q1, room_seats.d1}；ids == {room_seats.q2} |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.213s。 实采HTTP 3次，状态分布{"200": 3}。GET /api/seats → 200 [{"id": 3, "room_id": 1, "room_name": "缺口自习室", "code": "D01", "location": "图书馆", "floor": "3层", "facilities": null, "zone_type": "discussion", "has_power": true, "by_window": false, "accessible": false, "status": "available", "qr_payload":… GET /api/seats → 200 [{"id": 2, "room_id": 1, "room_name": "缺口自习室", "code": "Q02", "location": "图书馆", "floor": "3层", "facilities": null, "zone_type": "quiet", "has_power": false, "by_window": false, "accessible": true, "status": "available", "qr_payload": "stu… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_gaps.py:188](../backend/tests/test_gaps.py)；`tests/test_gaps.py::test_facility_filters`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-069 关闭房间取消未来预约

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-069；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 关闭房间取消未来预约；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login, room_seats, clock, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "request_key": "109693840bf144b386d52008fd98b863"}；PATCH /api/admin/rooms/1/status，JSON={"status": "closed"} |
| 预期结果 | r.status_code == 201；resp.status_code == 200；reservation.status == E.ReservationStatus.ADMIN_CANCELLED；any(('已关闭' in n.content for n in notes)) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.231s。 实采HTTP 4次，状态分布{"200": 3, "201": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR2026110208000019B385", "user_id": 1, "room_id": 1, "room_name": "缺口自习室", "seat_id": 1, "seat_code": "Q01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERV… PATCH /api/admin/rooms/1/status → 200 {"name": "缺口自习室", "location": "图书馆", "floor": "3层", "capacity": 10, "facilities": null, "remark": null, "id": 1, "status": "closed"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_gaps.py:210](../backend/tests/test_gaps.py)；`tests/test_gaps.py::test_close_room_cancels_reservations`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-070 开放时段调整取消冲突预约

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-070；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 开放时段调整取消冲突预约；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login, room_seats, clock, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T20:00:00+08:00", "end_time": "2026-11-02T21:00:00+08:00", "request_key": "0d5bc788fc38493d829389ce6c7e3251"}；GET /api/admin/rooms/1/schedules；PUT /api/admin/rooms/1/schedules/1，JSON={"day_type": "weekday", "open_time": "08:00:00", "close_time": "18:00:00", "enabled": true} |
| 预期结果 | r.status_code == 201；resp.status_code == 200；reservation.status == E.ReservationStatus.ADMIN_CANCELLED |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.240s。 实采HTTP 5次，状态分布{"200": 4, "201": 1}。GET /api/admin/rooms/1/schedules → 200 [{"day_type": "exam_week", "open_time": "08:00:00", "close_time": "22:00:00", "effective_from": null, "effective_to": null, "enabled": true, "id": 4, "room_id": 1}, {"day_type": "holiday", "open_time": "08:00:00", "close_time": "22:00:00",… PUT /api/admin/rooms/1/schedules/1 → 200 {"day_type": "weekday", "open_time": "08:00:00", "close_time": "18:00:00", "effective_from": null, "effective_to": null, "enabled": true, "id": 1, "room_id": 1} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_gaps.py:239](../backend/tests/test_gaps.py)；`tests/test_gaps.py::test_schedule_change_cancels_conflicting`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-071 健康接口与数据库连通

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-071；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 健康接口与数据库连通；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具： |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/health |
| 预期结果 | resp.status_code == 200；body['status'] == 'ok'；body['database'] == 'sqlite'；body['timezone'] == 'Asia/Shanghai' |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.012s。 实采HTTP 1次，状态分布{"200": 1}。GET /api/health → 200 {"status": "ok", "database": "sqlite", "timezone": "Asia/Shanghai", "server_time": "2026-11-26T19:19:10.765257+08:00"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_health.py:10](../backend/tests/test_health.py)；`tests/test_health.py::test_health_ok`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-072 服务端时间为UTC加8时区

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-072；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 服务端时间为UTC加8时区；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具： |
| 操作/输入 | 按源函数顺序执行：now() |
| 预期结果 | now().utcoffset() == timedelta(hours=8) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_health.py:19](../backend/tests/test_health.py)；`tests/test_health.py::test_server_time_is_utc_plus_8`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-073 SQLite外键WAL及忙等待配置

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-073；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | SQLite外键WAL及忙等待配置；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具： |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_sqlite_pragmas_enabled，进行异常、返回值或Mock调用核验。 |
| 预期结果 | conn.execute(text('PRAGMA foreign_keys')).scalar() == 1；conn.execute(text('PRAGMA journal_mode')).scalar() == 'wal'；conn.execute(text('PRAGMA busy_timeout')).scalar() == 5000 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_health.py:25](../backend/tests/test_health.py)；`tests/test_health.py::test_sqlite_pragmas_enabled`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-074 登录成功失败和注销留痕

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-074；SRS NFR-008/012；ADR-09 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 登录成功失败和注销留痕；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/auth/logout |
| 预期结果 | rows == [('20260001', 'login', False, 'invalid_credentials', True), ('nobody99', 'login', False, 'invalid_credentials', False), ('20260001', 'login', True, None, True), ('20260001', 'logout', True, None, True)] |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.163s。 实采HTTP 4次，状态分布{"401": 2, "200": 1, "204": 1}。POST /api/auth/logout → 204 {"bytes": 0} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_logs.py:18](../backend/tests/test_logs.py)；`tests/test_logs.py::test_login_events_are_logged`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-075 登录日志仅运维可读

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-075；SRS NFR-008/012；ADR-09 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 登录日志仅运维可读；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/ops/login-logs；GET /api/ops/login-logs；GET /api/ops/login-logs；GET /api/ops/login-logs |
| 预期结果 | client.get('/api/ops/login-logs', headers=login('A0000001', 'secret123')).status_code == 403；data['total'] == 1 and data['items'][0]['reason'] == 'invalid_credentials'；data['total'] == 1；client.get('/api/ops/login-logs', headers=ops, params={'start': future}).json()['total'] == 0 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.192s。 实采HTTP 7次，状态分布{"401": 1, "200": 5, "403": 1}。GET /api/ops/login-logs → 200 {"total": 1, "items": [{"id": 3, "user_id": 2, "student_no": "A0000001", "event": "login", "success": true, "reason": null, "occurred_at": "2026-11-26T19:19:11.077291+08:00", "ip_address": "testclient", "user_agent": "testclient"}]} GET /api/ops/login-logs → 200 {"total": 0, "items": []} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_logs.py:35](../backend/tests/test_logs.py)；`tests/test_logs.py::test_login_logs_only_for_ops`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-076 审计日志过滤与分页

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-076；SRS NFR-008/012；ADR-09 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 审计日志过滤与分页；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/ops/audit-logs；POST /api/admin/rooms，JSON={"name": "301"}；GET /api/admin/users；PUT /api/admin/users/1/roles，JSON={"roles": ["user", "ops"]}；GET /api/ops/audit-logs；GET /api/ops/audit-logs；GET /api/ops/audit-logs；GET /api/ops/audit-logs；其余1步请求见本例原始证据。 |
| 预期结果 | client.get('/api/ops/audit-logs', headers=user).status_code == 403；data['total'] == 1 and data['items'][0]['operator_student_no'] == 'A0000001'；data['total'] == 0；data['total'] == 1 and len(data['items']) == 1；data['total'] == 2 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.233s。 实采HTTP 12次，状态分布{"200": 10, "403": 1, "201": 1}。GET /api/ops/audit-logs → 200 {"total": 0, "items": []} GET /api/ops/audit-logs → 200 {"total": 1, "items": [{"id": 1, "operator_id": 2, "operator_student_no": "A0000001", "op_type": "admin_action", "target_type": "study_room", "target_id": "1", "occurred_at": "2026-11-26T19:19:11.296622+08:00", "before_value": null, "after… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_logs.py:55](../backend/tests/test_logs.py)；`tests/test_logs.py::test_audit_logs_query_filters`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-077 清理到期审计及登录日志

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-077；SRS NFR-008/012；ADR-09 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 清理到期审计及登录日志；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：api_db |
| 操作/输入 | 按源函数顺序执行：now()；now() |
| 预期结果 | purge_expired(s) == {'audit_logs': 1, 'login_logs': 1}；s.scalar(select(AuditLog.target_type)) == 'x' |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.118s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_logs.py:82](../backend/tests/test_logs.py)；`tests/test_logs.py::test_purge_expired_logs`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-078 演示数据重复导入与重置

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-078；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 演示数据重复导入与重置；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：seeded |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_seed_is_idempotent_and_reset_rebuilds，进行异常、返回值或Mock调用核验。 |
| 预期结果 | mock_data.seed(s, moment=MOMENT) is False；mock_data.summary(s) == before；mock_data.seed(s, reset=True, moment=MOMENT) is True；mock_data.summary(s) == before |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计1.615s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_mock_data.py:42](../backend/tests/test_mock_data.py)；`tests/test_mock_data.py::test_seed_is_idempotent_and_reset_rebuilds`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-079 演示数据数量及状态组合

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-079；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 演示数据数量及状态组合；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：seeded |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_counts_and_states，进行异常、返回值或Mock调用核验。 |
| 预期结果 | _count(s, User) == 17；_count(s, StudyRoom) == 4；_count(s, Seat) == 40；_count(s, Reservation) >= 150；{E.ReservationStatus.RESERVED, E.ReservationStatus.ACTIVE, E.ReservationStatus.TEMP_LEAVE, E.ReservationStatus.COMPLETED, E.ReservationStatus.CANCELLED, E.ReservationStatus.EXPIRED, E.ReservationStatus.TIMED_OUT} <= statuses；s.scalar(select(func.count()).where(Reservation.cancel_type == E.CancelType.LATE))；{None, E.AppealResult.APPROVED, E.AppealResult.REJECTED} <= appeals；s.scalar(select(func.count()).where(Seat.status == E.SeatStatus.MAINTENANCE)) == 1；disabled.status == E.AccountStatus.DISABLED；r.status == E.RestrictionStatus.ACTIVE and r.end_at > MOMENT |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计1.127s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_mock_data.py:51](../backend/tests/test_mock_data.py)；`tests/test_mock_data.py::test_counts_and_states`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-080 演示预约不重叠且处于开放时间

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-080；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 演示预约不重叠且处于开放时间；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：seeded |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_no_overlaps_and_within_opening_hours，进行异常、返回值或Mock调用核验。 |
| 预期结果 | all((n <= 1 for _, n in per_user))；covers(s, r.room_id, r.start_time, r.end_time)；r.created_at <= MOMENT；k not in last_end or last_end[k] <= r.start_time；r.start_time > MOMENT；r.start_time <= MOMENT < r.end_time；r.end_time <= MOMENT |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.984s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_mock_data.py:78](../backend/tests/test_mock_data.py)；`tests/test_mock_data.py::test_no_overlaps_and_within_opening_hours`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-081 演示数据不会被扫尾误处理

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-081；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 演示数据不会被扫尾误处理；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：seeded |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_sweeper_finds_nothing_due，进行异常、返回值或Mock调用核验。 |
| 预期结果 | counts['no_show'] == counts['no_checkout'] == counts['temp_leave'] == 0；counts['archived_violations'] == 0；_count(s, ViolationRecord) >= 5 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计1.157s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_mock_data.py:110](../backend/tests/test_mock_data.py)；`tests/test_mock_data.py::test_sweeper_finds_nothing_due`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-082 演示角色账号可登录

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-082；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 演示角色账号可登录；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：seeded, client |
| 操作/输入 | 按源函数顺序执行：client.post('/api/auth/login', json={'student_no': no, 'password': pw}) |
| 预期结果 | r.status_code == 403；r.status_code == 200 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计1.044s。 实采HTTP 17次，状态分布{"200": 16, "403": 1}。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_mock_data.py:118](../backend/tests/test_mock_data.py)；`tests/test_mock_data.py::test_demo_accounts_can_log_in`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-083 生产环境拒绝导入演示数据

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-083；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 生产环境拒绝导入演示数据；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：api_db, monkeypatch |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_refuses_outside_dev，进行异常、返回值或Mock调用核验。 |
| 预期结果 | pytest.raises(mock_data.MockDataError) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.116s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_mock_data.py:127](../backend/tests/test_mock_data.py)；`tests/test_mock_data.py::test_refuses_outside_dev`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-084 开发脚本迁移与演示数据准备

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-084；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 单元（命令Mock） |
| 场景和风险 | 开发脚本迁移与演示数据准备；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 开发脚本runner被替换为记录列表；不启动服务或执行真实迁移命令。 夹具：monkeypatch |
| 操作/输入 | 按源函数顺序执行：dev.prepare_db(Path('py'), runner=runner)；dev.prepare_db(Path('py'), mock=False, runner=runner)；dev.prepare_db(Path('py'), reset=True, runner=runner)；dev.prepare_db(Path('py'), runner=runner) |
| 预期结果 | dev.prepare_db(Path('py'), runner=runner) is True；calls[0][-3:] == ['alembic', 'upgrade', 'head']；calls[1][-1] == 'seed-mock'；dev.prepare_db(Path('py'), mock=False, runner=runner) is False；len(calls) == 1；dev.prepare_db(Path('py'), reset=True, runner=runner) is True；calls[1][-1] == '--reset'；dev.prepare_db(Path('py'), runner=runner) is False；len(calls) == 1 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.008s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_mock_data.py:140](../backend/tests/test_mock_data.py)；`tests/test_mock_data.py::test_dev_script_prepare_db`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-085 开发脚本命令行参数

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-085；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 单元（命令Mock） |
| 场景和风险 | 开发脚本命令行参数；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 开发脚本runner被替换为记录列表；不启动服务或执行真实迁移命令。 夹具： |
| 操作/输入 | 按源函数顺序执行：dev.build_parser().parse_args(['--no-mock'])；dev.build_parser().parse_args(['dev', '--reset-mock'])；dev.build_parser()；dev.build_parser() |
| 预期结果 | a.no_mock and a.cmd is None；a.reset_mock |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.007s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_mock_data.py:160](../backend/tests/test_mock_data.py)；`tests/test_mock_data.py::test_dev_script_flags`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-086 迁移创建全部模型表

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-086；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 迁移创建全部模型表；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：engine |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_all_tables_created，进行异常、返回值或Mock调用核验。 |
| 预期结果 | set(Base.metadata.tables) <= tables；'zones' not in tables；'waitlist_entries' not in tables |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.137s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:76](../backend/tests/test_models.py)；`tests/test_models.py::test_all_tables_created`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-087 数据库迁移可重复及可逆

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-087；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 数据库迁移可重复及可逆；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：db_url |
| 操作/输入 | 按源函数顺序执行：command.upgrade(cfg, 'head')；command.downgrade(cfg, 'base')；command.upgrade(cfg, 'head') |
| 预期结果 | conn.execute(text('SELECT version_num FROM alembic_version')).scalar() == head；conn.execute(text('SELECT count(*) FROM roles')).scalar() == 3 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.386s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:83](../backend/tests/test_models.py)；`tests/test_models.py::test_migration_rerunnable_and_reversible`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-088 迁移与 ORM 模型一致（等同 alembic check）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-088；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 迁移与 ORM 模型一致（等同 alembic check）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：db_url |
| 操作/输入 | 按源函数顺序执行：command.check(_alembic_cfg(db_url)) |
| 预期结果 | 按测试函数中的异常期望及调用断言核验，见源代码。 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.177s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:96](../backend/tests/test_models.py)；`tests/test_models.py::test_migration_matches_models`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-089 数据库初始角色齐全

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-089；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 数据库集成 |
| 场景和风险 | 数据库初始角色齐全；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_roles_seeded，进行异常、返回值或Mock调用核验。 |
| 预期结果 | names == {E.RoleName.USER, E.RoleName.ADMIN, E.RoleName.OPS} |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.125s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:101](../backend/tests/test_models.py)；`tests/test_models.py::test_roles_seeded`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-090 用户学号唯一约束

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-090；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 数据库集成 |
| 场景和风险 | 用户学号唯一约束；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_student_no_unique，进行异常、返回值或Mock调用核验。 |
| 预期结果 | pytest.raises(IntegrityError) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.122s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:109](../backend/tests/test_models.py)；`tests/test_models.py::test_student_no_unique`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-091 数据库强制外键约束

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-091；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 数据库强制外键约束；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_foreign_keys_enforced，进行异常、返回值或Mock调用核验。 |
| 预期结果 | pytest.raises(IntegrityError) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.122s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:117](../backend/tests/test_models.py)；`tests/test_models.py::test_foreign_keys_enforced`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-092 房间内座位编号唯一

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-092；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 房间内座位编号唯一；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_seat_code_unique_within_room，进行异常、返回值或Mock调用核验。 |
| 预期结果 | pytest.raises(IntegrityError) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.397s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:123](../backend/tests/test_models.py)；`tests/test_models.py::test_seat_code_unique_within_room`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-093 数据库枚举检查约束

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-093；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 数据库枚举检查约束；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_enum_check_constraint，进行异常、返回值或Mock调用核验。 |
| 预期结果 | pytest.raises(IntegrityError) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.118s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:130](../backend/tests/test_models.py)；`tests/test_models.py::test_enum_check_constraint`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-094 ORM拒绝非法枚举

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-094；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | ORM拒绝非法枚举；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具： |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_invalid_enum_rejected_by_orm，进行异常、返回值或Mock调用核验。 |
| 预期结果 | pytest.raises((StatementError, LookupError, ValueError)) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:140](../backend/tests/test_models.py)；`tests/test_models.py::test_invalid_enum_rejected_by_orm`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-095 数据库拒绝无效预约起止顺序

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-095；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 数据库拒绝无效预约起止顺序；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：now() |
| 预期结果 | pytest.raises(IntegrityError) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.120s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:145](../backend/tests/test_models.py)；`tests/test_models.py::test_reservation_time_order`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-096 同座同起点有效预约唯一约束

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-096；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 同座同起点有效预约唯一约束；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：now() |
| 预期结果 | pytest.raises(IntegrityError) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.129s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:156](../backend/tests/test_models.py)；`tests/test_models.py::test_one_active_reservation_per_seat_slot`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-097 门禁来源事件号唯一约束

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-097；SRS HD-15/16/30/31/52、NFR-013/014；ADR-06 |
| 层级 | 数据库集成 |
| 场景和风险 | 门禁来源事件号唯一约束；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：now() |
| 预期结果 | pytest.raises(IntegrityError) |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.114s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:176](../backend/tests/test_models.py)；`tests/test_models.py::test_entry_exit_dedup`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-098 日期时间按北京时间往返存取

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-098；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 日期时间按北京时间往返存取；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_datetime_stored_as_utc8，进行异常、返回值或Mock调用核验。 |
| 预期结果 | str(raw).startswith('2026-11-01 08:00:00')；loaded.start_time.utcoffset() == timedelta(hours=8)；loaded.start_time == utc_start |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.128s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:194](../backend/tests/test_models.py)；`tests/test_models.py::test_datetime_stored_as_utc8`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-099 拒绝无时区日期时间入库

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-099；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 拒绝无时区日期时间入库；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_naive_datetime_rejected，进行异常、返回值或Mock调用核验。 |
| 预期结果 | pytest.raises(StatementError) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.125s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:208](../backend/tests/test_models.py)；`tests/test_models.py::test_naive_datetime_rejected`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-100 业务异常回滚全部事务变化

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-100；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 业务异常回滚全部事务变化；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_transaction_rolls_back_all_changes_on_error，进行异常、返回值或Mock调用核验。 |
| 预期结果 | session.scalar(select(User).where(User.student_no == 'rollback-1')) is None；session.get(Seat, seat.id).status == E.SeatStatus.AVAILABLE；pytest.raises(RuntimeError) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.115s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:219](../backend/tests/test_models.py)；`tests/test_models.py::test_transaction_rolls_back_all_changes_on_error`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-101 数据库约束失败回滚事务

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-101；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 数据库约束失败回滚事务；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_transaction_rolls_back_on_constraint_violation，进行异常、返回值或Mock调用核验。 |
| 预期结果 | session.scalar(select(User).where(User.student_no == 'ok-but-rolled-back')) is None；pytest.raises(IntegrityError) |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.126s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:231](../backend/tests/test_models.py)；`tests/test_models.py::test_transaction_rolls_back_on_constraint_violation`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-102 成功事务正常提交

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-102；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | 成功事务正常提交；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：session |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_transaction_commits_on_success，进行异常、返回值或Mock调用核验。 |
| 预期结果 | session.scalar(select(User).where(User.student_no == 'committed')) is not None |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.116s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:241](../backend/tests/test_models.py)；`tests/test_models.py::test_transaction_commits_on_success`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-103 BEGIN IMMEDIATE 一开始就持有写锁：另一连接的写事务在 busy_timeout 后失败

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-103；SRS FR-070～075、BR-050～053；ADR-02/08 |
| 层级 | 数据库集成 |
| 场景和风险 | BEGIN IMMEDIATE 一开始就持有写锁：另一连接的写事务在 busy_timeout 后失败；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 每例独立迁移的临时文件SQLite；真实连接/约束，测试数据为合成数据。 夹具：engine, db_url |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_immediate_transaction_takes_write_lock，进行异常、返回值或Mock调用核验。 |
| 预期结果 | pytest.raises(sqlite3.OperationalError, match='locked') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.280s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_models.py:248](../backend/tests/test_models.py)；`tests/test_models.py::test_immediate_transaction_takes_write_lock`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-104 数据库权限矩阵与代码一致

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-104；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 服务／数据库集成 |
| 场景和风险 | 数据库权限矩阵与代码一致；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 依照api_db/session等夹具使用临时SQLite及合成数据；具体隔离/patch见源码。 夹具：api_db |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_db_permission_matrix_matches_code，进行异常、返回值或Mock调用核验。 |
| 预期结果 | db == {c: sorted(v[3]) for c, v in PERMISSIONS.items()} |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.126s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_permissions.py:11](../backend/tests/test_permissions.py)；`tests/test_permissions.py::test_db_permission_matrix_matches_code`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-105 本人接口返回角色权限集合

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-105；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 本人接口返回角色权限集合；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/auth/me |
| 预期结果 | 'system_log:read' in me['permissions']；'room:manage' not in me['permissions'] |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.141s。 实采HTTP 2次，状态分布{"200": 2}。GET /api/auth/me → 200 {"id": 1, "student_no": "20260001", "name": "测试用户", "department": null, "contact": null, "status": "normal", "roles": ["ops"], "permissions": ["audit_log:read", "entry_exit:read", "room:read", "system:backup", "system_log:read"]} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_permissions.py:22](../backend/tests/test_permissions.py)；`tests/test_permissions.py::test_me_lists_permissions`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-106 仅管理员能够管理用户

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-106；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 仅管理员能够管理用户；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/admin/users；GET /api/admin/users；GET /api/admin/users；GET /api/admin/users |
| 预期结果 | client.get('/api/admin/users').status_code == 401；r.status_code == code |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.180s。 实采HTTP 7次，状态分布{"200": 4, "403": 2, "401": 1}。GET /api/admin/users → 200 {"total": 3, "items": [{"id": 1, "student_no": "20260001", "name": "测试用户", "department": null, "contact": null, "status": "normal", "roles": ["user"], "permissions": ["reservation:own", "room:read"]}, {"id": 2, "student_no": "20260002", "n… GET /api/admin/users → 401 {"detail": "请先登录"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_permissions.py:29](../backend/tests/test_permissions.py)；`tests/test_permissions.py::test_only_admin_can_manage_users`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-107 管理员角色变更及审计

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-107；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 管理员角色变更及审计；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/admin/users；PUT /api/admin/users/1/roles，JSON={"roles": ["user", "ops"]}；GET /api/auth/me |
| 预期结果 | users['total'] == 1；r.status_code == 200 and r.json()['roles'] == ['ops', 'user']；log.op_type == 'permission_change' and log.target_id == str(uid)；json.loads(log.before_value) == {'roles': ['user']}；json.loads(log.after_value) == {'roles': ['ops', 'user']}；'system_log:read' in me['permissions'] |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.520s。 实采HTTP 5次，状态分布{"200": 5}。PUT /api/admin/users/1/roles → 200 {"id": 1, "student_no": "20260001", "name": "测试用户", "department": null, "contact": null, "status": "normal", "roles": ["ops", "user"], "permissions": ["audit_log:read", "entry_exit:read", "reservation:own", "room:read", "system:backup", "s… GET /api/auth/me → 200 {"id": 1, "student_no": "20260001", "name": "测试用户", "department": null, "contact": null, "status": "normal", "roles": ["ops", "user"], "permissions": ["audit_log:read", "entry_exit:read", "reservation:own", "room:read", "system:backup", "s… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_permissions.py:39](../backend/tests/test_permissions.py)；`tests/test_permissions.py::test_admin_promotes_user_and_change_is_logged`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-108 管理员不得自降权或自禁用

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-108；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 管理员不得自降权或自禁用；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/auth/me；PUT /api/admin/users/1/roles，JSON={"roles": ["user"]}；PATCH /api/admin/users/1/status，JSON={"status": "disabled"} |
| 预期结果 | r.status_code == 400；r.status_code == 400 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.156s。 实采HTTP 4次，状态分布{"200": 2, "400": 2}。PUT /api/admin/users/1/roles → 400 {"detail": "不能移除自己的管理员角色"} PATCH /api/admin/users/1/status → 400 {"detail": "不能禁用自己的账户"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_permissions.py:59](../backend/tests/test_permissions.py)；`tests/test_permissions.py::test_admin_cannot_demote_or_disable_self`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-109 禁用账号撤销会话并拒绝登录

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-109；SRS NFR-008/012；ADR-09 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 禁用账号撤销会话并拒绝登录；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/auth/me；PATCH /api/admin/users/1/status，JSON={"status": "disabled"}；GET /api/auth/me；PATCH /api/admin/users/1/status，JSON={"status": "normal"} |
| 预期结果 | r.status_code == 200；client.get('/api/auth/me', headers=user).status_code == 401；r.status_code == 403；login('20260001', 'secret123') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.199s。 实采HTTP 8次，状态分布{"200": 6, "401": 1, "403": 1}。GET /api/auth/me → 401 {"detail": "登录已失效，请重新登录"} PATCH /api/admin/users/1/status → 200 {"id": 1, "student_no": "20260001", "name": "测试用户", "department": null, "contact": null, "status": "normal", "roles": ["user"], "permissions": ["reservation:own", "room:read"]} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_permissions.py:69](../backend/tests/test_permissions.py)；`tests/test_permissions.py::test_disable_account_logs_out_and_blocks_login`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-110 管理员为目标用户签发重置码

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-110；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 管理员为目标用户签发重置码；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/admin/users；POST /api/admin/users/1/reset-code；POST /api/auth/reset-password，JSON={"student_no": "20260001", "reset_code": "[redacted]", "new_password": "[redacted]"} |
| 预期结果 | r.status_code == 204；login('20260001', 'brandnew1') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.186s。 实采HTTP 5次，状态分布{"200": 4, "204": 1}。POST /api/admin/users/1/reset-code → 200 {"reset_code": "[redacted]", "expires_in": 1800} POST /api/auth/reset-password → 204 {"bytes": 0} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_permissions.py:85](../backend/tests/test_permissions.py)；`tests/test_permissions.py::test_admin_issues_reset_code`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-111 CLI创建管理员账号

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-111；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | CLI创建管理员账号；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：monkeypatch, api_db, client, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/auth/me |
| 预期结果 | cli.main(['create-user', '--student-no', 'A0000009', '--name', '管理员', '--role', 'admin', '--password', 'adminpw123']) == 0；me['roles'] == ['admin'] |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.151s。 实采HTTP 2次，状态分布{"200": 2}。GET /api/auth/me → 200 {"id": 1, "student_no": "A0000009", "name": "管理员", "department": null, "contact": null, "status": "normal", "roles": ["admin"], "permissions": ["appeal:manage", "audit_log:read", "data:export", "reservation:own", "reservation:read_all", "r… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_permissions.py:101](../backend/tests/test_permissions.py)；`tests/test_permissions.py::test_cli_create_admin`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-112 房间搜索详情及区间座位状态

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-112；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 房间搜索详情及区间座位状态；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/rooms?date=2026-11-02；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；GET /api/seats；GET /api/seats；GET /api/seats/1；GET /api/seats/1；GET /api/seats/2 |
| 预期结果 | rooms.status_code == 200；(room['name'], room['location'], room['floor'], room['capacity']) == ('自习室1', '图书馆', '1层', 3)；room['opening_hours'] == [{'open_time': '06:00:00', 'close_time': '23:30:00'}]；r.status_code == 201；[x['status'] for x in result] == ['reserved', 'available']；[x['id'] for x in filtered.json()] == [seats.b]；detail['has_power'] and detail['zone_type'] == 'quiet'；detail['qr_payload'] == f'studyroom:seat:{seats.a}'；'user_id' not in detail and 'reservation_no' not in detail；client.get(f'/api/seats/{seats.a}', headers=actors.b, params=query).json()['status'] == 'available'；client.get(f'/api/seats/{seats.b}', headers=actors.a).json()['status'] == 'maintenance' |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.279s。 实采HTTP 9次，状态分布{"200": 8, "201": 1}。GET /api/seats/1 → 200 {"id": 1, "room_id": 1, "room_name": "自习室1", "code": "A01", "location": "图书馆", "floor": "1层", "facilities": null, "zone_type": "quiet", "has_power": true, "by_window": false, "accessible": false, "status": "available", "qr_payload": "study… GET /api/seats/2 → 200 {"id": 2, "room_id": 1, "room_name": "自习室1", "code": "A02", "location": "图书馆", "floor": "1层", "facilities": null, "zone_type": "discussion", "has_power": false, "by_window": false, "accessible": false, "status": "maintenance", "qr_payload"… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:94](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_room_search_detail_and_interval_states`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-113 资源查询拒绝不完整或非法时间（query='date=2026-11-02'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-113；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 资源查询拒绝不完整或非法时间（query='date=2026-11-02'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, query |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/seats?date=2026-11-02；本例参数：query='date=2026-11-02'；参数：{"query": "'date=2026-11-02'"} |
| 预期结果 | client.get(f'/api/seats?{query}', headers=actors.a).status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.190s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。GET /api/seats?date=2026-11-02 → 422 {"detail": "查询时请同时提供日期、开始时间和结束时间"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:146](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_search_invalid_inputs[date=2026-11-02]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-114 资源查询拒绝不完整或非法时间（query='start_time=09:00&end_time=10:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-114；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 资源查询拒绝不完整或非法时间（query='start_time=09:00&end_time=10:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, query |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/seats?start_time=09:00&end_time=10:00；本例参数：query='start_time=09:00&end_time=10:00'；参数：{"query": "'start_time=09:00&end_time=10:00'"} |
| 预期结果 | client.get(f'/api/seats?{query}', headers=actors.a).status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.186s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。GET /api/seats?start_time=09:00&end_time=10:00 → 422 {"detail": "查询时请同时提供日期、开始时间和结束时间"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:146](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_search_invalid_inputs[start_time=09:00&end_time=10:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-115 资源查询拒绝不完整或非法时间（query='date=2026-11-02&start_time=23:00&end_time=01:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-115；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 资源查询拒绝不完整或非法时间（query='date=2026-11-02&start_time=23:00&end_time=01:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, query |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/seats?date=2026-11-02&start_time=23:00&end_time=01:00；本例参数：query='date=2026-11-02&start_time=23:00&end_time=01:00'；参数：{"query": "'date=2026-11-02&start_time=23:00&end_time=01:00'"} |
| 预期结果 | client.get(f'/api/seats?{query}', headers=actors.a).status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.181s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。GET /api/seats?date=2026-11-02&start_time=23:00&end_time=01:00 → 422 {"detail": "查询时段须为北京时间，开始早于结束且不跨零点"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:146](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_search_invalid_inputs[date=2026-11-02&start_time=23:00&end_time=01:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-116 资源查询拒绝不完整或非法时间（query='zone_type=unknown'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-116；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 资源查询拒绝不完整或非法时间（query='zone_type=unknown'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, query |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：GET /api/seats?zone_type=unknown；本例参数：query='zone_type=unknown'；参数：{"query": "'zone_type=unknown'"} |
| 预期结果 | client.get(f'/api/seats?{query}', headers=actors.a).status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.190s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。GET /api/seats?zone_type=unknown → 422 {"detail": [{"type": "enum", "loc": ["query", "zone_type"], "msg": "Input should be 'quiet', 'discussion' or 'exam_prep'", "input": "unknown", "ctx": {"expected": "'quiet', 'discussion' or 'exam_prep'"}}]} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:146](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_search_invalid_inputs[zone_type=unknown]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-117 校历优先级生效日期与关闭房间

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-117；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 校历优先级生效日期与关闭房间；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；GET /api/rooms；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；GET /api/seats/1 |
| 预期结果 | reserve(client, actors.a, seats.a).status_code == 422；rooms[0]['opening_hours'][0]['open_time'] == '12:00:00'；reserve(client, actors.a, seats.a).status_code == 409；client.get(f'/api/seats/{seats.a}', headers=actors.a).json()['status'] == 'closed' |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.221s。 实采HTTP 6次，状态分布{"200": 4, "422": 1, "409": 1}。POST /api/reservations → 409 {"detail": "座位维护中或已关闭，请选择其他座位"} GET /api/seats/1 → 200 {"id": 1, "room_id": 1, "room_name": "自习室1", "code": "A01", "location": "图书馆", "floor": "1层", "facilities": null, "zone_type": "quiet", "has_power": true, "by_window": false, "accessible": false, "status": "closed", "qr_payload": "studyroo… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:150](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_calendar_priority_effective_dates_and_closed_room`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-118 创建预约拒绝非法时间（start='2026-11-02T05:59:00+08:00'；end='2026-11-02T08:00:00+08:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-118；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 创建预约拒绝非法时间（start='2026-11-02T05:59:00+08:00'；end='2026-11-02T08:00:00+08:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T05:59:00+08:00", "end_time": "2026-11-02T08:00:00+08:00"}；本例参数：start='2026-11-02T05:59:00+08:00'；end='2026-11-02T08:00:00+08:00'；参数：{"start": "'2026-11-02T05:59:00+08:00'", "end": "'2026-11-02T08:00:00+08:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.510s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": "时段须完整落在自习室开放时间内（06:00–23:30，不跨零点）"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_create_rejects_invalid_times[2026-11-02T05:59:00+08:00-2026-11-02T08:00:00+08:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-119 创建预约拒绝非法时间（start='2026-11-02T22:00:00+08:00'；end='2026-11-02T23:31:00+08:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-119；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 创建预约拒绝非法时间（start='2026-11-02T22:00:00+08:00'；end='2026-11-02T23:31:00+08:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T22:00:00+08:00", "end_time": "2026-11-02T23:31:00+08:00"}；本例参数：start='2026-11-02T22:00:00+08:00'；end='2026-11-02T23:31:00+08:00'；参数：{"start": "'2026-11-02T22:00:00+08:00'", "end": "'2026-11-02T23:31:00+08:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.196s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": "时段须完整落在自习室开放时间内（06:00–23:30，不跨零点）"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_create_rejects_invalid_times[2026-11-02T22:00:00+08:00-2026-11-02T23:31:00+08:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-120 创建预约拒绝非法时间（start='2026-11-02T23:00:00+08:00'；end='2026-11-03T01:00:00+08:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-120；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 创建预约拒绝非法时间（start='2026-11-02T23:00:00+08:00'；end='2026-11-03T01:00:00+08:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T23:00:00+08:00", "end_time": "2026-11-03T01:00:00+08:00"}；本例参数：start='2026-11-02T23:00:00+08:00'；end='2026-11-03T01:00:00+08:00'；参数：{"start": "'2026-11-02T23:00:00+08:00'", "end": "'2026-11-03T01:00:00+08:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.185s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": "Value error, 预约不可跨零点"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_create_rejects_invalid_times[2026-11-02T23:00:00+08:00-2026-11-03T01:00:00+08:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-121 创建预约拒绝非法时间（start='2026-11-04T09:00:00+08:00'；end='2026-11-04T10:00:00+08:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-121；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 创建预约拒绝非法时间（start='2026-11-04T09:00:00+08:00'；end='2026-11-04T10:00:00+08:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-04T09:00:00+08:00", "end_time": "2026-11-04T10:00:00+08:00"}；本例参数：start='2026-11-04T09:00:00+08:00'；end='2026-11-04T10:00:00+08:00'；参数：{"start": "'2026-11-04T09:00:00+08:00'", "end": "'2026-11-04T10:00:00+08:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.195s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": "最多提前1天预约，请调整日期"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_create_rejects_invalid_times[2026-11-04T09:00:00+08:00-2026-11-04T10:00:00+08:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-122 创建预约拒绝非法时间（start='2026-11-02T09:00:00+08:00'；end='2026-11-02T09:00:00+08:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-122；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 创建预约拒绝非法时间（start='2026-11-02T09:00:00+08:00'；end='2026-11-02T09:00:00+08:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T09:00:00+08:00"}；本例参数：start='2026-11-02T09:00:00+08:00'；end='2026-11-02T09:00:00+08:00'；参数：{"start": "'2026-11-02T09:00:00+08:00'", "end": "'2026-11-02T09:00:00+08:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.179s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": "Value error, 开始时间必须早于结束时间"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_create_rejects_invalid_times[2026-11-02T09:00:00+08:00-2026-11-02T09:00:00+08:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-123 创建预约拒绝非法时间（start='2026-11-02T09:00:00'；end='2026-11-02T10:00:00'）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-123；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 创建预约拒绝非法时间（start='2026-11-02T09:00:00'；end='2026-11-02T10:00:00'）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, start, end |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00", "end_time": "2026-11-02T10:00:00"}；本例参数：start='2026-11-02T09:00:00'；end='2026-11-02T10:00:00'；参数：{"start": "'2026-11-02T09:00:00'", "end": "'2026-11-02T10:00:00'"} |
| 预期结果 | response.status_code == 422 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.189s。 实采HTTP 3次，状态分布{"200": 2, "422": 1}。POST /api/reservations → 422 {"detail": [{"type": "value_error", "loc": ["body", "start_time"], "msg": "Value error, 预约时间必须包含时区", "input": "2026-11-02T09:00:00", "ctx": {"error": {}}}, {"type": "value_error", "loc": ["body", "end_time"], "msg": "Value error, 预约时间必须包含时… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:181](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_create_rejects_invalid_times[2026-11-02T09:00:00-2026-11-02T10:00:00]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-124 当天次日短时段与全天开放预约

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-124；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 当天次日短时段与全天开放预约；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T06:00:00+08:00", "end_time": "2026-11-02T23:30:00+08:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-03T09:00:00+08:00", "end_time": "2026-11-03T09:00:01+08:00"} |
| 预期结果 | reserve(client, actors.a, seats.a, body=full).status_code == 201；reserve(client, actors.a, seats.a, body=short).status_code == 201 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.215s。 实采HTTP 4次，状态分布{"200": 2, "201": 2}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR202611020500001806E0", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T06:00:00+08:00", "end_time": "2026-11-02T23:30:00+08:00", "status": "RESERVE… POST /api/reservations → 201 {"id": 2, "reservation_no": "SR202611020500005B74AF", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-03T09:00:00+08:00", "end_time": "2026-11-03T09:00:01+08:00", "status": "RESERVE… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:187](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_today_tomorrow_short_duration_and_full_opening_day`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-125 座位及本人冲突相邻区间与时区转换

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-125；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 座位及本人冲突相邻区间与时区转换；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 3, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T01:30:00Z", "end_time": "2026-11-02T02:30:00Z"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T10:00:00+08:00", "end_time": "2026-11-02T11:00:00+08:00"} |
| 预期结果 | first.status_code == 201；reserve(client, actors.b, seats.a).status_code == 409；reserve(client, actors.a, seats.c).status_code == 409；reserve(client, actors.b, seats.a, body=utc).status_code == 409；reserve(client, actors.a, seats.a, body=adjacent).status_code == 201 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.244s。 实采HTTP 7次，状态分布{"200": 2, "201": 2, "409": 3}。POST /api/reservations → 409 {"detail": "该座位在所选时段已被预约，请重新选择"} POST /api/reservations → 201 {"id": 2, "reservation_no": "SR20261102080000461693", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T10:00:00+08:00", "end_time": "2026-11-02T11:00:00+08:00", "status": "RESERVE… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:196](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_overlap_person_overlap_adjacent_and_utc_conversion`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-126 无键现状及幂等键用户载荷范围

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-126；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 无键现状及幂等键用户载荷范围；现有断言通过不等于全部业务需求验收。 源函数名称含required，但正文测试接受无键创建，按实际断言归档，不声称强制幂等键。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 3, "start_time": "2026-11-02T11:00:00+08:00", "end_time": "2026-11-02T12:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 2, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；PATCH /api/reservations/2/seat，JSON={"seat_id": 2}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/2/cancel；其余1步请求见本例原始证据。 |
| 预期结果 | client.post('/api/reservations', headers=actors.a, json=payload(seats.c, '2026-11-02T11:00:00+08:00', '2026-11-02T12:00:00+08:00')).status_code == 201；first.status_code == 201 and replay.status_code == 200；replay.headers['Idempotent-Replayed'] == 'true'；replay.json()['id'] == first.json()['id']；reserve(client, actors.a, seats.b, key=key).status_code == 409；reserve(client, actors.b, seats.a, key=key).status_code == 409；reserve(client, actors.a, seats.a, key=key).json()['seat_id'] == seats.b；reserve(client, actors.a, seats.a, key=key).json()['status'] == 'CANCELLED'；count(api_db, Reservation) == 2 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.273s。 实采HTTP 11次，状态分布{"200": 7, "201": 2, "409": 2}。POST /api/reservations/2/cancel → 200 {"id": 2, "reservation_no": "SR20261102080000131376", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 2, "seat_code": "A02", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… POST /api/reservations → 200 {"id": 2, "reservation_no": "SR20261102080000131376", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 2, "seat_code": "A02", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:208](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_idempotency_key_required_and_scoped_to_payload_and_user`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-127 换座重查冲突且失败保留原预约

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-127；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 换座重查冲突且失败保留原预约；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 2, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；PATCH /api/reservations/1/seat，JSON={"seat_id": 2}；GET /api/reservations/1；PATCH /api/reservations/1/seat，JSON={"seat_id": 3, "start_time": "2026-11-02"}；PATCH /api/reservations/1/seat，JSON={"seat_id": 3}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"} |
| 预期结果 | client.patch(path, headers=actors.a, json={'seat_id': seats.b}).status_code == 409；client.get(f'/api/reservations/{rid}', headers=actors.a).json()['seat_id'] == seats.a；client.patch(path, headers=actors.a, json={'seat_id': seats.c, 'start_time': '2026-11-02'}).status_code == 422；response.status_code == 200；response.json()['room_id'] == seats.other_room；response.json()['start_time'] == '2026-11-02T09:00:00+08:00'；reserve(client, actors.b, seats.a).status_code == 409 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.597s。 实采HTTP 9次，状态分布{"200": 4, "201": 2, "409": 2, "422": 1}。PATCH /api/reservations/1/seat → 200 {"id": 1, "reservation_no": "SR20261102080000356733", "user_id": 1, "room_id": 2, "room_name": "自习室2", "seat_id": 3, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… POST /api/reservations → 409 {"detail": "你在该时段已有有效预约"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:236](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_change_seat_rechecks_conflicts_and_preserves_original_on_failure`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-128 取消15分钟边界及未到场违规互斥（minutes=16；late=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-128；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 取消15分钟边界及未到场违规互斥（minutes=16；late=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db, minutes, late |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/cancel；POST /api/reservations/1/cancel；本例参数：minutes=16；late=False；参数：{"minutes": "16", "late": "False"} |
| 预期结果 | r.status_code == 200；r.json()['cancel_type'] == ('late' if late else 'normal')；count(api_db, ViolationRecord) == int(late)；count(api_db, AuditLog) == int(late)；service.expire_due(s) == 0；s.get(Seat, seats.a).status == E.SeatStatus.AVAILABLE；s.scalar(select(ViolationRecord.violation_type)) == E.ViolationType.LATE_CANCEL |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.258s。 实采HTTP 5次，状态分布{"200": 4, "201": 1}。POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR20261102080000540F31", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR20261102080000540F31", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:256](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_cancel_exact_boundary_and_no_show_mutual_exclusion[16-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-129 取消15分钟边界及未到场违规互斥（minutes=15；late=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-129；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 取消15分钟边界及未到场违规互斥（minutes=15；late=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db, minutes, late |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/cancel；POST /api/reservations/1/cancel；本例参数：minutes=15；late=True；参数：{"minutes": "15", "late": "True"} |
| 预期结果 | r.status_code == 200；r.json()['cancel_type'] == ('late' if late else 'normal')；count(api_db, ViolationRecord) == int(late)；count(api_db, AuditLog) == int(late)；service.expire_due(s) == 0；s.get(Seat, seats.a).status == E.SeatStatus.AVAILABLE；s.scalar(select(ViolationRecord.violation_type)) == E.ViolationType.LATE_CANCEL |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.245s。 实采HTTP 5次，状态分布{"200": 4, "201": 1}。POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR20261102080000929CF4", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR20261102080000929CF4", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:256](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_cancel_exact_boundary_and_no_show_mutual_exclusion[15-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-130 取消15分钟边界及未到场违规互斥（minutes=1；late=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-130；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 取消15分钟边界及未到场违规互斥（minutes=1；late=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db, minutes, late |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/cancel；POST /api/reservations/1/cancel；本例参数：minutes=1；late=True；参数：{"minutes": "1", "late": "True"} |
| 预期结果 | r.status_code == 200；r.json()['cancel_type'] == ('late' if late else 'normal')；count(api_db, ViolationRecord) == int(late)；count(api_db, AuditLog) == int(late)；service.expire_due(s) == 0；s.get(Seat, seats.a).status == E.SeatStatus.AVAILABLE；s.scalar(select(ViolationRecord.violation_type)) == E.ViolationType.LATE_CANCEL |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.248s。 实采HTTP 5次，状态分布{"200": 4, "201": 1}。POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR20261102080000DD41EC", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR20261102080000DD41EC", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:256](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_cancel_exact_boundary_and_no_show_mutual_exclusion[1-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-131 禁约允许取消但拒绝创建换座

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-131；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 禁约允许取消但拒绝创建换座；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, api_db, clock |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；PATCH /api/reservations/1/seat，JSON={"seat_id": 2}；POST /api/reservations/1/cancel；POST /api/reservations，JSON={"seat_id": 2, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"} |
| 预期结果 | client.patch(f'/api/reservations/{rid}/seat', headers=actors.a, json={'seat_id': seats.b}).status_code == 403；client.post(f'/api/reservations/{rid}/cancel', headers=actors.a).status_code == 200；reserve(client, actors.a, seats.b).status_code == 403 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.237s。 实采HTTP 6次，状态分布{"200": 3, "201": 1, "403": 2}。POST /api/reservations/1/cancel → 200 {"id": 1, "reservation_no": "SR20261102080000546165", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "CANCELL… POST /api/reservations → 403 {"detail": "当前处于禁约期，解除时间：2026-11-03T08:00:00+08:00"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:276](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_restricted_user_can_cancel_but_cannot_create_or_change`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-132 签到窗口前缘边界（minute=44；second=59；success=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-132；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 签到窗口前缘边界（minute=44；second=59；success=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, minute, second, success |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/check-in，JSON={"seat_id": 1}；本例参数：minute=44；second=59；success=False；参数：{"minute": "44", "second": "59", "success": "False"} |
| 预期结果 | r.status_code == (200 if success else 409) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.247s。 实采HTTP 4次，状态分布{"200": 2, "201": 1, "409": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261102080000685A89", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… POST /api/reservations/1/check-in → 409 {"detail": "签到窗口尚未开放"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:303](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_checkin_early_boundary[44-59-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-133 签到窗口前缘边界（minute=45；second=0；success=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-133；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 签到窗口前缘边界（minute=45；second=0；success=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, minute, second, success |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/check-in，JSON={"seat_id": 1}；本例参数：minute=45；second=0；success=True；参数：{"minute": "45", "second": "0", "success": "True"} |
| 预期结果 | r.status_code == (200 if success else 409) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.219s。 实采HTTP 4次，状态分布{"200": 3, "201": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261102080000AC9B38", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… POST /api/reservations/1/check-in → 200 {"id": 1, "reservation_no": "SR20261102080000AC9B38", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "ACTIVE"… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:303](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_checkin_early_boundary[45-0-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-134 签到后缘边界与窗内不处罚（minute=0；microsecond=0；success=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-134；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 签到后缘边界与窗内不处罚（minute=0；microsecond=0；success=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db, minute, microsecond, success |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/check-in，JSON={"seat_id": 1}；本例参数：minute=0；microsecond=0；success=True；参数：{"minute": "0", "microsecond": "0", "success": "True"} |
| 预期结果 | response.status_code == (200 if success else 409)；count(api_db, ViolationRecord) == (0 if success else 1)；s.get(Reservation, rid).status == (E.ReservationStatus.ACTIVE if success else E.ReservationStatus.EXPIRED)；service.expire_due(s) == 0 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.233s。 实采HTTP 4次，状态分布{"200": 3, "201": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261102080000938760", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… POST /api/reservations/1/check-in → 200 {"id": 1, "reservation_no": "SR20261102080000938760", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "ACTIVE"… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:315](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_checkin_late_boundary_no_penalty_inside_window[0-0-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-135 签到后缘边界与窗内不处罚（minute=15；microsecond=0；success=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-135；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 签到后缘边界与窗内不处罚（minute=15；microsecond=0；success=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db, minute, microsecond, success |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/check-in，JSON={"seat_id": 1}；本例参数：minute=15；microsecond=0；success=True；参数：{"minute": "15", "microsecond": "0", "success": "True"} |
| 预期结果 | response.status_code == (200 if success else 409)；count(api_db, ViolationRecord) == (0 if success else 1)；s.get(Reservation, rid).status == (E.ReservationStatus.ACTIVE if success else E.ReservationStatus.EXPIRED)；service.expire_due(s) == 0 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.223s。 实采HTTP 4次，状态分布{"200": 3, "201": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR202611020800002D2BB2", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… POST /api/reservations/1/check-in → 200 {"id": 1, "reservation_no": "SR202611020800002D2BB2", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "ACTIVE"… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:315](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_checkin_late_boundary_no_penalty_inside_window[15-0-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-136 签到后缘边界与窗内不处罚（minute=15；microsecond=1；success=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-136；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 签到后缘边界与窗内不处罚（minute=15；microsecond=1；success=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db, minute, microsecond, success |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/check-in，JSON={"seat_id": 1}；本例参数：minute=15；microsecond=1；success=False；参数：{"minute": "15", "microsecond": "1", "success": "False"} |
| 预期结果 | response.status_code == (200 if success else 409)；count(api_db, ViolationRecord) == (0 if success else 1)；s.get(Reservation, rid).status == (E.ReservationStatus.ACTIVE if success else E.ReservationStatus.EXPIRED)；service.expire_due(s) == 0 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.548s。 实采HTTP 4次，状态分布{"200": 2, "201": 1, "409": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261102080000422188", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… POST /api/reservations/1/check-in → 409 {"detail": "签到窗口已关闭，预约已失效并记录1次违规"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:315](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_checkin_late_boundary_no_penalty_inside_window[15-1-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-137 签到后缘边界与窗内不处罚（minute=16；microsecond=0；success=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-137；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 签到后缘边界与窗内不处罚（minute=16；microsecond=0；success=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db, minute, microsecond, success |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/check-in，JSON={"seat_id": 1}；本例参数：minute=16；microsecond=0；success=False；参数：{"minute": "16", "microsecond": "0", "success": "False"} |
| 预期结果 | response.status_code == (200 if success else 409)；count(api_db, ViolationRecord) == (0 if success else 1)；s.get(Reservation, rid).status == (E.ReservationStatus.ACTIVE if success else E.ReservationStatus.EXPIRED)；service.expire_due(s) == 0 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.247s。 实采HTTP 4次，状态分布{"200": 2, "201": 1, "409": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261102080000B73032", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… POST /api/reservations/1/check-in → 409 {"detail": "签到窗口已关闭，预约已失效并记录1次违规"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:315](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_checkin_late_boundary_no_penalty_inside_window[16-0-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-138 签到归属座位重复及状态转换

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-138；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 签到归属座位重复及状态转换；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations/1/check-in，JSON={"seat_id": 1}；POST /api/reservations/1/check-in，JSON={"seat_id": 2}；POST /api/reservations/1/check-in，JSON={"room_id": 1, "seat_code": "A01"}；POST /api/reservations/1/check-in，JSON={"room_id": 1, "seat_code": "A01"}；GET /api/seats/1；POST /api/reservations/1/cancel；PATCH /api/reservations/1/seat，JSON={"seat_id": 2} |
| 预期结果 | client.post(path, headers=actors.b, json={'seat_id': seats.a}).status_code == 404；client.post(path, headers=actors.a, json={'seat_id': seats.b}).status_code == 409；client.post(path, headers=actors.a, json=body).status_code == 200；client.post(path, headers=actors.a, json=body).status_code == 200；count(api_db, ArrivalRecord) == 1；count(api_db, ViolationRecord) == 0；client.get(f'/api/seats/{seats.a}', headers=actors.b).json()['status'] == 'in_use'；client.post(f'/api/reservations/{rid}/cancel', headers=actors.a).status_code == 409；client.patch(f'/api/reservations/{rid}/seat', headers=actors.a, json={'seat_id': seats.b}).status_code == 409 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.290s。 实采HTTP 10次，状态分布{"200": 5, "201": 1, "404": 1, "409": 3}。POST /api/reservations/1/cancel → 409 {"detail": "仅未签到的有效预约可取消"} PATCH /api/reservations/1/seat → 409 {"detail": "仅未签到的有效预约可换座"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:332](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_checkin_identity_seat_repeat_and_state_transitions`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-139 无人请求时后台释放及去重

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-139；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 无人请求时后台释放及去重；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：api_db, seats, actors, clock, monkeypatch |
| 操作/输入 | 按源函数顺序执行：service.create(s, actors.a_id, ReservationIn(**payload(seats.a)), uuid4().hex)；service.expire_due(s) |
| 预期结果 | count(api_db, ViolationRecord) == 1；completed.wait(3)；s.get(Reservation, result.id).status == E.ReservationStatus.EXPIRED；s.get(Seat, seats.a).status == E.SeatStatus.AVAILABLE；service.expire_due(s) == 0 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.191s。 实采HTTP 2次，状态分布{"200": 2}。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:353](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_unattended_expiry_worker_and_dedup`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-140 查询补扫释放并保留维护状态

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-140；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 查询补扫释放并保留维护状态；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；GET /api/reservations/current；GET /api/seats/1 |
| 预期结果 | client.get('/api/reservations/current', headers=actors.a).json() == []；client.get(f'/api/seats/{seats.a}', headers=actors.a).json()['status'] == 'maintenance'；count(api_db, ViolationRecord) == 1 |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.241s。 实采HTTP 5次，状态分布{"200": 4, "201": 1}。GET /api/reservations/current → 200 [] GET /api/seats/1 → 200 {"id": 1, "room_id": 1, "room_name": "自习室1", "code": "A01", "location": "图书馆", "floor": "1层", "facilities": null, "zone_type": "quiet", "has_power": true, "by_window": false, "accessible": false, "status": "maintenance", "qr_payload": "stu… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:382](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_lazy_expiry_and_maintenance_preserved`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-141 本人预约隔离及运维权限

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-141；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 本人预约隔离及运维权限；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, make_user, login |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；get /api/reservations/1；post /api/reservations/1/cancel；patch /api/reservations/1/seat，JSON={"seat_id": 2}；GET /api/reservations/current；GET /api/rooms；GET /api/rooms；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；其余1步请求见本例原始证据。 |
| 预期结果 | client.get('/api/reservations/current', headers=actors.b).json() == []；client.get('/api/rooms').status_code == 401；client.get('/api/rooms', headers=ops).status_code == 200；reserve(client, ops, seats.a).status_code == 403；client.get('/api/reservations/current', headers=ops).status_code == 403；client.request(method, f'/api/reservations/{rid}{suffix}', headers=actors.b, json=body).status_code == 404 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.255s。 实采HTTP 12次，状态分布{"200": 5, "201": 1, "404": 3, "401": 1, "403": 2}。POST /api/reservations → 403 {"detail": "无权限执行此操作"} GET /api/reservations/current → 403 {"detail": "无权限执行此操作"} |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:393](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_owner_privacy_and_ops_permissions`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-142 取消审计异常回滚违规及释放

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-142；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 取消审计异常回滚违规及释放；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, clock, api_db, monkeypatch |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"} |
| 预期结果 | count(api_db, ViolationRecord) == 0；s.get(Reservation, rid).status == E.ReservationStatus.RESERVED；pytest.raises(RuntimeError, match='audit unavailable') |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.217s。 实采HTTP 3次，状态分布{"200": 2, "201": 1}。POST /api/reservations → 201 {"id": 1, "reservation_no": "SR202611020800001963D0", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:414](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_cancel_audit_failure_rolls_back_violation_and_release`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-143 100线程竞争同座仅一条预约成功

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-143；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 数据库并发集成 |
| 场景和风险 | 100线程竞争同座仅一条预约成功；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 临时文件SQLite、独立Session、多线程；不是Mock也不是线上压测。 夹具：api_db, seats, clock |
| 操作/输入 | 按源函数顺序执行：service.create(s, uid, ReservationIn(**payload(seats.a)), uuid4().hex) |
| 预期结果 | sum((r is not None for r in results)) == 1；count(api_db, Reservation) == 1；not replay；exc.status_code == 409 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计1.665s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 补采实际服务调用100次：成功1、冲突99，预约ID集合[1]，首次创建1、重放0。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:431](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_100_competing_users_only_one_reservation`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-144 16线程同键重试仅一次创建

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-144；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 数据库并发集成 |
| 场景和风险 | 16线程同键重试仅一次创建；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 临时文件SQLite、独立Session、多线程；不是Mock也不是线上压测。 夹具：api_db, seats, actors |
| 操作/输入 | 按源函数顺序执行：service.create(s, actors.a_id, ReservationIn(**payload(seats.a)), key) |
| 预期结果 | len({result.id for result, _ in results}) == 1；sum((not replay for _, replay in results)) == 1；count(api_db, Reservation) == 1 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.830s。 实采HTTP 2次，状态分布{"200": 2}。 补采实际服务调用16次：成功16、冲突0，预约ID集合[1]，首次创建1、重放15。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:462](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_concurrent_retries_return_same_id`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-145 写锁繁忙503及同键恢复重试

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-145；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 接口／数据库集成 |
| 场景和风险 | 写锁繁忙503及同键恢复重试；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 本地FastAPI TestClient，依赖覆盖到每例独立迁移的临时文件SQLite；合成用户/角色/资源，后台定时任务关闭。 夹具：client, actors, seats, api_db |
| 操作/输入 | 完成所列夹具准备后，按脚本顺序执行：POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"}；POST /api/reservations，JSON={"seat_id": 1, "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00"} |
| 预期结果 | reserve(client, actors.a, seats.a, key=key).status_code == 201；response.status_code == 503；response.headers['Retry-After'] == '1' |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.671s。 实采HTTP 4次，状态分布{"200": 2, "503": 1, "201": 1}。POST /api/reservations → 503 {"detail": "预约服务繁忙，请稍后使用相同请求重试"} POST /api/reservations → 201 {"id": 1, "reservation_no": "SR20261102080000C46BBF", "user_id": 1, "room_id": 1, "room_name": "自习室1", "seat_id": 1, "seat_code": "A01", "start_time": "2026-11-02T09:00:00+08:00", "end_time": "2026-11-02T10:00:00+08:00", "status": "RESERVE… |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_reservations.py:476](../backend/tests/test_reservations.py)；`tests/test_reservations.py::test_write_lock_error_is_retryable_and_same_key_can_recover`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-146 密码长度字符类别及字节上限

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-146；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 单元（纯函数） |
| 场景和风险 | 密码长度字符类别及字节上限；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 纯函数及合成字符串；不建业务数据库。 夹具： |
| 操作/输入 | 按源函数顺序执行：password_problem('Ab1')；password_problem('abcdefgh')；password_problem('12345678')；password_problem('a' * 73)；password_problem('Demo1234') |
| 预期结果 | password_problem('Ab1') == '密码至少 8 位'；password_problem('abcdefgh') == '密码须同时包含字母和数字'；password_problem('12345678') == '密码须同时包含字母和数字'；password_problem('a' * 73) == '密码不能超过 72 字节'；password_problem('Demo1234') is None |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_units.py:18](../backend/tests/test_units.py)；`tests/test_units.py::test_password_policy_rejects_short_or_single_class`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-147 学号格式有效及非法输入

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-147；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 单元（纯函数） |
| 场景和风险 | 学号格式有效及非法输入；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 纯函数及合成字符串；不建业务数据库。 夹具： |
| 操作/输入 | 按源函数顺序执行：student_no_valid('20260001')；student_no_valid('A0000001')；student_no_valid('12')；student_no_valid('学号2026')；student_no_valid('') |
| 预期结果 | student_no_valid('20260001')；student_no_valid('A0000001')；not student_no_valid('12')；not student_no_valid('学号2026')；not student_no_valid('') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_units.py:26](../backend/tests/test_units.py)；`tests/test_units.py::test_student_no_pattern`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-148 密码哈希验证不暴露明文

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-148；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 单元（纯函数） |
| 场景和风险 | 密码哈希验证不暴露明文；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 纯函数及合成字符串；不建业务数据库。 夹具： |
| 操作/输入 | 按源函数顺序执行：hash_password('Demo1234')；verify_password('Demo1234', stored)；verify_password('Demo1235', stored)；verify_password('Demo1234', 'not-a-hash') |
| 预期结果 | stored != 'Demo1234'；verify_password('Demo1234', stored)；not verify_password('Demo1235', stored)；not verify_password('Demo1234', 'not-a-hash') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.003s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_units.py:34](../backend/tests/test_units.py)；`tests/test_units.py::test_password_hash_verifies_and_hides_plaintext`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-149 会话摘要稳定且不等于原令牌

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-149；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 单元（纯函数） |
| 场景和风险 | 会话摘要稳定且不等于原令牌；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 纯函数及合成字符串；不建业务数据库。 夹具： |
| 操作/输入 | 按源函数顺序执行：token_digest('session-token')；token_digest('session-token') |
| 预期结果 | digest == token_digest('session-token')；digest != 'session-token'；len(digest) == 64 |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_units.py:42](../backend/tests/test_units.py)；`tests/test_units.py::test_token_digest_is_stable_and_not_the_token`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-150 角色权限投影与组合

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-150；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 单元（纯函数） |
| 场景和风险 | 角色权限投影与组合；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 纯函数及合成字符串；不建业务数据库。 夹具： |
| 操作/输入 | 按源函数顺序执行：permissions_of({RoleName.USER})；permissions_of({RoleName.ADMIN})；permissions_of({RoleName.OPS})；permissions_of(set())；roles_for('stats:read')；roles_for('stats:read') |
| 预期结果 | 'room:read' in user and 'user:manage' not in user；'user:manage' in admin and 'system:backup' not in admin；'system:backup' in ops and 'room:manage' not in ops；permissions_of(set()) == set()；RoleName.ADMIN in roles_for('stats:read')；RoleName.USER not in roles_for('stats:read') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_units.py:49](../backend/tests/test_units.py)；`tests/test_units.py::test_permission_projection_matches_role_matrix`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-151 统一时钟带北京时间时区

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-151；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（纯函数） |
| 场景和风险 | 统一时钟带北京时间时区；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 纯函数及合成字符串；不建业务数据库。 夹具： |
| 操作/输入 | 按源函数顺序执行：now()；tz() |
| 预期结果 | moment.tzinfo == tz()；moment.utcoffset() == timedelta(hours=8) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/test_units.py:61](../backend/tests/test_units.py)；`tests/test_units.py::test_now_is_shanghai_aware`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-152 门禁脱敏键稳定且隐藏学号

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-152；SRS HD-15/16/30/31/52、NFR-013/014；ADR-06 |
| 层级 | 单元（纯函数） |
| 场景和风险 | 门禁脱敏键稳定且隐藏学号；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 纯函数及合成字符串；不建业务数据库。 夹具： |
| 操作/输入 | 按源函数顺序执行：user_key_for_gate('20260001')；user_key_for_gate('20260001')；user_key_for_gate('20260002') |
| 预期结果 | first == user_key_for_gate('20260001')；first != user_key_for_gate('20260002')；'20260001' not in first；len(first) == 64 |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/test_units.py:67](../backend/tests/test_units.py)；`tests/test_units.py::test_gate_user_key_does_not_expose_student_no`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-153 取消15分钟边界分类（seconds=901；late=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-153；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 取消15分钟边界分类（seconds=901；late=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, moment, service_env, seconds, late |
| 操作/输入 | 按源函数顺序执行：service.cancel(session, 7, booking.id)；本例参数：seconds=901；late=False；参数：{"seconds": "901", "late": "False"} |
| 预期结果 | result.status == E.ReservationStatus.CANCELLED；result.cancel_type == (E.CancelType.LATE if late else E.CancelType.NORMAL)；result.cancelled_at == moment；service_env._sync_seat.assert_called_once_with(session, booking.seat, moment)；service_env._restriction.assert_not_called()；service_env._record_violation.assert_called_once_with(session, booking, E.ViolationType.LATE_CANCEL, moment)；service_env._record_violation.assert_not_called() |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_cancel_reservation.py:13](../backend/tests/units/test_cancel_reservation.py)；`tests/units/test_cancel_reservation.py::test_cancel_classifies_fifteen_minute_boundary[901-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-154 取消15分钟边界分类（seconds=900；late=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-154；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 取消15分钟边界分类（seconds=900；late=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, moment, service_env, seconds, late |
| 操作/输入 | 按源函数顺序执行：service.cancel(session, 7, booking.id)；本例参数：seconds=900；late=True；参数：{"seconds": "900", "late": "True"} |
| 预期结果 | result.status == E.ReservationStatus.CANCELLED；result.cancel_type == (E.CancelType.LATE if late else E.CancelType.NORMAL)；result.cancelled_at == moment；service_env._sync_seat.assert_called_once_with(session, booking.seat, moment)；service_env._restriction.assert_not_called()；service_env._record_violation.assert_called_once_with(session, booking, E.ViolationType.LATE_CANCEL, moment)；service_env._record_violation.assert_not_called() |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_cancel_reservation.py:13](../backend/tests/units/test_cancel_reservation.py)；`tests/units/test_cancel_reservation.py::test_cancel_classifies_fifteen_minute_boundary[900-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-155 取消15分钟边界分类（seconds=899；late=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-155；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 取消15分钟边界分类（seconds=899；late=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, moment, service_env, seconds, late |
| 操作/输入 | 按源函数顺序执行：service.cancel(session, 7, booking.id)；本例参数：seconds=899；late=True；参数：{"seconds": "899", "late": "True"} |
| 预期结果 | result.status == E.ReservationStatus.CANCELLED；result.cancel_type == (E.CancelType.LATE if late else E.CancelType.NORMAL)；result.cancelled_at == moment；service_env._sync_seat.assert_called_once_with(session, booking.seat, moment)；service_env._restriction.assert_not_called()；service_env._record_violation.assert_called_once_with(session, booking, E.ViolationType.LATE_CANCEL, moment)；service_env._record_violation.assert_not_called() |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_cancel_reservation.py:13](../backend/tests/units/test_cancel_reservation.py)；`tests/units/test_cancel_reservation.py::test_cancel_classifies_fifteen_minute_boundary[899-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-156 重复取消不重复违规和通知

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-156；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 重复取消不重复违规和通知；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env |
| 操作/输入 | 按源函数顺序执行：service.cancel(session, 7, booking.id)；service.cancel(session, 7, booking.id) |
| 预期结果 | service.cancel(session, 7, booking.id) is booking；service_env.create_notification.assert_not_called()；service_env._record_violation.assert_not_called()；service_env._sync_seat.assert_not_called() |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_cancel_reservation.py:33](../backend/tests/units/test_cancel_reservation.py)；`tests/units/test_cancel_reservation.py::test_repeated_cancel_does_not_repeat_violation_or_notification`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-157 非已预约状态拒绝取消（status=<ReservationStatus.ACTIVE: 'ACTIVE'>）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-157；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 非已预约状态拒绝取消（status=<ReservationStatus.ACTIVE: 'ACTIVE'>）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env, status |
| 操作/输入 | 按源函数顺序执行：service.cancel(session, 7, booking.id)；本例参数：status=<ReservationStatus.ACTIVE: 'ACTIVE'>；参数：{"status": "<ReservationStatus.ACTIVE: 'ACTIVE'>"} |
| 预期结果 | error.value.status_code == 409；booking.status == status；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_cancel_reservation.py:47](../backend/tests/units/test_cancel_reservation.py)；`tests/units/test_cancel_reservation.py::test_cancel_rejects_non_reserved_booking[ACTIVE]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-158 非已预约状态拒绝取消（status=<ReservationStatus.EXPIRED: 'EXPIRED'>）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-158；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 非已预约状态拒绝取消（status=<ReservationStatus.EXPIRED: 'EXPIRED'>）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env, status |
| 操作/输入 | 按源函数顺序执行：service.cancel(session, 7, booking.id)；本例参数：status=<ReservationStatus.EXPIRED: 'EXPIRED'>；参数：{"status": "<ReservationStatus.EXPIRED: 'EXPIRED'>"} |
| 预期结果 | error.value.status_code == 409；booking.status == status；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_cancel_reservation.py:47](../backend/tests/units/test_cancel_reservation.py)；`tests/units/test_cancel_reservation.py::test_cancel_rejects_non_reserved_booking[EXPIRED]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-159 预约开始后拒绝取消（seconds=0）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-159；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 预约开始后拒绝取消（seconds=0）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, moment, service_env, seconds |
| 操作/输入 | 按源函数顺序执行：service.cancel(session, 7, booking.id)；本例参数：seconds=0；参数：{"seconds": "0"} |
| 预期结果 | error.value.status_code == 409；service_env._record_violation.assert_not_called()；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_cancel_reservation.py:56](../backend/tests/units/test_cancel_reservation.py)；`tests/units/test_cancel_reservation.py::test_cancel_rejects_started_booking[0]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-160 预约开始后拒绝取消（seconds=-1）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-160；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 预约开始后拒绝取消（seconds=-1）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, moment, service_env, seconds |
| 操作/输入 | 按源函数顺序执行：service.cancel(session, 7, booking.id)；本例参数：seconds=-1；参数：{"seconds": "-1"} |
| 预期结果 | error.value.status_code == 409；service_env._record_violation.assert_not_called()；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_cancel_reservation.py:56](../backend/tests/units/test_cancel_reservation.py)；`tests/units/test_cancel_reservation.py::test_cancel_rejects_started_booking[-1]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-161 换座保留起止时间

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-161；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 换座保留起止时间；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, seat, booking, service_env |
| 操作/输入 | 按源函数顺序执行：service.change_seat(session, 7, booking.id, target.id) |
| 预期结果 | result.seat_id == 12；(result.start_time, result.end_time) == original_times；service_env._sync_seat.call_count == 2；service_env._check_slot.assert_called_once_with(session, target, *original_times, 7, booking.id) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_change_seat.py:15](../backend/tests/units/test_change_seat.py)；`tests/units/test_change_seat.py::test_change_seat_preserves_reservation_times`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-162 仅未签到预约允许换座（status=<ReservationStatus.ACTIVE: 'ACTIVE'>）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-162；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 仅未签到预约允许换座（status=<ReservationStatus.ACTIVE: 'ACTIVE'>）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env, status |
| 操作/输入 | 按源函数顺序执行：service.change_seat(session, 7, booking.id, 12)；本例参数：status=<ReservationStatus.ACTIVE: 'ACTIVE'>；参数：{"status": "<ReservationStatus.ACTIVE: 'ACTIVE'>"} |
| 预期结果 | error.value.status_code == 409；booking.seat_id == 11；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_change_seat.py:31](../backend/tests/units/test_change_seat.py)；`tests/units/test_change_seat.py::test_only_reserved_booking_can_change[ACTIVE]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-163 仅未签到预约允许换座（status=<ReservationStatus.CANCELLED: 'CANCELLED'>）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-163；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 仅未签到预约允许换座（status=<ReservationStatus.CANCELLED: 'CANCELLED'>）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env, status |
| 操作/输入 | 按源函数顺序执行：service.change_seat(session, 7, booking.id, 12)；本例参数：status=<ReservationStatus.CANCELLED: 'CANCELLED'>；参数：{"status": "<ReservationStatus.CANCELLED: 'CANCELLED'>"} |
| 预期结果 | error.value.status_code == 409；booking.seat_id == 11；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_change_seat.py:31](../backend/tests/units/test_change_seat.py)；`tests/units/test_change_seat.py::test_only_reserved_booking_can_change[CANCELLED]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-164 已超窗预约拒绝换座

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-164；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 已超窗预约拒绝换座；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, moment, service_env |
| 操作/输入 | 按源函数顺序执行：service.change_seat(session, 7, booking.id, 12) |
| 预期结果 | error.value.status_code == 409；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_change_seat.py:39](../backend/tests/units/test_change_seat.py)；`tests/units/test_change_seat.py::test_overdue_booking_cannot_change`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-165 目标冲突时原座位不变

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-165；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 目标冲突时原座位不变；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env |
| 操作/输入 | 按源函数顺序执行：service.change_seat(session, 7, booking.id, 12) |
| 预期结果 | booking.seat is original；service_env._sync_seat.assert_not_called()；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_change_seat.py:46](../backend/tests/units/test_change_seat.py)；`tests/units/test_change_seat.py::test_conflicting_target_preserves_original_seat`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-166 换座请求拒绝修改时间字段

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-166；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 换座请求拒绝修改时间字段；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：moment |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_change_request_rejects_time_modification，进行异常、返回值或Mock调用核验。 |
| 预期结果 | pytest.raises(ValidationError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_change_seat.py:55](../backend/tests/units/test_change_seat.py)；`tests/units/test_change_seat.py::test_change_request_rejects_time_modification`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-167 扫码及编号在签到窗口内成功（offset=-900；arrival_status=<ArrivalStatus.EARLY: 'early'>；use_code=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-167；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 扫码及编号在签到窗口内成功（offset=-900；arrival_status=<ArrivalStatus.EARLY: 'early'>；use_code=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, booking, moment, service_env, use_code, offset, arrival_status |
| 操作/输入 | 按源函数顺序执行：service.check_in(session, 7, booking.id, body)；本例参数：offset=-900；arrival_status=<ArrivalStatus.EARLY: 'early'>；use_code=False；参数：{"offset": "-900", "arrival_status": "<ArrivalStatus.EARLY: 'early'>", "use_code": "False"} |
| 预期结果 | result.status == E.ReservationStatus.ACTIVE；arrival.arrived_at == moment；arrival.arrival_method == E.ArrivalMethod.QR；arrival.arrival_status == arrival_status；service_env._sync_seat.assert_called_once_with(session, booking.seat, moment) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_qr_checkin_within_window[-900-early-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-168 扫码及编号在签到窗口内成功（offset=-900；arrival_status=<ArrivalStatus.EARLY: 'early'>；use_code=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-168；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 扫码及编号在签到窗口内成功（offset=-900；arrival_status=<ArrivalStatus.EARLY: 'early'>；use_code=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, booking, moment, service_env, use_code, offset, arrival_status |
| 操作/输入 | 按源函数顺序执行：service.check_in(session, 7, booking.id, body)；本例参数：offset=-900；arrival_status=<ArrivalStatus.EARLY: 'early'>；use_code=True；参数：{"offset": "-900", "arrival_status": "<ArrivalStatus.EARLY: 'early'>", "use_code": "True"} |
| 预期结果 | result.status == E.ReservationStatus.ACTIVE；arrival.arrived_at == moment；arrival.arrival_method == E.ArrivalMethod.QR；arrival.arrival_status == arrival_status；service_env._sync_seat.assert_called_once_with(session, booking.seat, moment) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_qr_checkin_within_window[-900-early-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-169 扫码及编号在签到窗口内成功（offset=0；arrival_status=<ArrivalStatus.ON_TIME: 'on_time'>；use_code=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-169；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 扫码及编号在签到窗口内成功（offset=0；arrival_status=<ArrivalStatus.ON_TIME: 'on_time'>；use_code=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, booking, moment, service_env, use_code, offset, arrival_status |
| 操作/输入 | 按源函数顺序执行：service.check_in(session, 7, booking.id, body)；本例参数：offset=0；arrival_status=<ArrivalStatus.ON_TIME: 'on_time'>；use_code=False；参数：{"offset": "0", "arrival_status": "<ArrivalStatus.ON_TIME: 'on_time'>", "use_code": "False"} |
| 预期结果 | result.status == E.ReservationStatus.ACTIVE；arrival.arrived_at == moment；arrival.arrival_method == E.ArrivalMethod.QR；arrival.arrival_status == arrival_status；service_env._sync_seat.assert_called_once_with(session, booking.seat, moment) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_qr_checkin_within_window[0-on_time-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-170 扫码及编号在签到窗口内成功（offset=0；arrival_status=<ArrivalStatus.ON_TIME: 'on_time'>；use_code=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-170；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 扫码及编号在签到窗口内成功（offset=0；arrival_status=<ArrivalStatus.ON_TIME: 'on_time'>；use_code=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, booking, moment, service_env, use_code, offset, arrival_status |
| 操作/输入 | 按源函数顺序执行：service.check_in(session, 7, booking.id, body)；本例参数：offset=0；arrival_status=<ArrivalStatus.ON_TIME: 'on_time'>；use_code=True；参数：{"offset": "0", "arrival_status": "<ArrivalStatus.ON_TIME: 'on_time'>", "use_code": "True"} |
| 预期结果 | result.status == E.ReservationStatus.ACTIVE；arrival.arrived_at == moment；arrival.arrival_method == E.ArrivalMethod.QR；arrival.arrival_status == arrival_status；service_env._sync_seat.assert_called_once_with(session, booking.seat, moment) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_qr_checkin_within_window[0-on_time-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-171 扫码及编号在签到窗口内成功（offset=900；arrival_status=<ArrivalStatus.LATE: 'late'>；use_code=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-171；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 扫码及编号在签到窗口内成功（offset=900；arrival_status=<ArrivalStatus.LATE: 'late'>；use_code=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, booking, moment, service_env, use_code, offset, arrival_status |
| 操作/输入 | 按源函数顺序执行：service.check_in(session, 7, booking.id, body)；本例参数：offset=900；arrival_status=<ArrivalStatus.LATE: 'late'>；use_code=False；参数：{"offset": "900", "arrival_status": "<ArrivalStatus.LATE: 'late'>", "use_code": "False"} |
| 预期结果 | result.status == E.ReservationStatus.ACTIVE；arrival.arrived_at == moment；arrival.arrival_method == E.ArrivalMethod.QR；arrival.arrival_status == arrival_status；service_env._sync_seat.assert_called_once_with(session, booking.seat, moment) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.003s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_qr_checkin_within_window[900-late-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-172 扫码及编号在签到窗口内成功（offset=900；arrival_status=<ArrivalStatus.LATE: 'late'>；use_code=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-172；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 扫码及编号在签到窗口内成功（offset=900；arrival_status=<ArrivalStatus.LATE: 'late'>；use_code=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, booking, moment, service_env, use_code, offset, arrival_status |
| 操作/输入 | 按源函数顺序执行：service.check_in(session, 7, booking.id, body)；本例参数：offset=900；arrival_status=<ArrivalStatus.LATE: 'late'>；use_code=True；参数：{"offset": "900", "arrival_status": "<ArrivalStatus.LATE: 'late'>", "use_code": "True"} |
| 预期结果 | result.status == E.ReservationStatus.ACTIVE；arrival.arrived_at == moment；arrival.arrival_method == E.ArrivalMethod.QR；arrival.arrival_status == arrival_status；service_env._sync_seat.assert_called_once_with(session, booking.seat, moment) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:20](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_qr_checkin_within_window[900-late-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-173 扫码座位必须匹配本人预约

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-173；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 扫码座位必须匹配本人预约；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env |
| 操作/输入 | 按源函数顺序执行：service.check_in(session, 7, booking.id, CheckInIn(seat_id=999)) |
| 预期结果 | error.value.status_code == 409；booking.status == E.ReservationStatus.RESERVED；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:37](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_qr_seat_must_match_booking`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-174 窗口开放前拒绝签到

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-174；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 窗口开放前拒绝签到；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env |
| 操作/输入 | 按源函数顺序执行：service.check_in(session, 7, booking.id, CheckInIn(seat_id=11)) |
| 预期结果 | error.value.status_code == 409；booking.status == E.ReservationStatus.RESERVED；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:44](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_checkin_before_window_fails`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-175 重复扫码不重复签到

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-175；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 重复扫码不重复签到；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env |
| 操作/输入 | 按源函数顺序执行：service.check_in(session, 7, booking.id, CheckInIn(seat_id=11)) |
| 预期结果 | service.check_in(session, 7, booking.id, CheckInIn(seat_id=11)) is booking；service_env._sync_seat.assert_not_called() |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:51](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_repeated_qr_checkin_is_idempotent`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-176 未签到宽限截止整秒判定（offset=900；expected=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-176；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 未签到宽限截止整秒判定（offset=900；expected=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：booking, offset, expected |
| 操作/输入 | 按源函数顺序执行：service._overdue(booking, booking.start_time + timedelta(seconds=offset), 15)；本例参数：offset=900；expected=False；参数：{"offset": "900", "expected": "False"} |
| 预期结果 | service._overdue(booking, booking.start_time + timedelta(seconds=offset), 15) is expected |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:58](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_no_show_grace_boundary[900-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-177 未签到宽限截止整秒判定（offset=901；expected=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-177；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 未签到宽限截止整秒判定（offset=901；expected=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：booking, offset, expected |
| 操作/输入 | 按源函数顺序执行：service._overdue(booking, booking.start_time + timedelta(seconds=offset), 15)；本例参数：offset=901；expected=True；参数：{"offset": "901", "expected": "True"} |
| 预期结果 | service._overdue(booking, booking.start_time + timedelta(seconds=offset), 15) is expected |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:58](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_no_show_grace_boundary[901-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-178 预约结束优先于未签到宽限

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-178；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 预约结束优先于未签到宽限；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：booking |
| 操作/输入 | 按源函数顺序执行：service._overdue(booking, booking.end_time, 15) |
| 预期结果 | service._overdue(booking, booking.end_time, 15) is True |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:62](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_booking_end_is_overdue_even_within_grace`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-179 超窗签到触发失效处理

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-179；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 超窗签到触发失效处理；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, booking, moment, service_env |
| 操作/输入 | 按源函数顺序执行：service.check_in(session, 7, booking.id, CheckInIn(seat_id=11)) |
| 预期结果 | error.value.status_code == 409；expire.assert_called_once_with(session, booking, moment)；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:67](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_late_checkin_expires_booking`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-180 失效记录未到场并释放座位

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-180；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 失效记录未到场并释放座位；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, booking, moment |
| 操作/输入 | 按源函数顺序执行：service._expire_one(session, booking, moment) |
| 预期结果 | booking.status == E.ReservationStatus.EXPIRED；booking.expire_reason == 'no_show'；booking.seat.status == E.SeatStatus.AVAILABLE；violation.assert_called_once_with(session, booking, E.ViolationType.NO_SHOW, moment) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:77](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_expiry_records_no_show_and_releases_seat`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-181 失效释放保留座位维护状态

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-181；SRS NFR-008/012；ADR-09 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 失效释放保留座位维护状态；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, booking, moment |
| 操作/输入 | 按源函数顺序执行：service._expire_one(session, booking, moment) |
| 预期结果 | booking.seat.status == E.SeatStatus.MAINTENANCE |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:91](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_expiry_preserves_maintenance_status`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-182 到期扫描处理候选预约（count=0）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-182；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 到期扫描处理候选预约（count=0）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, booking, moment, count |
| 操作/输入 | 按源函数顺序执行：service._expire_due(session, moment)；本例参数：count=0；参数：{"count": "0"} |
| 预期结果 | service._expire_due(session, moment) == count；[call.args for call in expire.call_args_list] == [(session, item, moment) for item in candidates] |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:99](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_expiry_sweep_processes_candidates[0]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-183 到期扫描处理候选预约（count=2）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-183；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 到期扫描处理候选预约（count=2）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, booking, moment, count |
| 操作/输入 | 按源函数顺序执行：service._expire_due(session, moment)；本例参数：count=2；参数：{"count": "2"} |
| 预期结果 | service._expire_due(session, moment) == count；[call.args for call in expire.call_args_list] == [(session, item, moment) for item in candidates] |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_checkin_expiry.py:99](../backend/tests/units/test_checkin_expiry.py)；`tests/units/test_checkin_expiry.py::test_expiry_sweep_processes_candidates[2]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-184 同键同载荷重放不再写入

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-184；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 同键同载荷重放不再写入；现有断言通过不等于全部业务需求验收。 本文件仅Mock事务/错误分支，不证明真实并发。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env |
| 操作/输入 | 按源函数顺序执行：service.create(session, 7, body, 'unit-key')；service.create(session, 7, body, 'unit-key') |
| 预期结果 | replay is False；result is first；replay is True；session.add.assert_not_called()；service_env._check_slot.assert_not_called()；service_env.create_notification.assert_not_called() |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_concurrency_idempotency.py:14](../backend/tests/units/test_concurrency_idempotency.py)；`tests/units/test_concurrency_idempotency.py::test_same_key_and_payload_replays_without_writing`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-185 幂等键不得跨用户或载荷复用（other_user=True；other_payload=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-185；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 幂等键不得跨用户或载荷复用（other_user=True；other_payload=False）；现有断言通过不等于全部业务需求验收。 本文件仅Mock事务/错误分支，不证明真实并发。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env, other_user, other_payload |
| 操作/输入 | 按源函数顺序执行：service.create(session, 7, body, 'unit-key')；service.create(session, 8 if other_user else 7, body, 'unit-key')；本例参数：other_user=True；other_payload=False；参数：{"other_user": "True", "other_payload": "False"} |
| 预期结果 | error.value.status_code == 409；session.add.assert_not_called()；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_concurrency_idempotency.py:33](../backend/tests/units/test_concurrency_idempotency.py)；`tests/units/test_concurrency_idempotency.py::test_key_cannot_be_reused_for_different_request[True-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-186 幂等键不得跨用户或载荷复用（other_user=False；other_payload=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-186；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 幂等键不得跨用户或载荷复用（other_user=False；other_payload=True）；现有断言通过不等于全部业务需求验收。 本文件仅Mock事务/错误分支，不证明真实并发。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, booking, service_env, other_user, other_payload |
| 操作/输入 | 按源函数顺序执行：service.create(session, 7, body, 'unit-key')；service.create(session, 8 if other_user else 7, body, 'unit-key')；本例参数：other_user=False；other_payload=True；参数：{"other_user": "False", "other_payload": "True"} |
| 预期结果 | error.value.status_code == 409；session.add.assert_not_called()；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_concurrency_idempotency.py:33](../backend/tests/units/test_concurrency_idempotency.py)；`tests/units/test_concurrency_idempotency.py::test_key_cannot_be_reused_for_different_request[False-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-187 业务事务请求立即写锁

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-187；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 业务事务请求立即写锁；现有断言通过不等于全部业务需求验收。 本文件仅Mock事务/错误分支，不证明真实并发。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session |
| 操作/输入 | 按源函数顺序执行：service.write_transaction(session) |
| 预期结果 | actual is session；factory.assert_called_once_with(session.get_bind.return_value, expire_on_commit=False, autoflush=False)；transaction.assert_called_once_with(session, immediate=True) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_concurrency_idempotency.py:48](../backend/tests/units/test_concurrency_idempotency.py)；`tests/units/test_concurrency_idempotency.py::test_write_transaction_requests_immediate_lock`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-188 锁忙及唯一异常映射业务错误（failure=OperationalError('(builtins.Exception) database is locked')；code=503）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-188；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 锁忙及唯一异常映射业务错误（failure=OperationalError('(builtins.Exception) database is locked')；code=503）；现有断言通过不等于全部业务需求验收。 本文件仅Mock事务/错误分支，不证明真实并发。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, failure, code |
| 操作/输入 | 按源函数顺序执行：service.write_transaction(session)；本例参数：failure=OperationalError('(builtins.Exception) database is locked')；code=503；参数：{"failure": "OperationalError('(builtins.Exception) database is locked')", "code": "503"} |
| 预期结果 | error.value.status_code == code；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.006s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_concurrency_idempotency.py:71](../backend/tests/units/test_concurrency_idempotency.py)；`tests/units/test_concurrency_idempotency.py::test_write_errors_become_booking_errors[failure0-503]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-189 锁忙及唯一异常映射业务错误（failure=OperationalError('(builtins.Exception) database is busy')；code=503）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-189；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 锁忙及唯一异常映射业务错误（failure=OperationalError('(builtins.Exception) database is busy')；code=503）；现有断言通过不等于全部业务需求验收。 本文件仅Mock事务/错误分支，不证明真实并发。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, failure, code |
| 操作/输入 | 按源函数顺序执行：service.write_transaction(session)；本例参数：failure=OperationalError('(builtins.Exception) database is busy')；code=503；参数：{"failure": "OperationalError('(builtins.Exception) database is busy')", "code": "503"} |
| 预期结果 | error.value.status_code == code；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_concurrency_idempotency.py:71](../backend/tests/units/test_concurrency_idempotency.py)；`tests/units/test_concurrency_idempotency.py::test_write_errors_become_booking_errors[failure1-503]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-190 锁忙及唯一异常映射业务错误（failure=IntegrityError('(builtins.Exception) unique constraint')；code=409）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-190；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 锁忙及唯一异常映射业务错误（failure=IntegrityError('(builtins.Exception) unique constraint')；code=409）；现有断言通过不等于全部业务需求验收。 本文件仅Mock事务/错误分支，不证明真实并发。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, failure, code |
| 操作/输入 | 按源函数顺序执行：service.write_transaction(session)；本例参数：failure=IntegrityError('(builtins.Exception) unique constraint')；code=409；参数：{"failure": "IntegrityError('(builtins.Exception) unique constraint')", "code": "409"} |
| 预期结果 | error.value.status_code == code；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_concurrency_idempotency.py:71](../backend/tests/units/test_concurrency_idempotency.py)；`tests/units/test_concurrency_idempotency.py::test_write_errors_become_booking_errors[failure2-409]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-191 无关数据库异常原样抛出

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-191；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 无关数据库异常原样抛出；现有断言通过不等于全部业务需求验收。 本文件仅Mock事务/错误分支，不证明真实并发。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session |
| 操作/输入 | 按源函数顺序执行：service.write_transaction(session) |
| 预期结果 | error.value is failure；pytest.raises(OperationalError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [backend/tests/units/test_concurrency_idempotency.py:79](../backend/tests/units/test_concurrency_idempotency.py)；`tests/units/test_concurrency_idempotency.py::test_unrelated_database_error_is_preserved`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-192 创建写入预约及到达占位

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-192；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 创建写入预约及到达占位；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, seat, booking, service_env |
| 操作/输入 | 按源函数顺序执行：service.create(session, 7, body, 'unit-create') |
| 预期结果 | replay is False；isinstance(result, Reservation)；(result.user_id, result.seat, result.start_time, result.end_time) == (7, seat, body.start_time, body.end_time)；any((isinstance(item, ArrivalRecord) and item.seat_id == seat.id for item in added))；service_env._check_slot.assert_called_once_with(session, seat, body.start_time, body.end_time, 7)；service_env.create_notification.assert_called_once() |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_create_reservation.py:14](../backend/tests/units/test_create_reservation.py)；`tests/units/test_create_reservation.py::test_create_saves_booking_and_arrival`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-193 创建拒绝过去及超提前期开始时间（offset=datetime.timedelta(days=-1, seconds=86340)）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-193；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 创建拒绝过去及超提前期开始时间（offset=datetime.timedelta(days=-1, seconds=86340)）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, seat, moment, service_env, offset |
| 操作/输入 | 按源函数顺序执行：service.create(session, 7, body, None)；本例参数：offset=datetime.timedelta(days=-1, seconds=86340)；参数：{"offset": "datetime.timedelta(days=-1, seconds=86340)"} |
| 预期结果 | error.value.status_code == 422；session.add.assert_not_called()；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_create_reservation.py:33](../backend/tests/units/test_create_reservation.py)；`tests/units/test_create_reservation.py::test_create_rejects_past_or_too_distant_start[offset0]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-194 创建拒绝过去及超提前期开始时间（offset=datetime.timedelta(days=2)）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-194；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 创建拒绝过去及超提前期开始时间（offset=datetime.timedelta(days=2)）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, seat, moment, service_env, offset |
| 操作/输入 | 按源函数顺序执行：service.create(session, 7, body, None)；本例参数：offset=datetime.timedelta(days=2)；参数：{"offset": "datetime.timedelta(days=2)"} |
| 预期结果 | error.value.status_code == 422；session.add.assert_not_called()；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_create_reservation.py:33](../backend/tests/units/test_create_reservation.py)；`tests/units/test_create_reservation.py::test_create_rejects_past_or_too_distant_start[offset1]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-195 时段检查拒绝关闭或重叠冲突（covered=False；overlaps=False；own_conflict=False；code=422）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-195；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 时段检查拒绝关闭或重叠冲突（covered=False；overlaps=False；own_conflict=False；code=422）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, booking, covered, overlaps, own_conflict, code |
| 操作/输入 | 按源函数顺序执行：service._check_slot(session, seat, booking.start_time, booking.end_time, 7)；本例参数：covered=False；overlaps=False；own_conflict=False；code=422；参数：{"covered": "False", "overlaps": "False", "own_conflict": "False", "code": "422"} |
| 预期结果 | error.value.status_code == code；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_create_reservation.py:46](../backend/tests/units/test_create_reservation.py)；`tests/units/test_create_reservation.py::test_slot_rejects_closed_hours_or_conflicts[False-False-False-422]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-196 时段检查拒绝关闭或重叠冲突（covered=True；overlaps=True；own_conflict=False；code=409）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-196；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 时段检查拒绝关闭或重叠冲突（covered=True；overlaps=True；own_conflict=False；code=409）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, booking, covered, overlaps, own_conflict, code |
| 操作/输入 | 按源函数顺序执行：service._check_slot(session, seat, booking.start_time, booking.end_time, 7)；本例参数：covered=True；overlaps=True；own_conflict=False；code=409；参数：{"covered": "True", "overlaps": "True", "own_conflict": "False", "code": "409"} |
| 预期结果 | error.value.status_code == code；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_create_reservation.py:46](../backend/tests/units/test_create_reservation.py)；`tests/units/test_create_reservation.py::test_slot_rejects_closed_hours_or_conflicts[True-True-False-409]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-197 时段检查拒绝关闭或重叠冲突（covered=True；overlaps=False；own_conflict=True；code=409）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-197；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 时段检查拒绝关闭或重叠冲突（covered=True；overlaps=False；own_conflict=True；code=409）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, booking, covered, overlaps, own_conflict, code |
| 操作/输入 | 按源函数顺序执行：service._check_slot(session, seat, booking.start_time, booking.end_time, 7)；本例参数：covered=True；overlaps=False；own_conflict=True；code=409；参数：{"covered": "True", "overlaps": "False", "own_conflict": "True", "code": "409"} |
| 预期结果 | error.value.status_code == code；pytest.raises(BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.003s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_create_reservation.py:46](../backend/tests/units/test_create_reservation.py)；`tests/units/test_create_reservation.py::test_slot_rejects_closed_hours_or_conflicts[True-False-True-409]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-198 换座时冲突检查排除本预约

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-198；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 换座时冲突检查排除本预约；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, booking |
| 操作/输入 | 按源函数顺序执行：service._check_slot(session, seat, booking.start_time, booking.end_time, 7, booking.id) |
| 预期结果 | 按测试函数中的异常期望及调用断言核验，见源代码。 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_create_reservation.py:57](../backend/tests/units/test_create_reservation.py)；`tests/units/test_create_reservation.py::test_slot_ignores_the_booking_being_modified`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-199 模型拒绝零负或跨日区间（minutes=0）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-199；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 模型拒绝零负或跨日区间（minutes=0）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：moment, minutes |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_invalid_time_range_is_rejected，进行异常、返回值或Mock调用核验。；本例参数：minutes=0；参数：{"minutes": "0"} |
| 预期结果 | pytest.raises(ValidationError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_create_reservation.py:64](../backend/tests/units/test_create_reservation.py)；`tests/units/test_create_reservation.py::test_invalid_time_range_is_rejected[0]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-200 模型拒绝零负或跨日区间（minutes=-1）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-200；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 模型拒绝零负或跨日区间（minutes=-1）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：moment, minutes |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_invalid_time_range_is_rejected，进行异常、返回值或Mock调用核验。；本例参数：minutes=-1；参数：{"minutes": "-1"} |
| 预期结果 | pytest.raises(ValidationError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_create_reservation.py:64](../backend/tests/units/test_create_reservation.py)；`tests/units/test_create_reservation.py::test_invalid_time_range_is_rejected[-1]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-201 模型拒绝零负或跨日区间（minutes=1440）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-201；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 模型拒绝零负或跨日区间（minutes=1440）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：moment, minutes |
| 操作/输入 | 按源函数顺序执行：使用所列夹具执行 test_invalid_time_range_is_rejected，进行异常、返回值或Mock调用核验。；本例参数：minutes=1440；参数：{"minutes": "1440"} |
| 预期结果 | pytest.raises(ValidationError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.000s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_create_reservation.py:64](../backend/tests/units/test_create_reservation.py)；`tests/units/test_create_reservation.py::test_invalid_time_range_is_rejected[1440]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-202 合法无冲突时段通过检查

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-202；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 合法无冲突时段通过检查；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, booking |
| 操作/输入 | 按源函数顺序执行：service._check_slot(session, seat, booking.start_time, booking.end_time, 7) |
| 预期结果 | 按测试函数中的异常期望及调用断言核验，见源代码。 |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_create_reservation.py:69](../backend/tests/units/test_create_reservation.py)；`tests/units/test_create_reservation.py::test_valid_slot_passes`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-203 房间列表包含位置容量开放时间

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-203；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 房间列表包含位置容量开放时间；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, moment |
| 操作/输入 | 按源函数顺序执行：catalog.room_list(session, moment.date()) |
| 预期结果 | len(result) == 1；(room.id, room.name, room.floor, room.capacity) == (1, '一号自习室', '3', 20)；room.date == moment.date()；(room.opening_hours[0].open_time, room.opening_hours[0].close_time) == (time(8), time(22)) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_room_search.py:11](../backend/tests/units/test_room_search.py)；`tests/units/test_room_search.py::test_room_list_contains_room_information`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-204 无房间返回空列表

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-204；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 无房间返回空列表；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, moment |
| 操作/输入 | 按源函数顺序执行：catalog.room_list(session, moment.date()) |
| 预期结果 | catalog.room_list(session, moment.date()) == [] |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_room_search.py:26](../backend/tests/units/test_room_search.py)；`tests/units/test_room_search.py::test_empty_room_list`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-205 搜索不存在房间返回404

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-205；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 搜索不存在房间返回404；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, moment |
| 操作/输入 | 按源函数顺序执行：catalog.seat_list(session, moment, None, 999, None, False) |
| 预期结果 | error.value.status_code == 404；session.scalars.assert_not_called()；pytest.raises(catalog.BookingError) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_room_search.py:30](../backend/tests/units/test_room_search.py)；`tests/units/test_room_search.py::test_search_unknown_room_fails`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-206 搜索仅可用座位过滤（available_only=False；expected=[11, 12]）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-206；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 搜索仅可用座位过滤（available_only=False；expected=[11, 12]）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, moment, available_only, expected |
| 操作/输入 | 按源函数顺序执行：catalog.seat_list(session, moment, None, None, None, available_only)；本例参数：available_only=False；expected=[11, 12]；参数：{"available_only": "False", "expected": "[11, 12]"} |
| 预期结果 | [item.id for item in result] == expected |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_room_search.py:39](../backend/tests/units/test_room_search.py)；`tests/units/test_room_search.py::test_search_available_only[False-expected0]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-207 搜索仅可用座位过滤（available_only=True；expected=[11]）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-207；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 搜索仅可用座位过滤（available_only=True；expected=[11]）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, moment, available_only, expected |
| 操作/输入 | 按源函数顺序执行：catalog.seat_list(session, moment, None, None, None, available_only)；本例参数：available_only=True；expected=[11]；参数：{"available_only": "True", "expected": "[11]"} |
| 预期结果 | [item.id for item in result] == expected |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_room_search.py:39](../backend/tests/units/test_room_search.py)；`tests/units/test_room_search.py::test_search_available_only[True-expected1]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-208 搜索生成房间区域设施筛选条件（flag=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-208；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 搜索生成房间区域设施筛选条件（flag=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, seat, moment, flag |
| 操作/输入 | 按源函数顺序执行：catalog.seat_list(session, moment, None, 1, E.ZoneType.QUIET, False, has_power=flag, by_window=flag, accessible=flag)；本例参数：flag=True；参数：{"flag": "True"} |
| 预期结果 | query.compile().params['room_id_1'] == 1；query.compile().params['zone_type_1'] == E.ZoneType.QUIET；f"seats.{field} IS {('true' if flag else 'false')}" in sql |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.004s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_room_search.py:57](../backend/tests/units/test_room_search.py)；`tests/units/test_room_search.py::test_search_passes_room_zone_and_facility_filters[True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-209 搜索生成房间区域设施筛选条件（flag=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-209；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 搜索生成房间区域设施筛选条件（flag=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, seat, moment, flag |
| 操作/输入 | 按源函数顺序执行：catalog.seat_list(session, moment, None, 1, E.ZoneType.QUIET, False, has_power=flag, by_window=flag, accessible=flag)；本例参数：flag=False；参数：{"flag": "False"} |
| 预期结果 | query.compile().params['room_id_1'] == 1；query.compile().params['zone_type_1'] == E.ZoneType.QUIET；f"seats.{field} IS {('true' if flag else 'false')}" in sql |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.003s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_room_search.py:57](../backend/tests/units/test_room_search.py)；`tests/units/test_room_search.py::test_search_passes_room_zone_and_facility_filters[False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-210 维护关闭停用座位保持原状态（status=<SeatStatus.MAINTENANCE: 'maintenance'>）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-210；SRS NFR-008/012；ADR-09 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 维护关闭停用座位保持原状态（status=<SeatStatus.MAINTENANCE: 'maintenance'>）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, seat, moment, status |
| 操作/输入 | 按源函数顺序执行：catalog.seat_status(session, seat, moment)；本例参数：status=<SeatStatus.MAINTENANCE: 'maintenance'>；参数：{"status": "<SeatStatus.MAINTENANCE: 'maintenance'>"} |
| 预期结果 | catalog.seat_status(session, seat, moment) == status；session.scalars.assert_not_called() |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_seat_detail.py:12](../backend/tests/units/test_seat_detail.py)；`tests/units/test_seat_detail.py::test_blocked_seat_keeps_status[maintenance]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-211 维护关闭停用座位保持原状态（status=<SeatStatus.CLOSED: 'closed'>）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-211；SRS NFR-008/012；ADR-09 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 维护关闭停用座位保持原状态（status=<SeatStatus.CLOSED: 'closed'>）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, seat, moment, status |
| 操作/输入 | 按源函数顺序执行：catalog.seat_status(session, seat, moment)；本例参数：status=<SeatStatus.CLOSED: 'closed'>；参数：{"status": "<SeatStatus.CLOSED: 'closed'>"} |
| 预期结果 | catalog.seat_status(session, seat, moment) == status；session.scalars.assert_not_called() |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_seat_detail.py:12](../backend/tests/units/test_seat_detail.py)；`tests/units/test_seat_detail.py::test_blocked_seat_keeps_status[closed]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-212 维护关闭停用座位保持原状态（status=<SeatStatus.DISABLED: 'disabled'>）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-212；SRS NFR-008/012；ADR-09 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 维护关闭停用座位保持原状态（status=<SeatStatus.DISABLED: 'disabled'>）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：session, seat, moment, status |
| 操作/输入 | 按源函数顺序执行：catalog.seat_status(session, seat, moment)；本例参数：status=<SeatStatus.DISABLED: 'disabled'>；参数：{"status": "<SeatStatus.DISABLED: 'disabled'>"} |
| 预期结果 | catalog.seat_status(session, seat, moment) == status；session.scalars.assert_not_called() |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_seat_detail.py:12](../backend/tests/units/test_seat_detail.py)；`tests/units/test_seat_detail.py::test_blocked_seat_keeps_status[disabled]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-213 房间关闭或非开放时间显示关闭（room_open=False；covered=True）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-213；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 房间关闭或非开放时间显示关闭（room_open=False；covered=True）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, moment, room_open, covered |
| 操作/输入 | 按源函数顺序执行：catalog.seat_status(session, seat, moment)；本例参数：room_open=False；covered=True；参数：{"room_open": "False", "covered": "True"} |
| 预期结果 | catalog.seat_status(session, seat, moment) == E.SeatStatus.CLOSED |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_seat_detail.py:19](../backend/tests/units/test_seat_detail.py)；`tests/units/test_seat_detail.py::test_closed_room_or_outside_opening_hours[False-True]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-214 房间关闭或非开放时间显示关闭（room_open=True；covered=False）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-214；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 房间关闭或非开放时间显示关闭（room_open=True；covered=False）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, moment, room_open, covered |
| 操作/输入 | 按源函数顺序执行：catalog.seat_status(session, seat, moment)；本例参数：room_open=True；covered=False；参数：{"room_open": "True", "covered": "False"} |
| 预期结果 | catalog.seat_status(session, seat, moment) == E.SeatStatus.CLOSED |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_seat_detail.py:19](../backend/tests/units/test_seat_detail.py)；`tests/units/test_seat_detail.py::test_closed_room_or_outside_opening_hours[True-False]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-215 有效预约映射座位实时状态（status=None；expected=<SeatStatus.AVAILABLE: 'available'>）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-215；SRS NFR-008/012；ADR-09 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 有效预约映射座位实时状态（status=None；expected=<SeatStatus.AVAILABLE: 'available'>）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, booking, moment, status, expected |
| 操作/输入 | 按源函数顺序执行：catalog.seat_status(session, seat, moment)；本例参数：status=None；expected=<SeatStatus.AVAILABLE: 'available'>；参数：{"status": "None", "expected": "<SeatStatus.AVAILABLE: 'available'>"} |
| 预期结果 | catalog.seat_status(session, seat, moment) == expected |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_seat_detail.py:36](../backend/tests/units/test_seat_detail.py)；`tests/units/test_seat_detail.py::test_current_booking_determines_status[None-available]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-216 有效预约映射座位实时状态（status=<ReservationStatus.RESERVED: 'RESERVED'>；expected=<SeatStatus.RESERVED: 'reserved'>）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-216；SRS NFR-008/012；ADR-09 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 有效预约映射座位实时状态（status=<ReservationStatus.RESERVED: 'RESERVED'>；expected=<SeatStatus.RESERVED: 'reserved'>）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, booking, moment, status, expected |
| 操作/输入 | 按源函数顺序执行：catalog.seat_status(session, seat, moment)；本例参数：status=<ReservationStatus.RESERVED: 'RESERVED'>；expected=<SeatStatus.RESERVED: 'reserved'>；参数：{"status": "<ReservationStatus.RESERVED: 'RESERVED'>", "expected": "<SeatStatus.RESERVED: 'reserved'>"} |
| 预期结果 | catalog.seat_status(session, seat, moment) == expected |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_seat_detail.py:36](../backend/tests/units/test_seat_detail.py)；`tests/units/test_seat_detail.py::test_current_booking_determines_status[RESERVED-reserved]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-217 有效预约映射座位实时状态（status=<ReservationStatus.ACTIVE: 'ACTIVE'>；expected=<SeatStatus.IN_USE: 'in_use'>）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-217；SRS NFR-008/012；ADR-09 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 有效预约映射座位实时状态（status=<ReservationStatus.ACTIVE: 'ACTIVE'>；expected=<SeatStatus.IN_USE: 'in_use'>）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, booking, moment, status, expected |
| 操作/输入 | 按源函数顺序执行：catalog.seat_status(session, seat, moment)；本例参数：status=<ReservationStatus.ACTIVE: 'ACTIVE'>；expected=<SeatStatus.IN_USE: 'in_use'>；参数：{"status": "<ReservationStatus.ACTIVE: 'ACTIVE'>", "expected": "<SeatStatus.IN_USE: 'in_use'>"} |
| 预期结果 | catalog.seat_status(session, seat, moment) == expected |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.002s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_seat_detail.py:36](../backend/tests/units/test_seat_detail.py)；`tests/units/test_seat_detail.py::test_current_booking_determines_status[ACTIVE-in_use]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-218 有效预约映射座位实时状态（status=<ReservationStatus.TEMP_LEAVE: 'TEMP_LEAVE'>；expected=<SeatStatus.IN_USE: 'in_use'>）

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-218；SRS NFR-008/012；ADR-09 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 有效预约映射座位实时状态（status=<ReservationStatus.TEMP_LEAVE: 'TEMP_LEAVE'>；expected=<SeatStatus.IN_USE: 'in_use'>）；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, booking, moment, status, expected |
| 操作/输入 | 按源函数顺序执行：catalog.seat_status(session, seat, moment)；本例参数：status=<ReservationStatus.TEMP_LEAVE: 'TEMP_LEAVE'>；expected=<SeatStatus.IN_USE: 'in_use'>；参数：{"status": "<ReservationStatus.TEMP_LEAVE: 'TEMP_LEAVE'>", "expected": "<SeatStatus.IN_USE: 'in_use'>"} |
| 预期结果 | catalog.seat_status(session, seat, moment) == expected |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_seat_detail.py:36](../backend/tests/units/test_seat_detail.py)；`tests/units/test_seat_detail.py::test_current_booking_determines_status[TEMP_LEAVE-in_use]`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-219 未来预约不占据当前空闲状态

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-219；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 未来预约不占据当前空闲状态；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, booking, moment |
| 操作/输入 | 按源函数顺序执行：catalog.seat_status(session, seat, moment) |
| 预期结果 | catalog.seat_status(session, seat, moment) == E.SeatStatus.AVAILABLE |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_seat_detail.py:46](../backend/tests/units/test_seat_detail.py)；`tests/units/test_seat_detail.py::test_future_booking_does_not_occupy_seat_now`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-BE-220 座位详情设施与二维码载荷

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-BE-220；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 单元（Mock隔离） |
| 场景和风险 | 座位详情设施与二维码载荷；现有断言通过不等于全部业务需求验收。 |
| 前置数据与角色 | 合成内存对象、固定测试时钟；数据库Session及事务/外部协作按夹具Mock，不执行真实数据库并发。 夹具：monkeypatch, session, seat, moment |
| 操作/输入 | 按源函数顺序执行：catalog.seat_out(session, seat, moment, None) |
| 预期结果 | (result.room_name, result.code, result.floor) == ('一号自习室', 'A01', '3')；result.has_power is True；result.by_window is True；result.accessible is False；result.qr_payload == 'studyroom:seat:11' |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | pytest 通过；setup/call/teardown累计0.001s。 运行器确认现有断言通过；未采集独立函数返回快照，不填造逐值输出。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [backend/tests/units/test_seat_detail.py:52](../backend/tests/units/test_seat_detail.py)；`tests/units/test_seat_detail.py::test_detail_contains_facilities_and_qr_payload`；[backend-case-results.json](evidence/test/2026-11-26-full-suite/backend-case-results.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-001 保存及清除浏览器会话令牌

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-001；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 保存及清除浏览器会话令牌；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：setToken('abc')；setToken('')；核对所列expect断言。 |
| 预期结果 | expect(getToken()).toBe('abc')；expect(getToken()).toBeNull() |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时4.048ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/api/client.test.js:20](../frontend/src/api/client.test.js)；`token storage writes and clears the session token`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-002 请求携带Bearer并解析JSON

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-002；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 请求携带Bearer并解析JSON；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：setToken('abc')；const fetchMock = mockFetch({|
|<br>      status: 200,||
|<br>      ok: true,||
|<br>      json: async () => ({ ok: true }),||
|<br>    })；const [url, options] = fetchMock.mock.calls[0]；核对所列expect断言。 ||
| 预期结果 | expect(api('/auth/me')).resolves.toEqual({ ok: true })；expect(url).toBe('/api/auth/me')；expect(options.headers.Authorization).toBe('Bearer abc') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时4.490ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/api/client.test.js:29](../frontend/src/api/client.test.js)；`api sends the bearer token and returns JSON`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-003 204无正文响应返回null

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-003；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 204无正文响应返回null；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：mockFetch({ status: 204, ok: true, json: async () => ({}) })；核对所列expect断言。 |
| 预期结果 | expect(api('/auth/logout', { method: 'POST' })).resolves.toBeNull() |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | Vitest 通过；本例耗时1.064ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [frontend/src/api/client.test.js:42](../frontend/src/api/client.test.js)；`api returns null for an empty response`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-004 展示后端字符串错误提示

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-004；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 展示后端字符串错误提示；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：mockFetch({|
|<br>      status: 401,||
|<br>      ok: false,||
|<br>      json: async () => ({ detail: '学号或密码错误' }),||
|<br>    })；核对所列expect断言。 ||
| 预期结果 | expect(api('/auth/login', { method: 'POST', body: { student_no: '1' } })).rejects.toThrow(|
|<br>      '学号或密码错误',||
|<br>    ) ||
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | Vitest 通过；本例耗时2.584ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [frontend/src/api/client.test.js:47](../frontend/src/api/client.test.js)；`api surfaces a string error from the backend`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-005 拼接字段校验错误信息

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-005；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 拼接字段校验错误信息；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：mockFetch({|
|<br>      status: 422,||
|<br>      ok: false,||
|<br>      json: async () => ({ detail: [{ msg: '太短' }, { message: '缺数字' }] }),||
|<br>    })；核对所列expect断言。 ||
| 预期结果 | expect(api('/auth/register', { method: 'POST', body: {} })).rejects.toThrow(|
|<br>      '太短；缺数字',||
|<br>    ) ||
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | Vitest 通过；本例耗时1.080ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [frontend/src/api/client.test.js:58](../frontend/src/api/client.test.js)；`api joins field validation messages`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-006 提取对象错误并保留状态码

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-006；SRS NFR-008/012；ADR-09 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 提取对象错误并保留状态码；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：mockFetch({|
|<br>      status: 409,||
|<br>      ok: false,||
|<br>      json: async () => ({ detail: { message: '座位已被占用' } }),||
|<br>    })；const error = await api('/reservations', { method: 'POST', body: { seat_id: 1 } }).catch(||
|<br>      (err) => err,||
|<br>    )；核对所列expect断言。 ||
| 预期结果 | expect(error).toMatchObject({|
|<br>      message: '座位已被占用',||
|<br>      status: 409,||
|<br>      detail: { message: '座位已被占用' },||
|<br>    }) ||
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时1.926ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [frontend/src/api/client.test.js:69](../frontend/src/api/client.test.js)；`api uses an object message and keeps the status code`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-007 缺少详情时提示资源冲突

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-007；SRS FR-010～031、BR-001/010/011/050～052；ADR-02/03/04/10 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 缺少详情时提示资源冲突；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：mockFetch({ status: 409, ok: false, json: async () => ({}) })；核对所列expect断言。 |
| 预期结果 | expect(api('/reservations')).rejects.toThrow('资源冲突，请刷新后重试') |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | Vitest 通过；本例耗时0.880ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [frontend/src/api/client.test.js:85](../frontend/src/api/client.test.js)；`api explains a conflict that has no detail`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-008 响应不可解析时显示HTTP状态

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-008；SRS NFR-008/012；ADR-09 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 响应不可解析时显示HTTP状态；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：mockFetch({|
|<br>      status: 500,||
|<br>      ok: false,||
|<br>      json: async () => {||
|<br>        throw new Error('not json')||
|<br>      },||
|<br>    })；核对所列expect断言。 ||
| 预期结果 | expect(api('/health')).rejects.toThrow('请求失败（HTTP 500）') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时0.860ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [frontend/src/api/client.test.js:90](../frontend/src/api/client.test.js)；`api names the HTTP status when the body cannot be read`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-009 无令牌时保持未登录且不请求本人

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-009；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 无令牌时保持未登录且不请求本人；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：getToken.mockReturnValue(null)；核对所列expect断言。 |
| 预期结果 | expect(loadMe()).resolves.toBeNull()；expect(auth.loaded).toBe(true)；expect(api).not.toHaveBeenCalled()；expect(hasRole('user')).toBe(false)；expect(can('room:read')).toBe(false) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时3.812ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/auth.test.js:21](../frontend/src/auth.test.js)；`auth session stays logged out when there is no token`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-010 失效会话清除令牌及用户信息

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-010；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 失效会话清除令牌及用户信息；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：getToken.mockReturnValue('expired')；api.mockRejectedValue(new Error('unauthorized'))；await loadMe()；核对所列expect断言。 |
| 预期结果 | expect(setToken).toHaveBeenCalledWith(null)；expect(auth.user).toBeNull()；expect(auth.loaded).toBe(true) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时1.153ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/auth.test.js:30](../frontend/src/auth.test.js)；`auth session drops a token that the server no longer accepts`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-011 登录后保存会话用户及权限

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-011；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 登录后保存会话用户及权限；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：api.mockResolvedValue({ access_token: 'tok', user })；await login('20260001', 'Demo1234')；核对所列expect断言。 |
| 预期结果 | expect(api).toHaveBeenCalledWith('/auth/login', {|
|<br>      method: 'POST',||
|<br>      body: { student_no: '20260001', password: 'Demo1234' },||
|<br>    })；expect(setToken).toHaveBeenCalledWith('tok')；expect(hasRole('user')).toBe(true)；expect(hasRole('admin')).toBe(false)；expect(can('reservation:own')).toBe(true)；expect(can('user:manage')).toBe(false) ||
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时1.238ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/auth.test.js:39](../frontend/src/auth.test.js)；`auth session stores the user returned by login`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-012 注销请求失败也清理本地会话

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-012；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 注销请求失败也清理本地会话；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：auth.user = user；api.mockRejectedValue(new Error('offline'))；核对所列expect断言。 |
| 预期结果 | expect(logout()).rejects.toThrow('offline')；expect(auth.user).toBeNull()；expect(setToken).toHaveBeenCalledWith(null) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时2.683ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/auth.test.js:53](../frontend/src/auth.test.js)；`auth session clears the session even when logout fails`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-013 空状态组件无操作时仅显示标题

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-013；SRS NFR-009/010；测试计划及交互约定 |
| 层级 | 前端组件单元 |
| 场景和风险 | 空状态组件无操作时仅显示标题；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 Vue Test Utils挂载组件，RouterLink使用stub。 |
| 操作/输入 | 按源测试顺序执行：const wrapper = mount(EmptyState, {|
|<br>      props: { title: '还没有预约' },||
|<br>      global: { stubs },||
|<br>    })；核对所列expect断言。 ||
| 预期结果 | expect(wrapper.text()).toBe('还没有预约')；expect(wrapper.find('a').exists()).toBe(false) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时15.269ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P2（本次风险分级）。 |
| 证据 | [frontend/src/components/EmptyState.test.js:11](../frontend/src/components/EmptyState.test.js)；`EmptyState shows only the title when there is no action`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-014 空状态组件展示下一步链接

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-014；SRS NFR-009/010；测试计划及交互约定 |
| 层级 | 前端组件单元 |
| 场景和风险 | 空状态组件展示下一步链接；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 Vue Test Utils挂载组件，RouterLink使用stub。 |
| 操作/输入 | 按源测试顺序执行：const wrapper = mount(EmptyState, {|
|<br>      props: { title: '还没有预约', actionTo: '/workflows', actionText: '去预约' },||
|<br>      global: { stubs },||
|<br>    })；核对所列expect断言。 ||
| 预期结果 | expect(wrapper.get('a').text()).toBe('去预约')；expect(wrapper.get('a').attributes('href')).toBe('/workflows') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时9.583ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P2（本次风险分级）。 |
| 证据 | [frontend/src/components/EmptyState.test.js:20](../frontend/src/components/EmptyState.test.js)；`EmptyState links to the next step when an action is given`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-015 状态组件显示已知中文标签

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-015；SRS NFR-008/012；ADR-09 |
| 层级 | 前端组件单元 |
| 场景和风险 | 状态组件显示已知中文标签；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 Vue Test Utils挂载组件，RouterLink使用stub。 |
| 操作/输入 | 按源测试顺序执行：const wrapper = mount(StatusBadge, { props: { status: 'temp_leave' } })；核对所列expect断言。 |
| 预期结果 | expect(wrapper.text()).toBe('暂离')；expect(wrapper.classes()).toContain('tone-warn') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时15.468ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [frontend/src/components/StatusBadge.test.js:7](../frontend/src/components/StatusBadge.test.js)；`StatusBadge shows the shared label for a known status`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-016 状态组件保留未知状态原文

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-016；SRS NFR-008/012；ADR-09 |
| 层级 | 前端组件单元 |
| 场景和风险 | 状态组件保留未知状态原文；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 Vue Test Utils挂载组件，RouterLink使用stub。 |
| 操作/输入 | 按源测试顺序执行：const wrapper = mount(StatusBadge, { props: { status: '' } })；核对所列expect断言。 |
| 预期结果 | expect(wrapper.text()).toBe('—')；expect(wrapper.classes()).toContain('tone-neutral') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时2.395ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P1（本次风险分级）。 |
| 证据 | [frontend/src/components/StatusBadge.test.js:13](../frontend/src/components/StatusBadge.test.js)；`StatusBadge keeps an unknown status readable`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-017 确认对话框仅主动确认返回true

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-017；SRS NFR-009/010；测试计划及交互约定 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 确认对话框仅主动确认返回true；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：const pending = confirmDialog({ title: '取消预约', message: '确定取消？', danger: true })；settleConfirm(true)；核对所列expect断言。 |
| 预期结果 | expect(confirmState.open).toBe(true)；expect(confirmState.title).toBe('取消预约')；expect(confirmState.danger).toBe(true)；expect(pending).resolves.toBe(true)；expect(confirmState.open).toBe(false)；expect(confirmState.resolve).toBeNull() |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | Vitest 通过；本例耗时5.159ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P2（本次风险分级）。 |
| 证据 | [frontend/src/confirm.test.js:6](../frontend/src/confirm.test.js)；`confirmDialog resolves true only after the user confirms`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-018 打开新对话框取消已有待确认操作

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-018；SRS NFR-009/010；测试计划及交互约定 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 打开新对话框取消已有待确认操作；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：const first = confirmDialog({ title: '第一次' })；const second = confirmDialog({ title: '第二次' })；settleConfirm(false)；核对所列expect断言。 |
| 预期结果 | expect(first).resolves.toBe(false)；expect(confirmState.title).toBe('第二次')；expect(second).resolves.toBe(false) |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | Vitest 通过；本例耗时0.784ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P2（本次风险分级）。 |
| 证据 | [frontend/src/confirm.test.js:17](../frontend/src/confirm.test.js)；`confirmDialog cancels the dialog that is already open`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-019 输入框确认返回文本取消返回null

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-019；SRS NFR-009/010；测试计划及交互约定 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 输入框确认返回文本取消返回null；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：const pending = promptDialog({ title: '申诉原因', placeholder: '请填写' })；confirmState.value = '设备故障'；settleConfirm(true)；const cancelled = promptDialog()；settleConfirm(false)；核对所列expect断言。 |
| 预期结果 | expect(confirmState.input).toBe(true)；expect(confirmState.placeholder).toBe('请填写')；expect(pending).resolves.toBe('设备故障')；expect(cancelled).resolves.toBeNull() |
| 预期确认人 | 责任安排：周俊博 |
| 实际输出 | Vitest 通过；本例耗时0.699ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P2（本次风险分级）。 |
| 证据 | [frontend/src/confirm.test.js:28](../frontend/src/confirm.test.js)；`promptDialog returns the typed text, or null when cancelled`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-020 区域文案翻译及未知值回退

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-020；SRS NFR-009/010；测试计划及交互约定 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 区域文案翻译及未知值回退；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：；核对所列expect断言。 |
| 预期结果 | expect(zoneLabel('quiet')).toBe('静音区')；expect(zoneLabel('exam_prep')).toBe('考研区')；expect(zoneLabel('rooftop')).toBe('rooftop')；expect(zoneLabel('')).toBe('—')；expect(zoneLabel(null)).toBe('—') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时3.580ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P2（本次风险分级）。 |
| 证据 | [frontend/src/labels.test.js:6](../frontend/src/labels.test.js)；`zoneLabel translates known zones and keeps unknown values`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-021 违规文案兼容大小写及未知值

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-021；SRS FR-032～043/050～052/060～073；ADR-04/05/07/08 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 违规文案兼容大小写及未知值；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：；核对所列expect断言。 |
| 预期结果 | expect(violationTypeLabel('NO_SHOW')).toBe('预约未到（爽约）')；expect(violationTypeLabel('temp_leave_timeout')).toBe('暂离超时未归')；expect(violationTypeLabel('other')).toBe('other')；expect(violationTypeLabel('')).toBe('—') |
| 预期确认人 | 责任安排：方梓安 |
| 实际输出 | Vitest 通过；本例耗时0.757ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/labels.test.js:16](../frontend/src/labels.test.js)；`violationTypeLabel accepts either case and falls back to the raw value`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-022 设施文案仅组合实际具备项目

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-022；SRS NFR-009/010；测试计划及交互约定 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 设施文案仅组合实际具备项目；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：；核对所列expect断言。 |
| 预期结果 | expect(facilityText(null)).toBe('—')；expect(facilityText({})).toBe('—')；expect(facilityText({ has_power: true, by_window: true, accessible: false })).toBe('电源、靠窗')；expect(facilityText({ accessible: true })).toBe('无障碍') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时0.446ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P2（本次风险分级）。 |
| 证据 | [frontend/src/labels.test.js:25](../frontend/src/labels.test.js)；`facilityText joins the facilities a seat actually has`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-023 未登录访问受保护页跳转并保存目标

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-023；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 未登录访问受保护页跳转并保存目标；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：const loadMe = vi.fn()；const result = await authorizeNavigation(|
|<br>      { fullPath: '/workflows', meta: { auth: true } },||
|<br>      authState(null),||
|<br>      loadMe,||
|<br>    )；核对所列expect断言。 ||
| 预期结果 | expect(result).toEqual({ path: '/login', query: { next: '/workflows' } })；expect(loadMe).not.toHaveBeenCalled() |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时2.788ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/router/guard.test.js:10](../frontend/src/router/guard.test.js)；`authorizeNavigation sends an anonymous visitor to login and keeps the target`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-024 导航前只加载一次未初始化会话

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-024；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 导航前只加载一次未初始化会话；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：const auth = { loaded: false, user: null }；const loadMe = vi.fn(async () => {|
|<br>      auth.loaded = true||
|<br>      auth.user = { permissions: ['room:read'] }||
|<br>    })；const result = await authorizeNavigation({ fullPath: '/', meta: { auth: true } }, auth, loadMe)；核对所列expect断言。 ||
| 预期结果 | expect(loadMe).toHaveBeenCalledOnce()；expect(result).toBe(true) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时0.924ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/router/guard.test.js:21](../frontend/src/router/guard.test.js)；`authorizeNavigation loads the session once before deciding`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-025 缺少页面权限时阻止导航

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-025；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 缺少页面权限时阻止导航；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：const user = { permissions: ['room:read'] }；const missing = await authorizeNavigation(|
|<br>      { fullPath: '/admin/users', meta: { auth: true, perm: 'user:manage' } },||
|<br>      authState(user),||
|<br>      vi.fn(),||
|<br>    )；const neither = await authorizeNavigation(||
|<br>      {||
|<br>        fullPath: '/admin/logs',||
|<br>        meta: { auth: true, anyPerm: ['audit_log:read', 'system_log:read'] },||
|<br>      },||
|<br>      authState(user),||
|<br>      vi.fn(),||
|<br>    )；核对所列expect断言。 ||
| 预期结果 | expect(missing).toBe('/')；expect(neither).toBe('/') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时0.574ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/router/guard.test.js:32](../frontend/src/router/guard.test.js)；`authorizeNavigation blocks a page the signed-in user cannot access`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-026 任一允许权限匹配即可导航

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-026；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 任一允许权限匹配即可导航；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：const user = { permissions: ['system_log:read'] }；const result = await authorizeNavigation(|
|<br>      {||
|<br>        fullPath: '/admin/ops',||
|<br>        meta: { auth: true, anyPerm: ['system:backup', 'system_log:read'] },||
|<br>      },||
|<br>      authState(user),||
|<br>      vi.fn(),||
|<br>    )；核对所列expect断言。 ||
| 预期结果 | expect(result).toBe(true) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时0.537ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/router/guard.test.js:51](../frontend/src/router/guard.test.js)；`authorizeNavigation allows a page when any required permission matches`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-027 公共页面不要求登录

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-027；SRS FR-001～007、NFR-005/011；权限矩阵 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 公共页面不要求登录；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：const result = await authorizeNavigation(|
|<br>      { fullPath: '/login', meta: {} },||
|<br>      authState(null),||
|<br>      vi.fn(),||
|<br>    )；核对所列expect断言。 ||
| 预期结果 | expect(result).toBe(true) |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时0.572ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P0（本次风险分级）。 |
| 证据 | [frontend/src/router/guard.test.js:64](../frontend/src/router/guard.test.js)；`authorizeNavigation leaves public pages open`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-028 优先使用用户保存主题

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-028；SRS NFR-009/010；测试计划及交互约定 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 优先使用用户保存主题；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：localStorage.setItem('studyroom_theme', 'dark')；mockSystem(false)；initTheme()；核对所列expect断言。 |
| 预期结果 | expect(theme.followSystem).toBe(false)；expect(theme.name).toBe('dark')；expect(document.documentElement.dataset.theme).toBe('dark') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时7.180ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P2（本次风险分级）。 |
| 证据 | [frontend/src/theme.test.js:21](../frontend/src/theme.test.js)；`theme uses a saved choice instead of the system theme`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-029 未保存有效主题时跟随系统

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-029；SRS NFR-009/010；测试计划及交互约定 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 未保存有效主题时跟随系统；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：localStorage.setItem('studyroom_theme', 'blue')；mockSystem(true)；initTheme()；核对所列expect断言。 |
| 预期结果 | expect(theme.followSystem).toBe(true)；expect(theme.name).toBe('dark')；expect(document.documentElement.style.colorScheme).toBe('dark') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时1.122ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P2（本次风险分级）。 |
| 证据 | [frontend/src/theme.test.js:30](../frontend/src/theme.test.js)；`theme follows the system when nothing valid is saved`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

### TC-FE-030 切换主题后保存选择并停止跟随

| 字段 | 内容 |
|---|---|
| 编号/关联依据 | TC-FE-030；SRS NFR-009/010；测试计划及交互约定 |
| 层级 | 前端逻辑单元 |
| 场景和风险 | 切换主题后保存选择并停止跟随；happy-dom与Mock环境结论，不代表真实浏览器、摄像头、移动端或端到端通过。 |
| 前置数据与角色 | Vitest＋happy-dom；fetch/API/系统主题等依源码stub；不连接真实后端。 |
| 操作/输入 | 按源测试顺序执行：mockSystem(false)；initTheme()；toggleTheme()；toggleTheme()；核对所列expect断言。 |
| 预期结果 | expect(theme.name).toBe('dark')；expect(theme.followSystem).toBe(false)；expect(localStorage.getItem('studyroom_theme')).toBe('dark')；expect(theme.name).toBe('light') |
| 预期确认人 | 责任安排：张东岩 |
| 实际输出 | Vitest 通过；本例耗时0.931ms；运行期expect断言全部满足，具体表达式见预期；不将Mock返回写为真实后端响应。 |
| 执行结果 | 通过；2026-11-26本机自动运行；优先级P2（本次风险分级）。 |
| 证据 | [frontend/src/theme.test.js:39](../frontend/src/theme.test.js)；`theme toggle stores the choice and stops following the system`；[frontend-vitest.json](evidence/test/2026-11-26-full-suite/frontend-vitest.json)按nodeid/fullName定位；版本及环境见本报告§2。 |

## 6. 证据与复现

证据入口为[evidence/test/2026-11-26-full-suite/README.md](evidence/test/2026-11-26-full-suite/README.md)。包含全量日志、JUnit、Vitest JSON、逐例HTTP与并发服务输出、环境安装记录、源码SHA-256、未提交补丁、用例数据及采集脚本。

复现时以本轮source-manifest和补丁定位代码，使用合成数据与隔离临时SQLite；按环境版本准备依赖后在backend执行pytest、在frontend执行npm test。外部证据采集插件只增加记录，不改变业务与断言；具体命令和工作目录见各-command.json。标准测试无需采集插件也能运行，但不会产出逐例HTTP记录。

文档整理负责人按团队分工落实，实际执行者为本机自动化工具；交叉复核与课程验收由真实参与成员后续据实记录。本报告不代签。
