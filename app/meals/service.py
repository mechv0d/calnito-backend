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
from app.meals.models import ManualMealCreateRequest, MealUpdateRequest
from app.meals.repository import MealRepository
from app.meals.serializers import meal_to_response_dict
from app.storage.images import ImageProcessingError, process_food_photo
from app.storage.supabase_storage import SignedUrlError, StorageService


class MealService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.repo = MealRepository()
        self._storage: StorageService | None = None
        self.context = FoodContextService(self.repo)
        self.ai = AIClient()

    @property
    def storage(self) -> StorageService:
        if self._storage is None:
            self._storage = StorageService()
        return self._storage

    @storage.setter
    def storage(self, value: StorageService) -> None:
        self._storage = value

    def _meal_response(self, meal: dict, *, include_photo_url: bool = False) -> dict:
        return meal_to_response_dict(meal, self._storage, include_photo_url=include_photo_url)

    async def create_meal(
        self,
        uid: str,
        description: str,
        timezone_name: str | None,
        photo: UploadFile | None,
        background_tasks=None,
    ) -> dict:
        """Create a server-side pending meal and finish AI parsing in background.

        The HTTP request now returns as soon as the user input is safely stored.
        Closing the browser tab no longer cancels the long LLM parse request.
        """
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
                'items': [],
                'totals': {
                    'calories': 0.0,
                    'products_count': 0,
                    'total_weight_g': 0.0,
                },
                'processing_status': 'processing',
                'processing_error': None,
                'llm': {
                    'provider': 'openai',
                    'model': self.settings.llm_model,
                    'estimated': True,
                    'notes': 'AI parse queued',
                },
            }
            self.repo.create(uid, meal_id, meal)

            if background_tasks is not None:
                background_tasks.add_task(
                    complete_ai_meal_task,
                    uid=uid,
                    meal_id=meal_id,
                    description=description,
                    meal_type_value=meal_type.value,
                    image_webp_bytes=webp_bytes,
                )
            else:
                # Keeps tests and non-FastAPI callers functional.
                self.complete_ai_meal(
                    uid=uid,
                    meal_id=meal_id,
                    description=description,
                    meal_type_value=meal_type.value,
                    image_webp_bytes=webp_bytes,
                )
                completed = self.repo.get(uid, meal_id) or meal
                return self._meal_response(completed, include_photo_url=True)

            return self._meal_response(meal, include_photo_url=False)
        except Exception:
            if uploaded_storage_path:
                self.storage.remove_file(uploaded_storage_path)
            raise

    def complete_ai_meal(
        self,
        uid: str,
        meal_id: str,
        description: str,
        meal_type_value: str,
        image_webp_bytes: bytes | None = None,
    ) -> None:
        """Finish queued AI parsing without depending on the browser request."""
        existing = self.repo.get(uid, meal_id)
        if existing is None:
            return

        try:
            meal_type = MealType(meal_type_value)
            recent_products = self.context.recent_products(uid, limit=10)
            same_type_products = self.context.recent_products_by_type(uid, meal_type, limit=10)

            parsed = self.ai.parse_food(
                description=description,
                meal_type=meal_type,
                recent_products=recent_products,
                same_type_products=same_type_products,
                image_webp_bytes=image_webp_bytes,
            )

            items = build_items_from_parsed(parsed)
            self.repo.update(uid, meal_id, {
                'items': items,
                'totals': calculate_totals(items),
                'updated_at': now_utc(),
                'processing_status': 'completed',
                'processing_error': None,
                'llm': {
                    'provider': 'openai',
                    'model': self.settings.llm_model,
                    'estimated': True,
                    'notes': parsed.notes,
                },
            })
        except Exception as exc:
            self.repo.update(uid, meal_id, {
                'updated_at': now_utc(),
                'processing_status': 'failed',
                'processing_error': getattr(self.settings, 'user_facing_ai_error', 'Мы проебались, Босс.'),
                'llm': {
                    'provider': 'openai',
                    'model': self.settings.llm_model,
                    'estimated': True,
                    'notes': repr(exc),
                },
            })

    def create_manual_meal(
        self,
        uid: str,
        payload: ManualMealCreateRequest,
        timezone_name: str | None,
    ) -> dict:
        tz = self._resolve_tz(timezone_name)
        current_utc = now_utc()
        consumed_at_utc = payload.consumed_at.astimezone(timezone.utc)
        meal_id = uuid4().hex
        items = build_items_from_manual(payload.items)
        totals = calculate_totals(items)

        meal = {
            'id': meal_id,
            'uid': uid,
            'description': payload.description.strip(),
            'meal_type': payload.meal_type.value,
            'date_local': local_date_string(consumed_at_utc, tz),
            'consumed_at': consumed_at_utc,
            'created_at': current_utc,
            'updated_at': current_utc,
            'photo': {
                'storage_path': None,
                'width': None,
                'height': None,
            },
            'items': items,
            'totals': totals,
            'manual_created': True,
            'manual_edited': True,
            'processing_status': 'completed',
            'processing_error': None,
            'llm': {
                'provider': None,
                'model': None,
                'estimated': False,
                'notes': 'manual meal',
            },
        }
        self.repo.create(uid, meal_id, meal)
        return self._meal_response(meal)

    def search_product_suggestions(
        self,
        uid: str,
        query: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        normalized_query = (query or '').strip().lower()
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 50)
        meals = self.repo.list_recent(uid, limit=500)

        products: dict[str, dict] = {}
        for meal in meals:
            consumed_at = meal.get('consumed_at')
            for item in meal.get('items', []):
                name = str(item.get('product_name') or '').strip().lower()
                if not name:
                    continue
                if normalized_query and normalized_query not in name:
                    continue

                portion_g = self._float_or_zero(item.get('portion_g'))
                kcal_per_100g = self._float_or_zero(item.get('kcal_per_100g'))
                existing = products.setdefault(
                    name,
                    {
                        'product_name': name,
                        'kcal_weighted_sum': 0.0,
                        'portion_sum': 0.0,
                        'times_used': 0,
                        'last_used_at': None,
                    },
                )
                existing['times_used'] += 1
                existing['portion_sum'] += portion_g
                if portion_g > 0:
                    existing['kcal_weighted_sum'] += kcal_per_100g * portion_g
                elif kcal_per_100g > 0:
                    existing['kcal_weighted_sum'] += kcal_per_100g
                    existing['portion_sum'] += 1
                if consumed_at and (existing['last_used_at'] is None or consumed_at > existing['last_used_at']):
                    existing['last_used_at'] = consumed_at

        suggestions = []
        for product in products.values():
            portion_sum = product['portion_sum']
            times_used = product['times_used']
            suggestions.append({
                'product_name': product['product_name'],
                'kcal_per_100g': round(product['kcal_weighted_sum'] / portion_sum, 1) if portion_sum else 100.0,
                'times_used': times_used,
                'average_portion_g': round(portion_sum / times_used, 1) if times_used else 100.0,
                'last_used_at': product['last_used_at'],
            })

        suggestions.sort(key=lambda item: (item['times_used'], item['last_used_at'] is not None, item['last_used_at']), reverse=True)
        total = len(suggestions)
        start = (safe_page - 1) * safe_page_size
        end = start + safe_page_size
        return {
            'items': suggestions[start:end],
            'page': safe_page,
            'page_size': safe_page_size,
            'total': total,
            'has_next': end < total,
        }

    @staticmethod
    def _float_or_zero(value) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

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

        return self._meal_response(updated)

    def delete_meal(self, uid: str, meal_id: str) -> dict:
        deleted = self.repo.delete(uid, meal_id)
        if deleted is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Meal not found')
        storage_path = (deleted.get('photo') or {}).get('storage_path')
        if storage_path:
            self.storage.remove_file(storage_path)
        return {'ok': True, 'deleted_id': meal_id}

    def get_meal(self, uid: str, meal_id: str) -> dict:
        meal = self.repo.get(uid, meal_id)
        if meal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Meal not found')
        return self._meal_response(meal, include_photo_url=True)

    def get_meal_photo_url(self, uid: str, meal_id: str) -> dict:
        meal = self.repo.get(uid, meal_id)
        if meal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Meal not found')

        storage_path = (meal.get('photo') or {}).get('storage_path')
        if not storage_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Meal photo not found')

        try:
            signed_url = self.storage.create_signed_url(storage_path)
        except SignedUrlError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Photo URL is temporarily unavailable',
            ) from exc

        if not signed_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Photo URL is temporarily unavailable',
            )

        return {
            'meal_id': meal_id,
            'storage_path': storage_path,
            'signed_url': signed_url,
            'expires_in_seconds': self.settings.signed_url_expires_seconds,
        }

    def get_by_day(self, uid: str, date_local: str) -> dict:
        meals = self.repo.list_by_day(uid, date_local)
        responses = [self._meal_response(meal) for meal in meals]
        return {
            'date': date_local,
            'meals': responses,
            'total_calories': round(sum(float(meal['totals']['calories']) for meal in meals), 1),
        }


    def get_between_days(self, uid: str, date_from: str, date_to: str) -> dict:
        meals = self.repo.list_between_days(uid, date_from, date_to)
        responses = [self._meal_response(meal) for meal in meals]
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
            'meals': [self._meal_response(meal) for meal in meals],
        }

    def _resolve_tz(self, timezone_name: str | None):
        try:
            return get_zoneinfo(timezone_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail='Invalid timezone') from exc


def complete_ai_meal_task(
    uid: str,
    meal_id: str,
    description: str,
    meal_type_value: str,
    image_webp_bytes: bytes | None = None,
) -> None:
    MealService().complete_ai_meal(
        uid=uid,
        meal_id=meal_id,
        description=description,
        meal_type_value=meal_type_value,
        image_webp_bytes=image_webp_bytes,
    )
