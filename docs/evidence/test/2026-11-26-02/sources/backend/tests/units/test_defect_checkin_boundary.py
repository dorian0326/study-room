"""DEFECT-002：后台扫描在开始后恰好 15 分钟时提前判定未到。"""

from contextlib import nullcontext
from datetime import timedelta
from unittest.mock import Mock

from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import BinaryExpression

from app.schemas.admin import BusinessSettings
from app.services import reservations as service


def test_srs_ac02_sweep_must_keep_exact_checkin_deadline(monkeypatch, session, booking):
    """AC-02：09:00 开始的预约，在 09:15:00 仍可签到。"""
    deadline = booking.start_time + timedelta(minutes=15)
    monkeypatch.setattr(service, "get_business_settings", lambda _: BusinessSettings())
    monkeypatch.setattr(service, "transaction", lambda *_args, **_kw: nullcontext())
    monkeypatch.setattr(service, "archive_expired_violations", Mock(return_value=0))
    # 不模拟数据库筛选结果；捕获业务函数实际生成的候选查询。
    session.scalars.return_value = []

    service.sweep_reservations(session, deadline)

    pending_query = session.scalars.call_args_list[1].args[0]
    predicates = [
        node
        for node in visitors.iterate(pending_query.whereclause)
        if isinstance(node, BinaryExpression)
        and getattr(node.left, "name", None) == "start_time"
    ]
    assert len(predicates) == 1
    predicate = predicates[0]
    # 用真实 SQL 表达式的比较符和绑定时间计算这个边界样例是否被选中。
    selected_as_no_show = predicate.operator(booking.start_time, predicate.right.value)
    assert selected_as_no_show is False, (
        "违反 SRS AC-02 / BR-020：开始后恰好 15 分钟仍应允许签到，"
        "但后台未到扫描的真实查询已将该预约纳入失效候选"
    )
