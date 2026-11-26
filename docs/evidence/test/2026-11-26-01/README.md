# 2026-11-26 全量测试证据

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

执行结束校验发现三份既有架构／接口文档在共享工作区发生其他编辑变化，已保留，详见source-comparison-after.json；前后端源码及测试内容SHA-256未变化，测试对应执行前隔离快照。
