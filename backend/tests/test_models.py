"""#5：从零建库（Alembic），检查关键约束与 FR-083 事务回滚。"""

from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session, sessionmaker

from app.db import make_engine, transaction
from app.models import (
    Base,
    EntryExitRecord,
    Reservation,
    Role,
    Seat,
    StudyRoom,
    User,
)
from app.models import enums as E
from app.timeutil import now

BACKEND_DIR = __import__("pathlib").Path(__file__).resolve().parents[1]


def _alembic_cfg(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture
def db_url(tmp_path):
    url = f"sqlite:///{tmp_path}/models.db"
    command.upgrade(_alembic_cfg(url), "head")
    return url


@pytest.fixture
def engine(db_url):
    eng = make_engine(db_url)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with sessionmaker(bind=engine, expire_on_commit=False)() as s:
        yield s


def _user(no: str = "20260001") -> User:
    return User(student_no=no, password_hash="x", name="测试")


def _room_seat(session: Session) -> tuple[StudyRoom, Seat]:
    room = StudyRoom(name="一号自习室", capacity=10)
    seat = Seat(room=room, code="A01", zone_type=E.ZoneType.QUIET)
    session.add_all([room, seat])
    session.commit()
    return room, seat


def _reservation(user, room, seat, start, no, status=E.ReservationStatus.RESERVED):
    return Reservation(
        reservation_no=no,
        user=user,
        room_id=room.id,
        seat=seat,
        start_time=start,
        end_time=start + timedelta(hours=1),
        status=status,
    )


# ---------- 迁移 ----------


def test_all_tables_created(engine):
    tables = set(inspect(engine).get_table_names())
    assert set(Base.metadata.tables) <= tables
    assert "zones" not in tables  # 区域为座位属性（HD-47）
    assert "waitlist_entries" not in tables  # 候补移出范围（HD-41）


def test_migration_rerunnable_and_reversible(db_url):
    cfg = _alembic_cfg(db_url)
    command.upgrade(cfg, "head")  # 已是最新时再次执行不报错
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    eng = make_engine(db_url)
    with eng.connect() as conn:
        head = ScriptDirectory.from_config(cfg).get_current_head()
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == head
        assert conn.execute(text("SELECT count(*) FROM roles")).scalar() == 3
    eng.dispose()


def test_migration_matches_models(db_url):
    """迁移与 ORM 模型一致（等同 alembic check）。"""
    command.check(_alembic_cfg(db_url))


def test_roles_seeded(session):
    names = set(session.scalars(select(Role.name)))
    assert names == {E.RoleName.USER, E.RoleName.ADMIN, E.RoleName.OPS}


# ---------- 约束 ----------


def test_student_no_unique(session):
    session.add(_user("20260001"))
    session.commit()
    session.add(_user("20260001"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_foreign_keys_enforced(session):
    session.add(Seat(room_id=9999, code="X", zone_type=E.ZoneType.QUIET))
    with pytest.raises(IntegrityError):
        session.commit()


def test_seat_code_unique_within_room(session):
    room, _ = _room_seat(session)
    session.add(Seat(room_id=room.id, code="A01", zone_type=E.ZoneType.DISCUSSION))
    with pytest.raises(IntegrityError):
        session.commit()


def test_enum_check_constraint(session):
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO study_rooms (name, capacity, status, created_at) "
                "VALUES ('r', 1, 'bogus', '2026-01-01')"
            )
        )


def test_invalid_enum_rejected_by_orm():
    with pytest.raises((StatementError, LookupError, ValueError)):
        Seat.__table__.c.zone_type.type.bind_processor(None)("not-a-zone")  # noqa: B018


def test_reservation_time_order(session):
    user = _user()
    room, seat = _room_seat(session)
    start = now()
    r = _reservation(user, room, seat, start, "R1")
    r.end_time = start
    session.add(r)
    with pytest.raises(IntegrityError):
        session.commit()


def test_one_active_reservation_per_seat_slot(session):
    u1, u2 = _user("1"), _user("2")
    room, seat = _room_seat(session)
    start = now().replace(microsecond=0)
    session.add(_reservation(u1, room, seat, start, "R1"))
    session.commit()

    session.add(_reservation(u2, room, seat, start, "R2"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    # 取消后同一时段可以再被预约
    r1 = session.scalar(select(Reservation).where(Reservation.reservation_no == "R1"))
    r1.status = E.ReservationStatus.CANCELLED
    session.commit()
    session.add(_reservation(u2, room, seat, start, "R2"))
    session.commit()


def test_entry_exit_dedup(session):
    t = now()
    rec = dict(
        external_id="ext-1",
        source_system="gate",
        masked_user_key="h1",
        record_type=E.EntryExitType.ENTRY,
        recorded_at=t,
        received_at=t,
        expires_at=t + timedelta(minutes=40),
    )
    session.add(EntryExitRecord(**rec))
    session.commit()
    session.add(EntryExitRecord(**rec))
    with pytest.raises(IntegrityError):
        session.commit()


def test_datetime_stored_as_utc8(session):
    user = _user()
    room, seat = _room_seat(session)
    utc_start = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)  # = 08:00 北京时间
    session.add(_reservation(user, room, seat, utc_start, "R1"))
    session.commit()
    raw = session.execute(text("SELECT start_time FROM reservations")).scalar()
    assert str(raw).startswith("2026-11-01 08:00:00")
    session.expire_all()
    loaded = session.scalar(select(Reservation))
    assert loaded.start_time.utcoffset() == timedelta(hours=8)
    assert loaded.start_time == utc_start


def test_naive_datetime_rejected(session):
    user = _user()
    room, seat = _room_seat(session)
    session.add(_reservation(user, room, seat, datetime(2026, 11, 1, 8), "R1"))
    with pytest.raises(StatementError):
        session.commit()


# ---------- FR-083 事务回滚 ----------


def test_transaction_rolls_back_all_changes_on_error(session):
    room, seat = _room_seat(session)
    with pytest.raises(RuntimeError), transaction(session):
        session.add(_user("rollback-1"))
        seat.status = E.SeatStatus.RESERVED
        session.flush()
        raise RuntimeError("模拟业务失败")
    assert session.scalar(select(User).where(User.student_no == "rollback-1")) is None
    session.expire_all()
    assert session.get(Seat, seat.id).status == E.SeatStatus.AVAILABLE


def test_transaction_rolls_back_on_constraint_violation(session):
    session.add(_user("dup"))
    session.commit()
    with pytest.raises(IntegrityError), transaction(session):
        session.add(_user("ok-but-rolled-back"))
        session.add(_user("dup"))
        session.flush()
    assert session.scalar(select(User).where(User.student_no == "ok-but-rolled-back")) is None


def test_transaction_commits_on_success(session):
    with transaction(session):
        session.add(_user("committed"))
    session.expire_all()
    assert session.scalar(select(User).where(User.student_no == "committed")) is not None


def test_immediate_transaction_takes_write_lock(engine, db_url):
    """BEGIN IMMEDIATE 一开始就持有写锁：另一连接的写事务在 busy_timeout 后失败。"""
    import sqlite3

    s1 = Session(engine)
    with transaction(s1, immediate=True):
        other = sqlite3.connect(db_url.removeprefix("sqlite:///"), timeout=0.1)
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            other.execute("BEGIN IMMEDIATE")
        other.close()
    s1.close()
