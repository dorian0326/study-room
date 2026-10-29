"""用户端座位与预约 API；时间必须包含时区。"""

from datetime import date, datetime, time

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.enums import CancelType, ReservationStatus, RoomStatus, SeatStatus, ZoneType
from app.timeutil import tz


class OpeningWindow(BaseModel):
    open_time: time
    close_time: time


class PublicRoom(BaseModel):
    id: int
    name: str
    location: str | None
    floor: str | None
    capacity: int
    facilities: str | None
    status: RoomStatus
    date: date
    opening_hours: list[OpeningWindow]


class PublicSeat(BaseModel):
    id: int
    room_id: int
    room_name: str
    code: str
    location: str | None
    floor: str | None
    facilities: str | None
    zone_type: ZoneType
    has_power: bool
    by_window: bool
    accessible: bool
    status: SeatStatus
    # 可印在桌上的二维码内容；不包含用户或预约信息。
    qr_payload: str


class ReservationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seat_id: int = Field(gt=0)
    start_time: AwareDatetime
    end_time: AwareDatetime

    @model_validator(mode="after")
    def validate_window(self):
        self.start_time = self.start_time.astimezone(tz())
        self.end_time = self.end_time.astimezone(tz())
        if self.start_time >= self.end_time:
            raise ValueError("开始时间必须早于结束时间")
        if self.start_time.date() != self.end_time.date():
            raise ValueError("预约不可跨零点")
        return self


class ChangeSeatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seat_id: int = Field(gt=0)


class CheckInIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    seat_id: int | None = Field(None, gt=0)
    room_id: int | None = Field(None, gt=0)
    seat_code: str | None = Field(None, min_length=1, max_length=32)

    @model_validator(mode="after")
    def validate_identifier(self):
        by_id = self.seat_id is not None and self.room_id is None and self.seat_code is None
        by_code = self.seat_id is None and self.room_id is not None and self.seat_code is not None
        if not (by_id or by_code):
            raise ValueError("请提供扫码座位 ID，或自习室 ID 与桌面座位编号")
        return self


class ReservationOut(BaseModel):
    id: int
    reservation_no: str
    room_id: int
    room_name: str
    seat_id: int
    seat_code: str
    start_time: datetime
    end_time: datetime
    status: ReservationStatus
    cancel_type: CancelType | None
    cancelled_at: datetime | None
    expire_reason: str | None
    arrived_at: datetime | None
    checkin_opens_at: datetime
    checkin_closes_at: datetime
