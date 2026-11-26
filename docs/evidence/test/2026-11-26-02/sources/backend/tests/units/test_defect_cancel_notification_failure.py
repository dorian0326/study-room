"""DEFECT-004：通知创建异常会导致取消预约事务回滚。"""

from contextlib import nullcontext
from unittest.mock import Mock

import pytest

from app.models import enums as E
from app.services import reservations as service
from app.services.reservations import write_transaction as real_write_transaction


def test_srs_uc009_notification_failure_must_not_rollback_cancel(
    monkeypatch, session, booking, service_env,
):
    # 保留真实 write_transaction 和 transaction，只替代 Session 的创建。
    monkeypatch.setattr(service, "write_transaction", real_write_transaction)
    monkeypatch.setattr(service, "Session", Mock(return_value=nullcontext(session)))
    session.in_transaction.return_value = False
    service_env.create_notification.side_effect = RuntimeError("模拟站内通知创建失败")

    try:
        result = service.cancel(session, booking.user_id, booking.id)
    except RuntimeError as exc:
        assert str(exc) == "模拟站内通知创建失败"
        session.rollback.assert_called_once()
        session.commit.assert_not_called()
        pytest.fail(
            "违反 SRS UC-009 异常流程 E1 / EX-06：通知失败应保持取消生效，"
            "实际通知异常向外传播，取消事务已 rollback，未 commit"
        )

    assert result.status == E.ReservationStatus.CANCELLED
    session.commit.assert_called_once()
    session.rollback.assert_not_called()
