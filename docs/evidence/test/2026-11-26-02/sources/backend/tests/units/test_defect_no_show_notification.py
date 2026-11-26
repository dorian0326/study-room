"""缺陷复现：SRS AC-03 要求超窗未签到自动失效时通知用户。

保留真实的 _expire_due -> _expire_one -> _record_violation 调用链；
只用 Mock 替代数据库和审计，不替换通知逻辑，也不使用 service_env。
本测试按需求断言，当前实现应失败；修复缺陷后应直接通过。
"""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from app.models import Notification, ViolationRecord
from app.models import enums as E
from app.services import reservations as service


def test_srs_ac03_no_show_expiry_must_notify_user(monkeypatch, session, booking, moment):
    # 预约 09:00–11:00，当前 10:00，已超出开始后 15 分钟的签到窗口。
    booking.start_time = moment - timedelta(hours=1)
    booking.end_time = moment + timedelta(hours=1)
    booking.seat.status = E.SeatStatus.RESERVED
    monkeypatch.setattr(
        service,
        "get_business_settings",
        lambda _: SimpleNamespace(no_show_after_minutes=15, violation_window_days=14),
    )
    monkeypatch.setattr(service.audit, "record", Mock())
    # 第一次查询返回超时预约，座位同步时没有其他有效预约。
    session.scalars.side_effect = [[booking], []]
    session.scalar.return_value = None

    expired_count = service._expire_due(session, moment)

    # 先确认真实执行了失效、释放与违规记录，避免只凭缺少通知推断缺陷。
    assert expired_count == 1
    assert booking.status == E.ReservationStatus.EXPIRED
    assert booking.expire_reason == "no_show"
    assert booking.seat.status == E.SeatStatus.AVAILABLE
    added = [call.args[0] for call in session.add.call_args_list]
    violations = [item for item in added if isinstance(item, ViolationRecord)]
    assert len(violations) == 1
    assert violations[0].violation_type == E.ViolationType.NO_SHOW
    assert violations[0].user_id == booking.user_id

    # SRS docs/软件需求规格说明书.md 的 AC-03：用户收到通知。
    notices = [item for item in added if isinstance(item, Notification)]
    assert any(item.user_id == booking.user_id for item in notices), (
        "违反 SRS AC-03：超窗未签到预约已失效、座位已释放并记录违规，"
        f"但没有给用户 {booking.user_id} 创建站内通知（实际通知数={len(notices)}）"
    )
