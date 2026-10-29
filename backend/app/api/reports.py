"""管理员资源利用率、预约高峰、违规趋势和 Excel 导出。"""

from collections import Counter
from datetime import date, datetime, time, timedelta
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import func, select

from app.deps import SessionDep, require_permission
from app.models import (
    CalendarDay,
    OpeningSchedule,
    Reservation,
    Seat,
    StudyRoom,
    User,
    ViolationRecord,
)
from app.models import enums as E
from app.timeutil import tz

router = APIRouter(prefix="/admin/reports", tags=["admin-reports"])
StatsAdmin = Annotated[User, Depends(require_permission("stats:read"))]
ExportAdmin = Annotated[User, Depends(require_permission("data:export"))]


def _period(start: date, end: date) -> tuple[datetime, datetime]:
    """把含首尾日期的报告区间转换为 Asia/Shanghai 半开区间。"""
    if start > end:
        raise HTTPException(422, "开始日期不能晚于结束日期")
    if (end - start).days > 366:
        raise HTTPException(422, "报告时间范围最多为一年")
    zone = tz()
    return datetime.combine(start, time.min, zone), datetime.combine(
        end + timedelta(days=1), time.min, zone
    )


def _day_type(session: SessionDep, day: date) -> E.DayType:
    """优先读取管理员校历，其余日期按周末或工作日推算。"""
    special = session.get(CalendarDay, day)
    if special:
        return special.day_type
    return E.DayType.WEEKEND if day.weekday() >= 5 else E.DayType.WEEKDAY


def _scheduled_seat_hours(session: SessionDep, start: date, end: date) -> float:
    """按每日开放时段和可用座位数计算统计区间内的供给座位小时。"""
    # 维护中、关闭和禁用的座位从可供预约容量中排除。
    rooms = list(session.scalars(select(StudyRoom).where(StudyRoom.status == E.RoomStatus.OPEN)))
    total = 0.0
    current = start
    while current <= end:
        day_kind = _day_type(session, current)
        for room in rooms:
            seat_count = (
                session.scalar(
                    select(func.count(Seat.id)).where(
                        Seat.room_id == room.id,
                        Seat.status.not_in(
                            (E.SeatStatus.MAINTENANCE, E.SeatStatus.CLOSED, E.SeatStatus.DISABLED)
                        ),
                    )
                )
                or 0
            )
            schedules = session.scalars(
                select(OpeningSchedule).where(
                    OpeningSchedule.room_id == room.id,
                    OpeningSchedule.day_type == day_kind,
                    OpeningSchedule.enabled.is_(True),
                    (OpeningSchedule.effective_from.is_(None))
                    | (OpeningSchedule.effective_from <= current),
                    (OpeningSchedule.effective_to.is_(None))
                    | (OpeningSchedule.effective_to >= current),
                )
            )
            for schedule in schedules:
                hours = (
                    datetime.combine(current, schedule.close_time)
                    - datetime.combine(current, schedule.open_time)
                ).total_seconds() / 3600
                total += hours * seat_count
        current += timedelta(days=1)
    return total


