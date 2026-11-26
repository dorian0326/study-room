"""DEFECT-003：请求触发的未到处理累计违规后不创建禁约记录。"""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models import Restriction, ViolationRecord
from app.models import enums as E
from app.schemas.admin import BusinessSettings
from app.services import reservations as service


@pytest.mark.parametrize("warning_count, ban_days", [(3, 1), (5, 2), (7, 3)])
def test_srs_br095_no_show_must_apply_penalty_tier(
    monkeypatch,
    session,
    booking,
    moment,
    warning_count,
    ban_days,
):
    booking.start_time = moment - timedelta(hours=1)
    previous = SimpleNamespace(
        period_start=moment - timedelta(days=1),
        period_seq=warning_count - 1,
    )
    monkeypatch.setattr(service, "get_business_settings", lambda _: BusinessSettings())
    monkeypatch.setattr(service.audit, "record", Mock())
    # 没有当前预约的重复违规；同一统计周期已有前 warning_count-1 次警告。
    session.scalar.side_effect = [None, previous]
    session.scalars.side_effect = [[booking], []]

    service._expire_due(session, moment)

    added = [call.args[0] for call in session.add.call_args_list]
    violations = [item for item in added if isinstance(item, ViolationRecord)]
    assert len(violations) == 1
    assert violations[0].violation_type == E.ViolationType.NO_SHOW
    assert violations[0].period_seq == warning_count
    bans = [item for item in added if isinstance(item, Restriction)]
    assert len(bans) == 1, (
        f"违反 SRS BR-095 / AC-09：未到违规累计第 {warning_count} 次，"
        f"应禁约 {ban_days} 天，实际创建禁约记录 {len(bans)} 条"
    )
    assert bans[0].user_id == booking.user_id
    assert bans[0].ban_days == ban_days
    assert bans[0].status == E.RestrictionStatus.ACTIVE
    assert bans[0].end_at == moment + timedelta(days=ban_days)
