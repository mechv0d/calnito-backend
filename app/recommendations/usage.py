from dataclasses import dataclass
from datetime import date, datetime, timezone

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.db.firestore_refs import user_doc


@dataclass(frozen=True)
class RecommendationLimit:
    used: int
    limit: int
    remaining: int
    week_key: str

    def to_dict(self) -> dict:
        return {
            'used': self.used,
            'limit': self.limit,
            'remaining': self.remaining,
            'week_key': self.week_key,
        }


class RecommendationUsageRepository:
    def _doc(self, uid: str, week_key: str):
        return user_doc(uid).collection('recommendation_usage').document(week_key)

    def get(self, uid: str, week_key: str) -> dict:
        snapshot = self._doc(uid, week_key).get()
        if not snapshot.exists:
            return {}
        return snapshot.to_dict() or {}

    def increment(self, uid: str, week_key: str, kind: str) -> None:
        ref = self._doc(uid, week_key)
        snapshot = ref.get()
        current = snapshot.to_dict() if snapshot.exists else {}
        kinds = dict(current.get('kinds') or {})
        kinds[kind] = int(kinds.get(kind, 0)) + 1
        ref.set({
            'week_key': week_key,
            'used': int(current.get('used') or 0) + 1,
            'kinds': kinds,
            'updated_at': datetime.now(timezone.utc),
        }, merge=True)


class RecommendationLimiter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.repo = RecommendationUsageRepository()

    def status(self, uid: str, local_date: date) -> RecommendationLimit:
        week_key = build_week_key(local_date)
        data = self.repo.get(uid, week_key)
        used = int(data.get('used') or 0)
        limit = max(int(self.settings.weekly_recommendation_limit), 0)
        return RecommendationLimit(
            used=used,
            limit=limit,
            remaining=max(limit - used, 0),
            week_key=week_key,
        )

    def ensure_available(self, uid: str, local_date: date) -> RecommendationLimit:
        current = self.status(uid, local_date)
        if current.remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f'Лимит рекомендаций на неделю исчерпан: {current.used}/{current.limit}.',
            )
        return current

    def consume(self, uid: str, local_date: date, kind: str) -> RecommendationLimit:
        week_key = build_week_key(local_date)
        self.repo.increment(uid, week_key, kind)
        return self.status(uid, local_date)


def build_week_key(local_date: date) -> str:
    year, week, _ = local_date.isocalendar()
    return f'{year}-W{week:02d}'
