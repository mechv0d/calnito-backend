from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.common.enums import MealType
from app.core.config import get_settings


def get_zoneinfo(timezone_name: str | None) -> ZoneInfo:
    settings = get_settings()
    name = timezone_name or settings.default_timezone
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f'Invalid timezone: {name}') from exc


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def local_date_string(dt_utc: datetime, tz: ZoneInfo) -> str:
    return dt_utc.astimezone(tz).date().isoformat()


def infer_meal_type(local_dt: datetime) -> MealType:
    current = local_dt.time()

    if time(5, 0) <= current < time(10, 30):
        return MealType.BREAKFAST
    if time(10, 30) <= current < time(12, 0):
        return MealType.SECOND_BREAKFAST
    if time(12, 0) <= current < time(15, 30):
        return MealType.LUNCH
    if time(15, 30) <= current < time(17, 30):
        return MealType.AFTERNOON_SNACK
    return MealType.DINNER
