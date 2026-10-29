"""演示用 Mock 数据（仅限开发 / 测试环境）。

python -m app.cli seed-mock            # 幂等：已导入则跳过
python -m app.cli seed-mock --reset    # 删除 Mock 行后重建

所有时间以当前 Asia/Shanghai 时间为基准倒推/顺推，每次重建都“看起来是最近的数据”。
数据经由真实模型写入（密码 bcrypt 哈希、违规阶梯走 services.violations），
并满足：同一座位 / 同一用户时段不重叠、位于开放时段内、同时有效预约 ≤ 1。
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import transaction
from app.models import (
    Appeal,
    ArrivalRecord,
    AuditLog,
    CalendarDay,
    EntryExitRecord,
    LoginLog,
    Notification,
    OpeningSchedule,
    Reservation,
    Restriction,
    Role,
    Seat,
    StudyRoom,
    SystemSetting,
    User,
    ViolationRecord,
)
from app.models import enums as E
from app.security import hash_password
from app.services.availability import opening_windows
from app.services.gate import user_key_for_gate
from app.services.reservations import _sync_seat
from app.services.settings import get_business_settings
from app.services.violations import record_violation
from app.timeutil import now as _now

MARKER_KEY = "_mock_data"
MOCK_VERSION = 1
GATE_SOURCE = "mock-gate"
CAL_NOTE_PREFIX = "[演示]"
STUDENT_PASSWORD = "Demo1234"

# (学号, 姓名, 角色, 密码, 院系, 备注)
STAFF = [
    ("A0000001", "演示管理员", "admin", "Admin1234", "图书馆管理部", "管理员"),
    ("O0000001", "演示运维", "ops", "Ops12345", "信息化中心", "运维"),
]
STUDENTS = [
    ("20260001", "林小满", "计算机学院", "演示学生（有进行中的预约）"),
    ("20260002", "陈思远", "计算机学院", "临时离开中"),
    ("20260003", "王雨桐", "外国语学院", "明天有预约"),
    ("20260004", "张子涵", "经济管理学院", "明天有预约，有待审申诉"),
    ("20260005", "李沐阳", "数学学院", ""),
    ("20260006", "刘欣怡", "法学院", ""),
    ("20260007", "赵一鸣", "机械工程学院", ""),
    ("20260008", "黄诗琪", "新闻传播学院", "申诉已通过"),
    ("20260009", "周浩然", "电子信息学院", "申诉被驳回"),
    ("20260010", "吴佳琪", "化学学院", ""),
    ("20260011", "徐明轩", "物理学院", ""),
    ("20260012", "孙若溪", "艺术学院", ""),
    ("20260013", "马俊杰", "土木工程学院", ""),
    ("20260014", "郑可欣", "医学院", "违规禁约中"),
    ("20260015", "何嘉豪", "体育学院", "账号已禁用"),
]
BANNED_NO = "20260014"
DISABLED_NO = "20260015"
ALL_NOS = [s[0] for s in STAFF] + [s[0] for s in STUDENTS]

# (名称, 位置, 楼层, 设施, 座位规格[(区域, 数量)], 节假日时段)
ROOMS = [
    (
        "图书馆一楼静音自习室",
        "图书馆 A 区",
        "1F",
        "空调、饮水机、储物柜",
        [(E.ZoneType.QUIET, 12)],
        (time(9), time(17)),  # 节假日缩短开放
    ),
    (
        "图书馆三楼讨论区",
        "图书馆 C 区",
        "3F",
        "白板、投影、可移动桌椅",
        [(E.ZoneType.DISCUSSION, 10)],
        (time(8), time(21)),
    ),
    (
        "图书馆五楼考研专区",
        "图书馆 E 区",
        "5F",
        "台灯、储物柜、打印机",
        [(E.ZoneType.EXAM_PREP, 10)],
        (time(8), time(21)),
    ),
    (
        "教学楼B201综合自习室",
        "第二教学楼",
        "2F",
        "空调、电源插座",
        [(E.ZoneType.QUIET, 5), (E.ZoneType.DISCUSSION, 3)],
        (time(8), time(21)),
    ),
]
ROOM_NAMES = [r[0] for r in ROOMS]
OPEN, CLOSE = time(7), time(22, 30)


class MockDataError(Exception):
    pass


def ensure_allowed() -> None:
    env = get_settings().env
    if env not in ("dev", "test"):
        raise MockDataError(f"STUDYROOM_ENV={env}：Mock 演示数据只允许在 dev / test 环境导入")


def is_seeded(session: Session) -> bool:
    return session.get(SystemSetting, MARKER_KEY) is not None


@dataclass
class _Ctx:
    session: Session
    now: datetime
    rng: random.Random
    users: dict[str, User] = field(default_factory=dict)
    seats: list[Seat] = field(default_factory=list)
    seat_busy: dict[int, list[tuple[datetime, datetime]]] = field(default_factory=dict)
    user_busy: dict[int, list[tuple[datetime, datetime]]] = field(default_factory=dict)
    seq: int = 0

    def at(self, day: date, t: time) -> datetime:
        return datetime.combine(day, t, self.now.tzinfo)


def _free(busy: list[tuple[datetime, datetime]], s: datetime, e: datetime) -> bool:
    return all(e <= bs or s >= be for bs, be in busy)


def _round(dt: datetime, minutes: int = 30) -> datetime:
    return dt.replace(minute=(dt.minute // minutes) * minutes, second=0, microsecond=0)


# ---------------- 基础数据 ----------------


def _make_users(c: _Ctx) -> None:
    roles = {r.name: r for r in c.session.scalars(select(Role))}
    rows = [(no, n, role, pw, dept, "") for no, n, role, pw, dept, _ in STAFF]
    rows += [(no, n, "user", STUDENT_PASSWORD, dept, "") for no, n, dept, _ in STUDENTS]
    for i, (no, name, role, pw, dept, _) in enumerate(rows):
        user = c.session.scalar(select(User).where(User.student_no == no))
        if user is None:
            user = User(student_no=no, name=name, password_hash=hash_password(pw))
            c.session.add(user)
        user.department = dept
        user.contact = f"{no}@stu.example.edu.cn"
        user.status = E.AccountStatus.DISABLED if no == DISABLED_NO else E.AccountStatus.NORMAL
        user.created_at = c.now - timedelta(days=40 - i)
        user.roles = [roles[E.RoleName(role)]]
        c.users[no] = user
    c.session.flush()


def _make_rooms(c: _Ctx) -> None:
    for name, loc, floor, fac, spec, holiday in ROOMS:
        room = StudyRoom(
            name=name,
            location=loc,
            floor=floor,
            facilities=fac,
            capacity=sum(n for _, n in spec),
            remark="演示数据",
            created_at=c.now - timedelta(days=45),
        )
        c.session.add(room)
        c.session.flush()
        for kind in (E.DayType.WEEKDAY, E.DayType.WEEKEND, E.DayType.EXAM_WEEK):
            c.session.add(
                OpeningSchedule(room_id=room.id, day_type=kind, open_time=OPEN, close_time=CLOSE)
            )
        c.session.add(
            OpeningSchedule(
                room_id=room.id,
                day_type=E.DayType.HOLIDAY,
                open_time=holiday[0],
                close_time=holiday[1],
            )
        )
        n = 0
        for zone, count in spec:
            for _ in range(count):
                n += 1
                seat = Seat(
                    room_id=room.id,
                    code=f"{floor[0]}{chr(64 + ROOM_NAMES.index(name) + 1)}-{n:02d}",
                    zone_type=zone,
                    has_power=n % 2 == 1 or zone == E.ZoneType.EXAM_PREP,
                    by_window=n % 4 in (1, 2),
                    accessible=n == 1,
                    status=E.SeatStatus.AVAILABLE,
                    status_changed_at=c.now - timedelta(days=30),
                )
                c.session.add(seat)
                c.seats.append(seat)
    c.session.flush()
    # 一个维护中的座位
    broken = c.seats[11]
    broken.status = E.SeatStatus.MAINTENANCE
    broken.status_changed_at = c.now - timedelta(days=2)


def _make_calendar(c: _Ctx) -> None:
    today = c.now.date()
    for offset, kind, note in (
        (-6, E.DayType.HOLIDAY, "校运动会（节假日时段）"),
        (5, E.DayType.HOLIDAY, "校庆日（节假日时段）"),
        (12, E.DayType.EXAM_WEEK, "期中考试周"),
    ):
        day = today + timedelta(days=offset)
        if c.session.get(CalendarDay, day) is None:
            c.session.add(CalendarDay(day=day, day_type=kind, note=f"{CAL_NOTE_PREFIX}{note}"))
    c.session.flush()


# ---------------- 预约 ----------------


def _reserve(
    c: _Ctx,
    user: User,
    seat: Seat,
    start: datetime,
    end: datetime,
    status: E.ReservationStatus,
    **extra,
) -> Reservation:
    c.seq += 1
    created = min(start - timedelta(hours=c.rng.randint(2, 20)), c.now - timedelta(minutes=5))
    r = Reservation(
        reservation_no=f"SR{created:%Y%m%d%H%M%S}M{c.seq:05d}",
        user_id=user.id,
        room_id=seat.room_id,
        seat_id=seat.id,
        start_time=start,
        end_time=end,
        status=status,
        created_at=created,
        remark="演示数据",
        **extra,
    )
    c.session.add(r)
    c.session.flush()
    c.seat_busy.setdefault(seat.id, []).append((start, end))
    c.user_busy.setdefault(user.id, []).append((start, end))
    c.session.add(
        Notification(
            user_id=user.id,
            type=E.NotificationType.RESERVATION_CONFIRMED,
            content=f"预约成功：{seat.room.name} {seat.code}，{start:%Y-%m-%d %H:%M}–{end:%H:%M}。",
            sent_at=created,
            is_read=start < c.now,
            idempotency_key=f"reservation:{r.id}:confirmed",
        )
    )
    return r


def _arrival(c: _Ctx, r: Reservation, **kw) -> ArrivalRecord:
    a = ArrivalRecord(reservation_id=r.id, user_id=r.user_id, seat_id=r.seat_id, **kw)
    c.session.add(a)
    c.session.flush()
    return a


def _gate(
    c: _Ctx, user: User, kind: E.EntryExitType, at: datetime, r: Reservation | None, status="synced"
) -> None:
    c.seq += 1
    delay = c.rng.randint(2, 40) if status != "late" else c.rng.randint(320, 900)
    c.session.add(
        EntryExitRecord(
            external_id=f"MOCK-{c.seq:06d}",
            source_system=GATE_SOURCE,
            masked_user_key=user_key_for_gate(user.student_no),
            record_type=kind,
            recorded_at=at,
            recognition=c.rng.choice([E.RecognitionMethod.FACE, E.RecognitionMethod.CARD]),
            received_at=at + timedelta(seconds=delay),
            expires_at=at + timedelta(days=get_settings().log_retention_days),
            sync_status=status,
            sync_delay_seconds=delay,
            reservation_id=r.id if r else None,
        )
    )


def _pick_slot(c: _Ctx, user: User, day: date, seats: list[Seat]):
    for _ in range(30):
        seat = c.rng.choice(seats)
        windows = opening_windows(c.session, seat.room_id, day)
        if not windows:
            continue
        w_open, w_close = windows[0]
        dur = c.rng.choice([2, 2, 3, 3, 4])
        first = c.at(day, w_open)
        last = c.at(day, w_close) - timedelta(hours=dur)
        if last < first:
            continue
        steps = int((last - first).total_seconds() // 1800)
        start = first + timedelta(minutes=30 * c.rng.randint(0, steps))
        end = start + timedelta(hours=dur)
        if end > c.now - timedelta(minutes=30):
            continue
        if _free(c.seat_busy.get(seat.id, []), start, end) and _free(
            c.user_busy.get(user.id, []), start, end
        ):
            return seat, start, end
    return None


def _completed(c: _Ctx, user: User, seat: Seat, start: datetime, end: datetime) -> Reservation:
    r = _reserve(c, user, seat, start, end, E.ReservationStatus.COMPLETED)
    arrived = start + timedelta(minutes=c.rng.randint(-10, 12))
    ended = end - timedelta(minutes=c.rng.randint(0, 40))
    _arrival(
        c,
        r,
        arrival_status=E.ArrivalStatus.EARLY
        if arrived < start
        else (
            E.ArrivalStatus.ON_TIME
            if arrived <= start + timedelta(minutes=5)
            else E.ArrivalStatus.LATE
        ),
        arrived_at=arrived,
        arrival_method=E.ArrivalMethod.QR,
        ended_at=ended,
        end_method=E.EndMethod.BUTTON,
        sync_delay_seconds=c.rng.randint(1, 30),
    )
    if end > c.now - timedelta(days=4):
        _gate(c, user, E.EntryExitType.ENTRY, arrived - timedelta(minutes=3), r)
        _gate(c, user, E.EntryExitType.EXIT, ended + timedelta(minutes=2), r)
    return r


def _make_history(c: _Ctx) -> dict[str, list]:
    """近 14 天的历史预约；违规按发生时间收集，之后按时间顺序计入阶梯。"""
    pending_violations: list[tuple[datetime, str, E.ViolationType, Reservation | None, str]] = []
    usable = [s for s in c.seats if s.status != E.SeatStatus.MAINTENANCE]
    budget = {no: 0 for no, *_ in STUDENTS}
    budget.update(
        {
            "20260004": 1,
            "20260008": 1,
            "20260009": 1,
            "20260005": 2,
            "20260010": 1,
            "20260012": 1,
            BANNED_NO: 2,
        }
    )
    today = c.now.date()
    for back in range(14, -1, -1):
        day = today - timedelta(days=back)
        for no, *_ in STUDENTS:
            user = c.users[no]
            if no == DISABLED_NO and back < 7:
                continue  # 禁用后不再有新预约
            for _ in range(c.rng.choice([0, 1, 1, 1, 2])):
                slot = _pick_slot(c, user, day, usable)
                if slot is None:
                    continue
                seat, start, end = slot
                roll = c.rng.random()
                can_violate = budget[no] > 0
                if can_violate and back == 3 + int(no[-2:]) % 6:
                    roll *= 0.18  # 确保有预算的学生至少产生一条违规（申诉演示依赖）
                if roll < 0.08 and can_violate:
                    # 未签到超时释放 → 爽约违规
                    r = _reserve(
                        c,
                        user,
                        seat,
                        start,
                        end,
                        E.ReservationStatus.EXPIRED,
                        expire_reason="no_show",
                    )
                    _arrival(c, r, arrival_status=E.ArrivalStatus.ABSENT)
                    at = start + timedelta(minutes=15)
                    pending_violations.append(
                        (
                            at,
                            no,
                            E.ViolationType.NO_SHOW,
                            r,
                            "预约开始后未在签到期限内到达，系统自动释放时段。",
                        )
                    )
                    budget[no] -= 1
                elif roll < 0.14 and can_violate:
                    # 开始前 15 分钟内取消 → 违规取消
                    at = start - timedelta(minutes=c.rng.randint(3, 14))
                    r = _reserve(
                        c,
                        user,
                        seat,
                        start,
                        end,
                        E.ReservationStatus.CANCELLED,
                        cancel_type=E.CancelType.LATE,
                        cancelled_at=at,
                        cancel_reason="临时有事",
                    )
                    r.created_at = min(r.created_at, at - timedelta(hours=1))
                    _arrival(c, r, arrival_status=E.ArrivalStatus.ABSENT)
                    pending_violations.append(
                        (at, no, E.ViolationType.LATE_CANCEL, r, "开始前15分钟内取消")
                    )
                    budget[no] -= 1
                elif roll < 0.18 and can_violate:
                    # 声明暂离后超时未归 → 超时结束
                    leave = start + timedelta(minutes=50)
                    r = _reserve(
                        c,
                        user,
                        seat,
                        start,
                        end,
                        E.ReservationStatus.TIMED_OUT,
                        temp_leave_at=leave,
                        temp_leave_state=E.TempLeaveState.TIMED_OUT,
                    )
                    _arrival(
                        c,
                        r,
                        arrival_status=E.ArrivalStatus.ON_TIME,
                        arrived_at=start,
                        arrival_method=E.ArrivalMethod.QR,
                        ended_at=leave + timedelta(minutes=30),
                        end_method=E.EndMethod.AUTO_TIMEOUT,
                    )
                    pending_violations.append(
                        (
                            leave + timedelta(minutes=30),
                            no,
                            E.ViolationType.TEMP_LEAVE_TIMEOUT,
                            r,
                            "临时离开超过 30 分钟未返回，座位已释放。",
                        )
                    )
                    budget[no] -= 1
                elif roll < 0.27:
                    at = start - timedelta(hours=c.rng.randint(1, 6))
                    r = _reserve(
                        c,
                        user,
                        seat,
                        start,
                        end,
                        E.ReservationStatus.CANCELLED,
                        cancel_type=E.CancelType.NORMAL,
                        cancelled_at=at,
                        cancel_reason=c.rng.choice(["课程调课", "改去图书馆其他区域", None]),
                    )
                    r.created_at = min(r.created_at, at - timedelta(hours=1))
                    _arrival(c, r, arrival_status=E.ArrivalStatus.ABSENT)
                elif roll < 0.29:
                    at = start - timedelta(hours=2)
                    r = _reserve(
                        c,
                        user,
                        seat,
                        start,
                        end,
                        E.ReservationStatus.ADMIN_CANCELLED,
                        cancel_type=E.CancelType.SYSTEM,
                        cancelled_at=at,
                        cancel_reason="座位临时检修，管理员强制取消",
                    )
                    r.created_at = min(r.created_at, at - timedelta(hours=1))
                    _arrival(c, r, arrival_status=E.ArrivalStatus.ABSENT)
                    c.session.add(
                        Notification(
                            user_id=user.id,
                            type=E.NotificationType.MAINTENANCE,
                            sent_at=at,
                            content=f"你的预约 {r.reservation_no} 因座位检修已被管理员取消。",
                            is_read=True,
                            idempotency_key=f"reservation:{r.id}:admin-cancelled",
                        )
                    )
                else:
                    _completed(c, user, seat, start, end)
    return {"violations": pending_violations}


def _make_current(c: _Ctx) -> None:
    """当前进行中 / 暂离 / 即将开始的预约（相对 now）。"""
    usable = [s for s in c.seats if s.status != E.SeatStatus.MAINTENANCE]
    today, tomorrow = c.now.date(), c.now.date() + timedelta(days=1)
    live_ok = False
    windows = opening_windows(c.session, usable[0].room_id, today)
    if windows:
        w_open, w_close = c.at(today, windows[0][0]), c.at(today, windows[0][1])
        live_ok = w_open + timedelta(minutes=60) <= c.now <= w_close - timedelta(minutes=45)

    def seat_for(start, end, user, pool):
        for s in pool:
            if _free(c.seat_busy.get(s.id, []), start, end) and _free(
                c.user_busy.get(user.id, []), start, end
            ):
                return s
        return None

    if live_ok:
        start = max(_round(c.now - timedelta(minutes=50)), w_open)
        end = min(_round(c.now + timedelta(hours=2, minutes=30)), w_close)
        # 进行中：主演示学生 + 几位同学
        for no in ("20260001", "20260005", "20260006", "20260010", "20260011", "20260013"):
            u = c.users[no]
            seat = seat_for(start, end, u, usable if no != "20260001" else [usable[2]] + usable)
            if seat is None:
                continue
            r = _reserve(c, u, seat, start, end, E.ReservationStatus.ACTIVE)
            arrived = start + timedelta(minutes=c.rng.randint(0, 8))
            _arrival(
                c,
                r,
                arrival_status=E.ArrivalStatus.ON_TIME,
                arrived_at=arrived,
                arrival_method=E.ArrivalMethod.QR,
                sync_delay_seconds=3,
            )
            _gate(c, u, E.EntryExitType.ENTRY, arrived - timedelta(minutes=2), r)
        # 临时离开中（10 分钟前离开，30 分钟内可返回）
        u = c.users["20260002"]
        seat = seat_for(start, end, u, usable[12:])
        if seat is not None:
            leave = c.now - timedelta(minutes=10)
            r = _reserve(
                c,
                u,
                seat,
                start,
                end,
                E.ReservationStatus.TEMP_LEAVE,
                temp_leave_at=leave,
                temp_leave_state=E.TempLeaveState.WAITING,
            )
            _arrival(
                c,
                r,
                arrival_status=E.ArrivalStatus.ON_TIME,
                arrived_at=start,
                arrival_method=E.ArrivalMethod.QR,
            )
            _gate(c, u, E.EntryExitType.ENTRY, start - timedelta(minutes=3), r)
            _gate(c, u, E.EntryExitType.EXIT, leave + timedelta(minutes=1), r)
            c.session.add(
                Notification(
                    user_id=u.id,
                    type=E.NotificationType.TEMP_LEAVE,
                    sent_at=leave,
                    content="已为你保留座位 30 分钟，请按时返回签到。",
                    idempotency_key=f"reservation:{r.id}:temp-leave",
                )
            )
    # 明天的预约（最多提前 1 天）
    for no, hour in (("20260003", 9), ("20260004", 14), ("20260007", 10), ("20260012", 19)):
        u = c.users[no]
        windows = opening_windows(c.session, usable[0].room_id, tomorrow)
        if not windows:
            break
        start = max(c.at(tomorrow, time(hour)), c.at(tomorrow, windows[0][0]))
        end = min(start + timedelta(hours=3), c.at(tomorrow, windows[0][1]))
        pool = [s for s in usable if opening_windows(c.session, s.room_id, tomorrow)]
        seat = seat_for(start, end, u, pool[(hour * 3) % len(pool) :] + pool)
        if seat is None or end <= start:
            continue
        r = _reserve(c, u, seat, start, end, E.ReservationStatus.RESERVED)
        r.created_at = c.now - timedelta(hours=c.rng.randint(1, 5))
        _arrival(c, r, arrival_status=E.ArrivalStatus.ABSENT)


def _apply_violations(c: _Ctx, pending: list) -> None:
    banned = c.users[BANNED_NO]
    # 禁约学生的第 3 次：一小时前闸机检测到未声明离馆（触发 1 天禁约）
    pending.append(
        (
            c.now - timedelta(hours=1),
            BANNED_NO,
            E.ViolationType.LEFT_UNDECLARED,
            None,
            "闸机检测到离馆，但未声明临时离开。",
        )
    )
    pending.sort(key=lambda v: v[0])
    created: dict[str, list[ViolationRecord]] = {}
    for at, no, kind, r, desc in pending:
        v = record_violation(
            c.session,
            user_id=c.users[no].id,
            violation_type=kind,
            reservation_id=r.id if r else None,
            description=desc,
            occurred_at=at,
        )
        v.created_at = at
        created.setdefault(no, []).append(v)
        for n in c.session.scalars(
            select(Notification).where(Notification.idempotency_key == f"violation:{v.id}:created")
        ):
            n.sent_at = at
            n.is_read = at < c.now - timedelta(days=2)
    c.session.flush()
    window = timedelta(days=get_business_settings(c.session).violation_window_days)
    for vs in created.values():
        for v in vs:
            if v.state == E.ViolationState.ACTIVE and v.period_start <= c.now - window:
                v.state, v.archived_at = E.ViolationState.ARCHIVED, v.period_start + window
    # 若禁约学生的前两条恰好未在同一窗口，确保其至少有一条生效的禁约
    if not c.session.scalar(
        select(Restriction).where(
            Restriction.user_id == banned.id, Restriction.status == E.RestrictionStatus.ACTIVE
        )
    ):
        c.session.add(
            Restriction(
                user_id=banned.id,
                ban_days=1,
                warning_count=3,
                trigger_condition="满3次",
                start_at=c.now - timedelta(hours=1),
                end_at=c.now + timedelta(hours=23),
            )
        )
    # 早于窗口的历史违规（已归档），让“历史记录”也有内容
    old = c.now - timedelta(days=20)
    c.session.add(
        ViolationRecord(
            user_id=c.users["20260007"].id,
            violation_type=E.ViolationType.NO_SHOW,
            occurred_at=old,
            description="预约开始后未在签到期限内到达，系统自动释放时段。",
            state=E.ViolationState.ARCHIVED,
            period_start=old,
            period_seq=1,
            archived_at=old + timedelta(days=14),
            created_at=old,
        )
    )

    admin = c.users["A0000001"]

    def appeal(no: str, reason: str, result: E.AppealResult | None, comment: str | None):
        v = created.get(no, [None])[0]
        if v is None:
            return
        a = Appeal(
            user_id=v.user_id,
            violation_id=v.id,
            restriction_id=v.restriction_id,
            reason=reason,
            evidence="课表截图.png",
            deadline=v.occurred_at + timedelta(days=7),
            created_at=v.occurred_at + timedelta(hours=3),
        )
        if result is None:
            v.appeal_status = E.AppealStatus.PENDING
        else:
            a.result, a.reviewer_id = result, admin.id
            a.reviewed_at = v.occurred_at + timedelta(days=1)
            a.review_comment = comment
            if result == E.AppealResult.APPROVED:
                v.appeal_status = E.AppealStatus.APPROVED
                v.state, v.archived_at = E.ViolationState.ARCHIVED, a.reviewed_at
            else:
                v.appeal_status = E.AppealStatus.REJECTED
            label = "通过" if result == E.AppealResult.APPROVED else "驳回"
            c.session.add(
                Notification(
                    user_id=v.user_id,
                    type=E.NotificationType.VIOLATION,
                    sent_at=a.reviewed_at,
                    content=f"你的违规申诉已{label}：{comment}",
                    is_read=True,
                )
            )
            c.session.add(
                AuditLog(
                    operator_id=admin.id,
                    op_type=E.AuditOpType.VIOLATION,
                    target_type="appeal",
                    target_id="mock",
                    occurred_at=a.reviewed_at,
                    ip_address="10.20.1.8",
                    after_value=json.dumps(
                        {"result": result.value, "comment": comment}, ensure_ascii=False
                    ),
                )
            )
        c.session.add(a)

    appeal("20260004", "当时在上实验课，课程临时拖堂，附课表。", None, None)
    appeal(
        "20260008",
        "门禁故障导致签到失败，已向前台登记。",
        E.AppealResult.APPROVED,
        "核实门禁故障，撤销违规",
    )
    appeal("20260009", "忘记了预约时间。", E.AppealResult.REJECTED, "理由不成立，维持原判")
    appeal(BANNED_NO, "离馆时手机没电无法声明暂离。", None, None)
    c.session.flush()


def _make_logs(c: _Ctx) -> None:
    admin, ops = c.users["A0000001"], c.users["O0000001"]
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5) Mobile/15E148",
    ]
    for no, user in c.users.items():
        for back in range(14, -1, -1):
            if c.rng.random() < (0.9 if no in ("A0000001", "O0000001") else 0.55):
                at = c.at(
                    c.now.date() - timedelta(days=back),
                    time(c.rng.randint(7, 21), c.rng.randint(0, 59)),
                )
                if at >= c.now:
                    continue
                ip = f"10.{c.rng.randint(1, 30)}.{c.rng.randint(0, 255)}.{c.rng.randint(2, 250)}"
                ua = c.rng.choice(agents)
                if c.rng.random() < 0.1:
                    c.session.add(
                        LoginLog(
                            user_id=user.id,
                            student_no=no,
                            event="login",
                            success=False,
                            reason="invalid_credentials",
                            occurred_at=at - timedelta(minutes=1),
                            ip_address=ip,
                            user_agent=ua,
                        )
                    )
                ok = no != DISABLED_NO or back > 6
                c.session.add(
                    LoginLog(
                        user_id=user.id,
                        student_no=no,
                        event="login",
                        success=ok,
                        reason=None if ok else "account_disabled",
                        occurred_at=at,
                        ip_address=ip,
                        user_agent=ua,
                    )
                )
                if ok and c.rng.random() < 0.4:
                    c.session.add(
                        LoginLog(
                            user_id=user.id,
                            student_no=no,
                            event="logout",
                            success=True,
                            occurred_at=at + timedelta(hours=2),
                            ip_address=ip,
                            user_agent=ua,
                        )
                    )
    for _ in range(3):  # 不存在学号的暴力尝试
        c.session.add(
            LoginLog(
                student_no="20269999",
                event="login",
                success=False,
                reason="invalid_credentials",
                ip_address="203.0.113.7",
                occurred_at=c.now - timedelta(hours=5, minutes=c.rng.randint(0, 9)),
            )
        )

    def audit(op, at, target_type, target_id, before=None, after=None, operator=admin):
        c.session.add(
            AuditLog(
                operator_id=operator.id if operator else None,
                op_type=op,
                target_type=target_type,
                target_id=str(target_id),
                occurred_at=at,
                ip_address="10.20.1.8",
                before_value=json.dumps(before, ensure_ascii=False) if before is not None else None,
                after_value=json.dumps(after, ensure_ascii=False) if after is not None else None,
            )
        )

    A = E.AuditOpType
    rooms = list(c.session.scalars(select(StudyRoom).where(StudyRoom.name.in_(ROOM_NAMES))))
    for i, room in enumerate(rooms):
        audit(
            A.ADMIN_ACTION,
            c.now - timedelta(days=45, minutes=-i),
            "study_room",
            room.id,
            after={"name": room.name, "capacity": room.capacity},
        )
    for no, *_ in STUDENTS[:6]:
        audit(
            A.PERMISSION_CHANGE,
            c.now - timedelta(days=38),
            "user",
            c.users[no].id,
            before={"roles": []},
            after={"roles": ["user"]},
        )
    audit(
        A.PERMISSION_CHANGE,
        c.now - timedelta(days=40),
        "user",
        ops.id,
        before={"roles": ["user"]},
        after={"roles": ["ops"]},
    )
    audit(
        A.ADMIN_ACTION,
        c.now - timedelta(days=8),
        "user",
        c.users[DISABLED_NO].id,
        before={"status": "normal"},
        after={"status": "disabled"},
    )
    audit(
        A.ADMIN_ACTION,
        c.now - timedelta(days=2),
        "seat",
        c.seats[11].id,
        before={"status": "available"},
        after={"status": "maintenance", "reason": "台灯损坏"},
    )
    audit(
        A.ADMIN_ACTION,
        c.now - timedelta(days=10),
        "system_setting",
        "no_show_after_minutes",
        before={"no_show_after_minutes": 10},
        after={"no_show_after_minutes": 15},
    )
    audit(
        A.ADMIN_ACTION,
        c.now - timedelta(days=7),
        "calendar_day",
        "holiday",
        after={"day_type": "holiday", "note": "校运动会"},
    )
    audit(
        A.ADMIN_ACTION,
        c.now - timedelta(days=1),
        "backup",
        "auto",
        after={"result": "ok"},
        operator=ops,
    )
    for v in c.session.scalars(
        select(ViolationRecord).where(ViolationRecord.user_id.in_([u.id for u in c.users.values()]))
    ):
        audit(
            A.VIOLATION,
            v.occurred_at,
            "violation_record",
            v.id,
            after={"type": v.violation_type.value, "seq": v.period_seq},
            operator=None,
        )
    # 系统公告与签到提醒
    for user in c.users.values():
        c.session.add(
            Notification(
                user_id=user.id,
                type=E.NotificationType.SYSTEM,
                sent_at=c.now - timedelta(days=13),
                content=(
                    "欢迎使用智慧自习室管理系统！"
                    "预约后请在开始前 15 分钟至开始后 15 分钟内扫码签到。"
                ),
                is_read=c.rng.random() < 0.7,
            )
        )
    for r in c.session.scalars(
        select(Reservation).where(
            Reservation.status == E.ReservationStatus.RESERVED,
            Reservation.user_id.in_([u.id for u in c.users.values()]),
        )
    ):
        c.session.add(
            Notification(
                user_id=r.user_id,
                type=E.NotificationType.CHECKIN_REMINDER,
                sent_at=c.now - timedelta(minutes=20),
                content=f"提醒：你预约的 {r.start_time:%m-%d %H:%M} 时段请按时签到。",
                idempotency_key=f"reservation:{r.id}:reminder",
            )
        )


# ---------------- 入口 ----------------


def _mock_user_ids(session: Session) -> list[int]:
    return list(session.scalars(select(User.id).where(User.student_no.in_(ALL_NOS))))


def clear(session: Session) -> None:
    """只删除 Mock 行（按 Mock 学号 / 自习室名 / 门禁来源 / 校历备注识别）。"""
    ensure_allowed()
    with transaction(session):
        uids = _mock_user_ids(session)
        room_ids = list(session.scalars(select(StudyRoom.id).where(StudyRoom.name.in_(ROOM_NAMES))))
        res_ids = list(
            session.scalars(
                select(Reservation.id).where(
                    or_(Reservation.user_id.in_(uids), Reservation.room_id.in_(room_ids))
                )
            )
        )
        session.execute(delete(Appeal).where(Appeal.user_id.in_(uids)))
        viol_ids = list(
            session.scalars(select(ViolationRecord.id).where(ViolationRecord.user_id.in_(uids)))
        )
        session.execute(
            delete(AuditLog).where(
                or_(
                    AuditLog.operator_id.in_(uids),
                    (AuditLog.target_type == "violation_record")
                    & AuditLog.target_id.in_([str(i) for i in viol_ids]),
                )
            )
        )
        session.execute(delete(ViolationRecord).where(ViolationRecord.user_id.in_(uids)))
        session.execute(delete(Restriction).where(Restriction.user_id.in_(uids)))
        session.execute(
            delete(EntryExitRecord).where(
                or_(
                    EntryExitRecord.source_system == GATE_SOURCE,
                    EntryExitRecord.reservation_id.in_(res_ids),
                )
            )
        )
        session.execute(delete(ArrivalRecord).where(ArrivalRecord.reservation_id.in_(res_ids)))
        session.execute(delete(Notification).where(Notification.user_id.in_(uids)))
        session.execute(delete(Reservation).where(Reservation.id.in_(res_ids)))
        session.execute(
            delete(LoginLog).where(
                or_(LoginLog.user_id.in_(uids), LoginLog.student_no.in_(ALL_NOS + ["20269999"]))
            )
        )
        session.execute(delete(Seat).where(Seat.room_id.in_(room_ids)))
        session.execute(delete(OpeningSchedule).where(OpeningSchedule.room_id.in_(room_ids)))
        session.execute(delete(StudyRoom).where(StudyRoom.id.in_(room_ids)))
        session.execute(delete(CalendarDay).where(CalendarDay.note.like(f"{CAL_NOTE_PREFIX}%")))
        for u in session.scalars(select(User).where(User.id.in_(uids))):
            session.delete(u)
        session.execute(delete(SystemSetting).where(SystemSetting.key == MARKER_KEY))


def seed(
    session: Session,
    *,
    reset: bool = False,
    moment: datetime | None = None,
    rng_seed: int = 20260326,
) -> bool:
    """导入演示数据。已导入且未要求 reset 时返回 False（幂等跳过）。"""
    ensure_allowed()
    if session.in_transaction():
        session.commit()
    if reset:
        clear(session)
    elif is_seeded(session):
        return False
    if session.scalar(select(StudyRoom.id).where(StudyRoom.name.in_(ROOM_NAMES))):
        clear(session)  # 半成品（标记缺失）先清理再重建
    session.commit()
    c = _Ctx(session=session, now=moment or _now(), rng=random.Random(rng_seed))
    with transaction(session, immediate=True):
        _make_users(c)
        _make_rooms(c)
        _make_calendar(c)
        hist = _make_history(c)
        _make_current(c)
        _apply_violations(c, hist["violations"])
        _make_logs(c)
        for seat in c.seats:
            _sync_seat(session, seat, c.now)
        session.add(
            SystemSetting(
                key=MARKER_KEY,
                updated_at=c.now,
                value=json.dumps({"version": MOCK_VERSION, "seeded_at": c.now.isoformat()}),
            )
        )
    return True


def summary(session: Session) -> dict[str, int]:
    """按表统计（供 CLI 打印）。"""
    from sqlalchemy import func

    models = [
        User,
        StudyRoom,
        Seat,
        OpeningSchedule,
        CalendarDay,
        Reservation,
        ArrivalRecord,
        ViolationRecord,
        Restriction,
        Appeal,
        Notification,
        EntryExitRecord,
        LoginLog,
        AuditLog,
    ]
    return {m.__tablename__: session.scalar(select(func.count()).select_from(m)) for m in models}


def demo_accounts() -> list[tuple[str, str, str, str]]:
    rows = [(no, pw, role, name) for no, name, role, pw, *_ in STAFF]
    rows += [
        (no, STUDENT_PASSWORD, "user", f"{name}{'（' + note + '）' if note else ''}")
        for no, name, _, note in STUDENTS
    ]
    return rows
