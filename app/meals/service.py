from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.common.enums import MealType
from app.common.http import ai_failed_exception
from app.common.time import get_zoneinfo, infer_meal_type, local_date_string, now_utc
from app.core.config import get_settings
from app.llm.client import AIClient
from app.llm.exceptions import AIExhaustedError
from app.meals.calculations import build_items_from_manual, build_items_from_parsed, calculate_totals
from app.meals.context import FoodContextService
from app.meals.models import MealUpdateRequest
from app.meals.repository import MealRepository
from app.meals.serializers import meal_to_response_dict
from app.storage.images import ImageProcessingError, process_food_photo
from app.storage.supabase_storage import StorageService


class MealService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.repo = MealRepository()
        self.storage = StorageService()
        self.context = FoodContextService(self.repo)
        self.ai = AIClient()

    async def create_meal(
        self,
        uid: str,
        description: str,
        timezone_name: str | None,
        photo: UploadFile | None,
    ) -> dict:
        tz = self._resolve_tz(timezone_name)
        current_utc = now_utc()
        current_local = current_utc.astimezone(tz)
        meal_type = infer_meal_type(current_local)
        date_local = local_date_string(current_utc, tz)

        meal_id = uuid4().hex
        uploaded_storage_path: str | None = None
        photo_doc = {
            'storage_path': None,
            'width': None,
            'height': None,
        }
        webp_bytes: bytes | None = None

        try:
            if photo is not None:
                processed = await self._process_upload(photo)
                webp_bytes = processed.bytes
                uploaded_storage_path = self.storage.upload_meal_photo(uid, meal_id, webp_bytes)
                photo_doc = {
                    'storage_path': uploaded_storage_path,
                    'width': processed.width,
                    'height': processed.height,
                }

            recent_products = self.context.recent_products(uid, limit=10)
            same_type_products = self.context.recent_products_by_type(uid, meal_type, limit=10)

            parsed = self.ai.parse_food(
                description=description,
                meal_type=meal_type,
                recent_products=recent_products,
                same_type_products=same_type_products,
                image_webp_bytes=webp_bytes,
            )

            items = build_items_from_parsed(parsed)
            totals = calculate_totals(items)

            meal = {
                'id': meal_id,
                'uid': uid,
                'description': description,
                'meal_type': meal_type.value,
                'date_local': date_local,
                'consumed_at': current_utc,
                'created_at': current_utc,
                'updated_at': current_utc,
                'photo': photo_doc,
                'items': items,
                'totals': totals,
                'llm': {
                    'provider': 'openai',
                    'model': self.settings.llm_model,
                    'estimated': True,
                    'notes': parsed.notes,
                },
            }

            self.repo.create(uid, meal_id, meal)
            return meal_to_response_dict(meal, self.storage)
        except AIExhaustedError as exc:
            self.storage.remove_file(uploaded_storage_path)
            raise ai_failed_exception() from exc
        except Exception:
            self.storage.remove_file(uploaded_storage_path)
            raise

    async def _process_upload(self, photo: UploadFile):
        if photo.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
            raise HTTPException(status_code=400, detail='Unsupported image type')

        raw = await photo.read()
        if len(raw) > self.settings.max_upload_bytes:
            raise HTTPException(status_code=400, detail='Image is too large')

        try:
            return process_food_photo(raw)
        except ImageProcessingError as exc:
            raise HTTPException(status_code=400, detail='Invalid image') from exc

    def update_meal(
        self,
        uid: str,
        meal_id: str,
        payload: MealUpdateRequest,
        timezone_name: str | None,
    ) -> dict:
        existing = self.repo.get(uid, meal_id)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Meal not found')

        update_data: dict = {'updated_at': now_utc()}

        resulting_meal_type = MealType(payload.meal_type or existing['meal_type'])

        if payload.description is not None:
            update_data['description'] = payload.description

        if payload.meal_type is not None:
            update_data['meal_type'] = payload.meal_type.value

        if payload.consumed_at is not None:
            if resulting_meal_type != MealType.SNACKS:
                raise HTTPException(
                    status_code=400,
                    detail='Manual consumed_at change is allowed only for snacks',
                )
            consumed_at_utc = payload.consumed_at.astimezone(timezone.utc)
            update_data['consumed_at'] = consumed_at_utc
            tz = self._resolve_tz(timezone_name)
            update_data['date_local'] = local_date_string(consumed_at_utc, tz)

        if payload.items is not None:
            items = build_items_from_manual(payload.items)
            update_data['items'] = items
            update_data['totals'] = calculate_totals(items)
            update_data['manual_edited'] = True

        updated = self.repo.update(uid, meal_id, update_data)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Meal not found')

        return meal_to_response_dict(updated, self.storage)

    def delete_meal(self, uid: str, meal_id: str) -> dict:
        deleted = self.repo.delete(uid, meal_id)
        if deleted is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Meal not found')
        self.storage.remove_file((deleted.get('photo') or {}).get('storage_path'))
        return {'ok': True, 'deleted_id': meal_id}

    def get_meal(self, uid: str, meal_id: str) -> dict:
        meal = self.repo.get(uid, meal_id)
        if meal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Meal not found')
        return meal_to_response_dict(meal, self.storage)

    def get_by_day(self, uid: str, date_local: str) -> dict:
        meals = self.repo.list_by_day(uid, date_local)
        responses = [meal_to_response_dict(meal, self.storage) for meal in meals]
        return {
            'date': date_local,
            'meals': responses,
            'total_calories': round(sum(float(meal['totals']['calories']) for meal in meals), 1),
        }


    def get_between_days(self, uid: str, date_from: str, date_to: str) -> dict:
        meals = self.repo.list_between_days(uid, date_from, date_to)
        responses = [meal_to_response_dict(meal, self.storage) for meal in meals]
        return {
            'date_from': date_from,
            'date_to': date_to,
            'meals': responses,
            'total_calories': round(sum(float(meal['totals']['calories']) for meal in meals), 1),
        }

    def get_today_summary(self, uid: str, timezone_name: str | None) -> dict:
        tz = self._resolve_tz(timezone_name)
        today = local_date_string(now_utc(), tz)
        meals = self.repo.list_by_day(uid, today)

        by_type = {meal_type.value: 0.0 for meal_type in MealType}
        for meal in meals:
            by_type[meal['meal_type']] = round(
                by_type.get(meal['meal_type'], 0.0) + float(meal['totals']['calories']),
                1,
            )

        return {
            'date': today,
            'total_calories': round(sum(float(meal['totals']['calories']) for meal in meals), 1),
            'by_meal_type': by_type,
            'meals_count': len(meals),
            'meals': [meal_to_response_dict(meal, self.storage) for meal in meals],
        }

    def _resolve_tz(self, timezone_name: str | None):
        try:
            return get_zoneinfo(timezone_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail='Invalid timezone') from exc
