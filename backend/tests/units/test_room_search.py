"""自习室列表与座位搜索的单元测试。"""

from datetime import time

import pytest

from app.models import enums as E
from app.services import availability as catalog


def test_room_list_contains_room_information(monkeypatch, session, seat, moment):
    session.scalars.return_value = [seat.room]
    monkeypatch.setattr(catalog, "opening_windows", lambda *_: [(time(8), time(22))])

    result = catalog.room_list(session, moment.date())

    assert len(result) == 1
    room = result[0]
    assert (room.id, room.name, room.floor, room.capacity) == (1, "一号自习室", "3", 20)
    assert room.date == moment.date()
    assert (room.opening_hours[0].open_time, room.opening_hours[0].close_time) == (
        time(8), time(22),
    )


def test_empty_room_list(session, moment):
    assert catalog.room_list(session, moment.date()) == []


def test_search_unknown_room_fails(session, moment):
    session.get.return_value = None
    with pytest.raises(catalog.BookingError) as error:
        catalog.seat_list(session, moment, None, 999, None, False)
    assert error.value.status_code == 404
    session.scalars.assert_not_called()


@pytest.mark.parametrize("available_only, expected", [(False, [11, 12]), (True, [11])])
def test_search_available_only(monkeypatch, session, seat, moment, available_only, expected):
    from types import SimpleNamespace

    session.scalars.return_value = [seat, SimpleNamespace(id=12)]
    monkeypatch.setattr(
        catalog, "seat_out",
        lambda _, item, *_times: SimpleNamespace(
            id=item.id,
            status=E.SeatStatus.AVAILABLE if item.id == 11 else E.SeatStatus.RESERVED,
        ),
    )

    result = catalog.seat_list(session, moment, None, None, None, available_only)

    assert [item.id for item in result] == expected


@pytest.mark.parametrize("flag", [True, False])
def test_search_passes_room_zone_and_facility_filters(session, seat, moment, flag):
    session.get.return_value = seat.room

    catalog.seat_list(
        session, moment, None, 1, E.ZoneType.QUIET, False,
        has_power=flag, by_window=flag, accessible=flag,
    )

    # 检查生成的筛选条件；数据库执行不属于本单元测试的范围。
    query = session.scalars.call_args.args[0]
    sql = str(query)
    assert query.compile().params["room_id_1"] == 1
    assert query.compile().params["zone_type_1"] == E.ZoneType.QUIET
    for field in ("has_power", "by_window", "accessible"):
        assert f"seats.{field} IS {'true' if flag else 'false'}" in sql
