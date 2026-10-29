"""业务参数读写。库中只保存被修改过的键，其余取 BusinessSettings 默认值。"""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SystemSetting, User
from app.schemas.admin import BusinessSettings
from app.timeutil import now


def get_business_settings(session: Session) -> BusinessSettings:
    stored = {s.key: json.loads(s.value) for s in session.scalars(select(SystemSetting))}
    known = {k: v for k, v in stored.items() if k in BusinessSettings.model_fields}
    return BusinessSettings.model_validate(known)


def save_business_settings(session: Session, new: BusinessSettings, operator: User) -> dict:
    """写入变化的键，返回 {key: (旧值, 新值)}。调用方负责事务。"""
    old = get_business_settings(session).model_dump(mode="json")
    changed = {}
    for key, value in new.model_dump(mode="json").items():
        if old[key] == value:
            continue
        changed[key] = (old[key], value)
        row = session.get(SystemSetting, key) or SystemSetting(key=key)
        row.value = json.dumps(value)
        row.updated_at = now()
        row.updated_by = operator.id
        session.add(row)
    return changed
