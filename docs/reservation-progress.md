# Issues #10–#16：后端阶段交付

本分支是阶段成果，七个 Issue 尚未全部完成。沿用 FastAPI / SQLAlchemy / SQLite。

## 需求与实现追溯

| Issue | 需求 | 实现 | 测试 |
|---|---|---|---|
| #10 自习室列表与座位搜索 | FR-010/011，UC-004/005 | services/availability.py、api/reservations.py；迁移 0006 可选 floor | test_room_search_detail_and_interval_states、test_calendar_priority_effective_dates_and_closed_room |
| #11 座位详情与实时状态 | FR-012/013，10_state_transitions | services/availability.py | test_room_search_detail_and_interval_states、test_checkin_identity_seat_repeat_and_state_transitions |
| #12 创建预约 | FR-020/023，UC-007 | services/reservations.py | test_create_rejects_invalid_times、test_overlap_person_overlap_adjacent_and_utc_conversion |
| #13 并发与幂等 | FR-024/080/081 | BEGIN IMMEDIATE、原有唯一索引、创建请求指纹 | test_100_competing_users_only_one_reservation、test_concurrent_retries_return_same_id、test_write_lock_error_is_retryable_and_same_key_can_recover |
| #14 仅换座 | FR-021，UC-008 | services/reservations.py::change_seat | test_change_seat_rechecks_conflicts_and_preserves_original_on_failure |
| #15 取消 | FR-022，HD-20/27/40 | services/reservations.py::cancel | test_cancel_exact_boundary_and_no_show_mutual_exclusion、test_restricted_user_can_cancel_but_cannot_create_or_change |
| #16 签到及超窗释放 | FR-026/030/031/033，UC-010 | services/reservations.py、reservation_worker.py | test_checkin_late_boundary_no_penalty_inside_window、test_unattended_expiry_worker_and_dedup |

路径均以 backend/app 为起点；测试位于 backend/tests/test_reservations.py。需求依据为 lieflatgo/Nailong-study-room 的 requirements/04、05、09、10 及 SRS；未修改需求仓库。

## 本次用户确认的冲突处理

- #13 按 Issue 和现有架构使用 BEGIN IMMEDIATE + 唯一约束 + 幂等键；不新增版本号乐观锁。
- 签到窗口含开始前后 15 分钟两端，窗内均不违规；超窗未签到记 1 次，不依赖门禁。短预约到结束时窗口关闭。
- 新增可选 floor 属性；管理端表单同步尚未完成。
- 禁约用户可取消；开始前恰好 15 分钟取消记 1 次，超过 15 分钟不记。开始后取消拒绝，按签到规则处理。

## API

所有接口复用现有 Bearer 登录认证。rooms/seats 需要 room:read；预约操作需要 reservation:own，查询和修改均仅本人。

- GET /api/rooms?date=YYYY-MM-DD：自习室及当天开放时间；未配置匹配日历的时段视为未开放。
- GET /api/seats：支持 room_id、zone_type、available_only，以及同时提供 date/start_time/end_time；无时间参数时返回当前状态。
- GET /api/seats/{id}：座位详情；同上时段参数；qr_payload 为 studyroom:seat:{id}。
- GET /api/reservations/current：本人的当前有效预约，用于操作入口；不替代 #21 历史模块。
- GET /api/reservations/{id}：本人预约详情。
- POST /api/reservations：JSON seat_id/start_time/end_time（时间带时区）；必填 Idempotency-Key 请求头（1–64 个字母数字或 ._:-）。首次 201，重放 200 并带 Idempotent-Replayed: true；同键不同请求返回 409。换座/取消后重试仍返回同一预约。
- PATCH /api/reservations/{id}/seat：只接受 seat_id；重新校验冲突与开放时段。
- POST /api/reservations/{id}/cancel：返回取消结果和 cancel_type。
- POST /api/reservations/{id}/check-in：接受 seat_id，或 room_id + seat_code（物理标签损坏的编号替代路径）。身份与预约所有者一致，座位匹配，重复签到幂等。
- 写锁超时返回 503 和 Retry-After: 1，客户端应使用同一幂等键重试创建。

运行前执行 alembic upgrade head。后台默认每 10 秒检查超窗预约；STUDYROOM_RESERVATION_SWEEP_INTERVAL_SECONDS=0 可关闭后台检查，相关请求仍补做超窗处理。

## 验证

上传前在 backend 实际执行：

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -X utf8 -m pytest -q --tb=short --basetemp=./.pytest-upload-check
```

结果：Ruff 通过，86 项后端测试通过（包含原有 52 项、新增 34 项）。提示包含 Starlette 对 httpx TestClient 的弃用提醒及 pytest 缓存目录权限警告；不影响测试断言。默认系统 pytest 临时目录因权限问题无法使用，因此指定项目内独立目录。

## 未完成与协作边界

- Vue 用户页面、摄像头扫码及楼层管理表单尚未完成，未进行前端端到端验收。当前仅提供后端扫码标识校验。
- #19 的阶梯处罚、归档、申诉尚待对应成员实现；本次只生成取消/未签到违规记录并写审计，读取现有 Restriction 阻止新预约。
- #20 的站内通知尚待对接；#17 结束使用、#18 门禁、#21 历史和 #23 座位管理未扩入此次范围。
- 单一扫码不能证明物理到场，沿用需求已确认限制。桌面二维码打印和部署尚未验收。
- 未创建 PR、未关闭 Issue；当前分支用于审查阶段成果。
