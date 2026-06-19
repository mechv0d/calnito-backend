from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

import app.meals.service as service_module
from app.common.enums import MealType
from app.llm.exceptions import AIExhaustedError
from app.llm.schemas import ParsedFoodItem, ParsedMeal
from app.meals.models import MealItemUpdate, MealUpdateRequest
from app.meals.service import MealService


class FakeRepo:
    def __init__(self, existing=None):
        self.existing = existing
        self.created = []
        self.updated_payload = None
        self.deleted = None
        self.by_day = []
        self.between = []

    def create(self, uid, meal_id, data):
        self.created.append((uid, meal_id, data))
        self.existing = data

    def get(self, uid, meal_id):
        return self.existing

    def update(self, uid, meal_id, data):
        if self.existing is None:
            return None
        self.updated_payload = data
        self.existing = {**self.existing, **data}
        return self.existing

    def delete(self, uid, meal_id):
        old = self.existing
        self.existing = None
        return old

    def list_by_day(self, uid, date_local):
        return self.by_day

    def list_between_days(self, uid, date_from, date_to):
        return self.between


class FakeContext:
    def recent_products(self, uid, limit):
        return [{"product_name": "хлеб", "kcal_per_100g": 250}]

    def recent_products_by_type(self, uid, meal_type, limit):
        return [{"product_name": "омлет", "kcal_per_100g": 154}]


class FakeAI:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def parse_food(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise AIExhaustedError("dead")
        return ParsedMeal(
            items=[
                ParsedFoodItem(
                    product_name="Омлет",
                    portion_g=180,
                    kcal_per_100g=154,
                    confidence=0.9,
                )
            ],
            notes="ok",
        )


def make_service(repo, storage, ai=None):
    service = object.__new__(MealService)
    service.settings = SimpleNamespace(max_upload_bytes=10, llm_model="test-food-model")
    service.repo = repo
    service.storage = storage
    service.context = FakeContext()
    service.ai = ai or FakeAI()
    return service


@pytest.mark.asyncio
async def test_create_meal_success_saves_firestore_doc_and_returns_signed_url(
    monkeypatch,
    dummy_storage,
    frozen_dt,
):
    monkeypatch.setattr(service_module, "now_utc", lambda: frozen_dt)
    monkeypatch.setattr(service_module, "uuid4", lambda: SimpleNamespace(hex="meal-fixed"))
    repo = FakeRepo()
    service = make_service(repo, dummy_storage)

    result = await service.create_meal(
        uid="u1",
        description="омлет",
        timezone_name="UTC",
        photo=None,
    )

    saved = repo.created[0][2]
    assert saved["id"] == "meal-fixed"
    assert saved["meal_type"] == "breakfast"
    assert saved["llm"]["model"] == "test-food-model"
    assert saved["items"][0]["product_name"] == "омлет"
    assert saved["totals"]["calories"] == 277.2
    assert result["photo"] is None


@pytest.mark.asyncio
async def test_create_meal_ai_failure_removes_uploaded_photo_and_returns_boss_error(
    monkeypatch,
    dummy_storage,
    frozen_dt,
):
    monkeypatch.setattr(service_module, "now_utc", lambda: frozen_dt)
    monkeypatch.setattr(service_module, "process_food_photo", lambda raw: SimpleNamespace(bytes=b"webp", width=1, height=1))
    repo = FakeRepo()
    service = make_service(repo, dummy_storage, ai=FakeAI(fail=True))
    upload = UploadFile(filename="food.jpg", file=__import__("io").BytesIO(b"abc"), headers={"content-type": "image/jpeg"})

    with pytest.raises(HTTPException) as exc:
        await service.create_meal("u1", "еда", "UTC", upload)

    assert exc.value.status_code == 503
    assert exc.value.detail == "Мы проебались, Босс."
    assert dummy_storage.removed == ["users/u1/meals/" + repo.created[0][1] + "/photo.webp"] if repo.created else dummy_storage.removed
    assert dummy_storage.removed[0].endswith("/photo.webp")
    assert repo.created == []


def test_update_meal_manual_items_recalculates_totals(sample_meal, dummy_storage):
    repo = FakeRepo(existing=sample_meal)
    service = make_service(repo, dummy_storage)
    payload = MealUpdateRequest(
        items=[MealItemUpdate(product_name="хлеб", portion_g=40, kcal_per_100g=250, confidence=1)]
    )

    result = service.update_meal("u1", "meal-1", payload, timezone_name="UTC")

    assert repo.updated_payload["manual_edited"] is True
    assert repo.updated_payload["totals"] == {"calories": 100, "products_count": 1, "total_weight_g": 40}
    assert result["items"][0]["product_name"] == "хлеб"


def test_update_meal_rejects_manual_time_for_non_snack(sample_meal, dummy_storage):
    repo = FakeRepo(existing=sample_meal)
    service = make_service(repo, dummy_storage)
    payload = MealUpdateRequest(consumed_at="2026-06-19T21:30:00+03:00")

    with pytest.raises(HTTPException) as exc:
        service.update_meal("u1", "meal-1", payload, timezone_name="Europe/Helsinki")

    assert exc.value.status_code == 400


def test_update_meal_allows_manual_time_for_snacks(sample_meal, dummy_storage):
    sample_meal["meal_type"] = MealType.SNACKS.value
    repo = FakeRepo(existing=sample_meal)
    service = make_service(repo, dummy_storage)
    payload = MealUpdateRequest(consumed_at="2026-06-19T21:30:00+03:00")

    result = service.update_meal("u1", "meal-1", payload, timezone_name="Europe/Helsinki")

    assert repo.updated_payload["consumed_at"] == datetime(2026, 6, 19, 18, 30, tzinfo=timezone.utc)
    assert result["date_local"] == "2026-06-19"


def test_delete_meal_removes_photo(sample_meal, dummy_storage):
    repo = FakeRepo(existing=sample_meal)
    service = make_service(repo, dummy_storage)

    assert service.delete_meal("u1", "meal-1") == {"ok": True, "deleted_id": "meal-1"}
    assert dummy_storage.removed == ["users/user-1/meals/meal-1/photo.webp"]


def test_get_today_summary_aggregates_by_type(sample_meal, dummy_storage, frozen_dt, monkeypatch):
    monkeypatch.setattr(service_module, "now_utc", lambda: frozen_dt)
    snack = {**sample_meal, "id": "meal-2", "meal_type": "snacks", "totals": {"calories": 50}}
    repo = FakeRepo()
    repo.by_day = [sample_meal, snack]
    service = make_service(repo, dummy_storage)

    result = service.get_today_summary("u1", "UTC")

    assert result["total_calories"] == 327.2
    assert result["by_meal_type"]["breakfast"] == 277.2
    assert result["by_meal_type"]["snacks"] == 50
    assert result["meals_count"] == 2


def test_get_meal_404_when_missing(dummy_storage):
    service = make_service(FakeRepo(existing=None), dummy_storage)

    with pytest.raises(HTTPException) as exc:
        service.get_meal("u1", "missing")

    assert exc.value.status_code == 404