def build_report(session: SessionDep, start: date, end: date) -> dict:
    """汇总资源利用率、预约高峰和违规趋势，并明确统计口径。"""
    start_at, end_exclusive = _period(start, end)
    # 预约时长仅统计已签到的最终记录，未签到和被取消预约不计入使用小时。
    reservations = list(
        session.scalars(
            select(Reservation).where(
                Reservation.start_time < end_exclusive,
                Reservation.end_time > start_at,
            )
        )
    )
    counted = [
        item
        for item in reservations
        if item.status
        in (
            E.ReservationStatus.ACTIVE,
            E.ReservationStatus.TEMP_LEAVE,
            E.ReservationStatus.COMPLETED,
            E.ReservationStatus.TIMED_OUT,
        )
    ]
    booked_hours = sum(
        max(
            0.0,
            (min(item.end_time, end_exclusive) - max(item.start_time, start_at)).total_seconds()
            / 3600,
        )
        for item in counted
    )
    available_hours = _scheduled_seat_hours(session, start, end)

    # 每天和开始小时的组合用于展示预约高峰，不推断座位实际入座人数。
    peaks: Counter[tuple[str, int]] = Counter()
    for item in reservations:
        local_start = item.start_time.astimezone(tz())
        if start <= local_start.date() <= end:
            peaks[(local_start.date().isoformat(), local_start.hour)] += 1
    peak_rows = [
        {"day": day, "hour": hour, "reservations": count}
        for (day, hour), count in sorted(peaks.items(), key=lambda row: (-row[1], row[0]))
    ]

    # 趋势包含候选与已确认记录，以实际发生日期分组并保留违规类型。
    violations = list(
        session.scalars(
            select(ViolationRecord).where(
                ViolationRecord.occurred_at >= start_at,
                ViolationRecord.occurred_at < end_exclusive,
            )
        )
    )
    trends = Counter(
        (item.occurred_at.astimezone(tz()).date().isoformat(), item.violation_type.value)
        for item in violations
    )
    trend_rows = [
        {"day": day, "type": kind, "count": count} for (day, kind), count in sorted(trends.items())
    ]
    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "definition": {
            "utilization": "已签到预约的预约时长 / 开放且非维护座位的计划开放时长",
            "peak": "按预约开始日期和小时统计预约数量",
            "violations": "按违规发生日期和类型统计系统记录条数",
        },
        "utilization": {
            "booked_hours": round(booked_hours, 2),
            "available_hours": round(available_hours, 2),
            "rate": round(booked_hours / available_hours, 4) if available_hours else 0.0,
        },
        "reservation_count": len(reservations),
        "booking_peaks": peak_rows,
        "violation_trends": trend_rows,
    }


@router.get("")
def read_report(
    _: StatsAdmin,
    session: SessionDep,
    start: date | None = None,
    end: date | None = None,
):
    """返回区间内的利用率、预约高峰和违规趋势 JSON。"""
    # 所有指标同时返回统计口径和日期范围，避免把预约时长误读为真实现场占座。
    report_end = end or datetime.now(tz()).date()
    report_start = start or report_end - timedelta(days=29)
    return build_report(session, report_start, report_end)


@router.get("/export.xlsx")
def export_report(
    _: ExportAdmin,
    session: SessionDep,
    start: date | None = None,
    end: date | None = None,
):
    """把同一组统计结果导出为可下载的 XLSX 工作簿。"""
    report_end = end or datetime.now(tz()).date()
    report_start = start or report_end - timedelta(days=29)
    report = build_report(session, report_start, report_end)
    # 分工作表组织概览、高峰和违规趋势，Excel 文件内保留日期和口径说明。
    workbook = Workbook()
    overview = workbook.active
    overview.title = "利用率概览"
    overview.append(["指标", "数值", "统计口径"])
    overview.append(["开始日期", report["period"]["start"], "含首尾日期"])
    overview.append(["结束日期", report["period"]["end"], "含首尾日期"])
    overview.append(
        [
            "已预约时长（小时）",
            report["utilization"]["booked_hours"],
            report["definition"]["utilization"],
        ]
    )
    overview.append(
        [
            "可用时长（座位小时）",
            report["utilization"]["available_hours"],
            report["definition"]["utilization"],
        ]
    )
    overview.append(["利用率", report["utilization"]["rate"], report["definition"]["utilization"]])
    overview.append(["预约数", report["reservation_count"], "所有状态的预约记录数量"])
    peaks = workbook.create_sheet("预约高峰")
    peaks.append(["日期", "开始小时", "预约数"])
    for row in report["booking_peaks"]:
        peaks.append([row["day"], row["hour"], row["reservations"]])
    trends = workbook.create_sheet("违规趋势")
    trends.append(["日期", "违规类型", "记录数"])
    for row in report["violation_trends"]:
        trends.append([row["day"], row["type"], row["count"]])
    for worksheet in workbook.worksheets:
        # 表头样式和冻结行便于管理员筛选较长报表。
        worksheet.freeze_panes = "A2"
        for cell in worksheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="285C4D")
        for column in worksheet.columns:
            width = min(64, max(12, max(len(str(cell.value or "")) for cell in column) + 2))
            worksheet.column_dimensions[column[0].column_letter].width = width
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    filename = f"study-room-report-{report_start:%Y%m%d}-{report_end:%Y%m%d}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
