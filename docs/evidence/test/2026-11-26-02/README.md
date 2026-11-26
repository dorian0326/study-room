# 2026-11-26 需求导向缺陷复测证据

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
