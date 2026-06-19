from app.common.enums import MEAL_TYPE_LABELS_RU, MealType
from app.meals.serializers import meal_to_response_dict


def test_meal_to_response_dict_adds_ru_label_and_signed_url(sample_meal, dummy_storage):
    response = meal_to_response_dict(sample_meal, dummy_storage)

    assert response["meal_type"] == "breakfast"
    assert response["meal_type_label"] == MEAL_TYPE_LABELS_RU[MealType.BREAKFAST]
    assert response["photo"] == {
        "storage_path": "users/user-1/meals/meal-1/photo.webp",
        "signed_url": "https://signed.test/users/user-1/meals/meal-1/photo.webp",
        "width": 1200,
        "height": 800,
    }


def test_meal_to_response_dict_omits_photo_when_no_storage_path(sample_meal, dummy_storage):
    sample_meal["photo"] = {"storage_path": None}

    response = meal_to_response_dict(sample_meal, dummy_storage)

    assert response["photo"] is None
