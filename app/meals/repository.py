from datetime import datetime

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.common.enums import MealType
from app.db.firestore_refs import meal_doc, meals_collection


class MealRepository:
    def create(self, uid: str, meal_id: str, data: dict) -> None:
        meal_doc(uid, meal_id).set(data)

    def get(self, uid: str, meal_id: str) -> dict | None:
        snapshot = meal_doc(uid, meal_id).get()
        if not snapshot.exists:
            return None
        return snapshot.to_dict()

    def update(self, uid: str, meal_id: str, data: dict) -> dict | None:
        ref = meal_doc(uid, meal_id)
        if not ref.get().exists:
            return None
        ref.update(data)
        return ref.get().to_dict()

    def delete(self, uid: str, meal_id: str) -> dict | None:
        ref = meal_doc(uid, meal_id)
        snapshot = ref.get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict()
        ref.delete()
        return data

    def list_by_day(self, uid: str, date_local: str) -> list[dict]:
        docs = (
            meals_collection(uid)
            .where(filter=FieldFilter('date_local', '==', date_local))
            .order_by('consumed_at')
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    def list_between_days(self, uid: str, date_from: str, date_to: str) -> list[dict]:
        docs = (
            meals_collection(uid)
            .where(filter=FieldFilter('date_local', '>=', date_from))
            .where(filter=FieldFilter('date_local', '<=', date_to))
            .order_by('date_local')
            .order_by('consumed_at')
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    def list_recent(self, uid: str, limit: int = 20) -> list[dict]:
        docs = (
            meals_collection(uid)
            .order_by('consumed_at', direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    def list_recent_by_type(self, uid: str, meal_type: MealType, limit: int = 20) -> list[dict]:
        docs = (
            meals_collection(uid)
            .where(filter=FieldFilter('meal_type', '==', meal_type.value))
            .order_by('consumed_at', direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    def list_since_utc(self, uid: str, dt_from: datetime, limit: int = 200) -> list[dict]:
        docs = (
            meals_collection(uid)
            .where(filter=FieldFilter('consumed_at', '>=', dt_from))
            .order_by('consumed_at')
            .limit(limit)
            .stream()
        )
        return [doc.to_dict() for doc in docs]
