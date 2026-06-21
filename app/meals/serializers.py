from __future__ import annotations

import logging

from app.common.enums import MealType, MEAL_TYPE_LABELS_RU
from app.storage.supabase_storage import SignedUrlError, StorageService

logger = logging.getLogger(__name__)


def meal_to_response_dict(
    meal: dict,
    storage: StorageService | None = None,
    *,
    include_photo_url: bool = False,
) -> dict:
    meal_type = MealType(meal['meal_type'])
    photo = meal.get('photo') or {}
    storage_path = photo.get('storage_path')
    signed_url = None

    if storage_path and include_photo_url:
        try:
            storage = storage or StorageService()
            signed_url = storage.create_signed_url(storage_path)
        except SignedUrlError:
            logger.warning(
                'Failed to create signed meal photo URL: meal_id=%s storage_path=%s',
                meal.get('id'),
                storage_path,
                exc_info=True,
            )
            signed_url = None
        except Exception:
            logger.exception(
                'Unexpected error while creating signed meal photo URL: meal_id=%s storage_path=%s',
                meal.get('id'),
                storage_path,
            )
            signed_url = None

    return {
        'id': meal['id'],
        'meal_type': meal_type.value,
        'meal_type_label': MEAL_TYPE_LABELS_RU[meal_type],
        'date_local': meal['date_local'],
        'consumed_at': meal['consumed_at'],
        'created_at': meal['created_at'],
        'updated_at': meal['updated_at'],
        'description': meal.get('description', ''),
        'items': meal.get('items', []),
        'totals': meal.get('totals', {'calories': 0, 'products_count': 0, 'total_weight_g': 0}),
        'photo': {
            'storage_path': storage_path,
            'signed_url': signed_url,
            'width': photo.get('width'),
            'height': photo.get('height'),
        } if storage_path else None,
    }
