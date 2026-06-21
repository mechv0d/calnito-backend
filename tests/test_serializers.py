from app.common.enums import MEAL_TYPE_LABELS_RU, MealType
from app.meals.serializers import meal_to_response_dict


def test_meal_to_response_dict_adds_ru_label_without_signing_by_default(sample_meal, dummy_storage):
    response = meal_to_response_dict(sample_meal, dummy_storage)

    assert response["meal_type"] == "breakfast"
    assert response["meal_type_label"] == MEAL_TYPE_LABELS_RU[MealType.BREAKFAST]
    assert response["photo"] == {
        "storage_path": "users/user-1/meals/meal-1/photo.webp",
        "signed_url": None,
        "width": 1200,
        "height": 800,
    }


def test_meal_to_response_dict_can_include_signed_url(sample_meal, dummy_storage):
    response = meal_to_response_dict(sample_meal, dummy_storage, include_photo_url=True)

    assert response["photo"]["signed_url"] == "https://signed.test/users/user-1/meals/meal-1/photo.webp"


def test_meal_to_response_dict_does_not_fail_when_signed_url_fails(sample_meal):
    class BrokenStorage:
        def create_signed_url(self, path):
            raise TimeoutError("supabase timed out")

    response = meal_to_response_dict(sample_meal, BrokenStorage(), include_photo_url=True)

    assert response["photo"]["storage_path"] == "users/user-1/meals/meal-1/photo.webp"
    assert response["photo"]["signed_url"] is None


def test_meal_to_response_dict_omits_photo_when_no_storage_path(sample_meal, dummy_storage):
    sample_meal["photo"] = {"storage_path": None}

    response = meal_to_response_dict(sample_meal, dummy_storage)

    assert response["photo"] is None
