from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app


DT = datetime(2026, 6, 19, 9, 0, tzinfo=timezone.utc)


MEAL_RESPONSE = {
    "id": "meal-1",
    "meal_type": "breakfast",
    "meal_type_label": "завтрак",
    "date_local": "2026-06-19",
    "consumed_at": DT.isoformat(),
    "created_at": DT.isoformat(),
    "updated_at": DT.isoformat(),
    "description": "омлет",
    "items": [
        {
            "product_name": "омлет",
            "portion_g": 180,
            "kcal_per_100g": 154,
            "calories": 277.2,
            "confidence": 0.9,
        }
    ],
    "totals": {"calories": 277.2, "products_count": 1, "total_weight_g": 180},
    "photo": None,
}


class FakeMealService:
    async def create_meal(self, uid, description, timezone_name, photo):
        assert uid == "u1"
        assert description == "омлет"
        return MEAL_RESPONSE

    def get_today_summary(self, uid, timezone_name):
        return {
            "date": "2026-06-19",
            "total_calories": 277.2,
            "by_meal_type": {"breakfast": 277.2},
            "meals_count": 1,
            "meals": [MEAL_RESPONSE],
        }

    def get_by_day(self, uid, date_local):
        return {"date": date_local, "meals": [MEAL_RESPONSE], "total_calories": 277.2}

    def get_between_days(self, uid, date_from, date_to):
        return {"date_from": date_from, "date_to": date_to, "meals": [MEAL_RESPONSE], "total_calories": 277.2}

    def get_meal(self, uid, meal_id):
        return MEAL_RESPONSE

    def get_meal_photo_url(self, uid, meal_id):
        return {
            "meal_id": meal_id,
            "storage_path": "users/u1/meals/meal-1/photo.webp",
            "signed_url": "https://signed.test/photo.webp",
            "expires_in_seconds": 3600,
        }

    def update_meal(self, uid, meal_id, payload, timezone_name):
        return {**MEAL_RESPONSE, "meal_type": payload.meal_type or MEAL_RESPONSE["meal_type"]}

    def delete_meal(self, uid, meal_id):
        return {"ok": True, "deleted_id": meal_id}


class FakeStatsService:
    def build_stats(self, uid, date_from, date_to):
        return {
            "period": {"date_from": date_from, "date_to": date_to},
            "totals": {"calories": 277.2, "meals_count": 1, "days_count": 1, "products_count": 1},
            "averages": {
                "calories_per_day": 277.2,
                "calories_per_meal": 277.2,
                "products_per_meal": 1,
                "weight_per_meal_g": 180,
            },
            "calories_by_day": {"2026-06-19": 277.2},
            "calories_by_meal_type": {"breakfast": 277.2},
            "top_products_by_frequency": [["омлет", 1]],
            "top_products_by_calories": [{"product_name": "омлет", "calories": 277.2}],
        }


class FakeRecommendationService:
    def weekly_recommendations(self, uid, timezone_name):
        return {"text": "Все норм.", "meals_analyzed": 1, "period": {"from": "2026-06-13", "to": "2026-06-19"}}


class FakeUserService:
    def get_or_create_profile(self, uid, email):
        return {"uid": uid, "email": email, "timezone": "UTC", "created_at": DT, "updated_at": DT}

    def update_profile(self, uid, email, timezone_name):
        return {"uid": uid, "email": email, "timezone": timezone_name, "created_at": DT, "updated_at": DT}


def override_user():
    return CurrentUser(uid="u1", email="u1@example.com")


def make_client(monkeypatch):
    import app.meals.router as meals_router
    import app.stats.router as stats_router
    import app.recommendations.router as recommendations_router
    import app.users.router as users_router

    monkeypatch.setattr(meals_router, "MealService", FakeMealService)
    monkeypatch.setattr(stats_router, "StatsService", FakeStatsService)
    monkeypatch.setattr(recommendations_router, "RecommendationService", FakeRecommendationService)
    monkeypatch.setattr(users_router, "UserService", FakeUserService)
    app.dependency_overrides[get_current_user] = override_user
    return TestClient(app)


def test_healthcheck():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_meals_endpoints(monkeypatch):
    with make_client(monkeypatch) as client:
        assert client.post("/v1/meals", data={"description": "омлет"}).status_code == 201
        assert client.get("/v1/meals/today").json()["total_calories"] == 277.2
        assert client.get("/v1/meals/by-day?date=2026-06-19").json()["date"] == "2026-06-19"
        assert client.get("/v1/meals?from=2026-06-19&to=2026-06-19").json()["total_calories"] == 277.2
        assert client.get("/v1/meals/meal-1").json()["id"] == "meal-1"
        assert client.get("/v1/meals/meal-1/photo-url").json()["signed_url"] == "https://signed.test/photo.webp"
        assert client.patch("/v1/meals/meal-1", json={"meal_type": "snacks"}).json()["meal_type"] == "snacks"
        assert client.delete("/v1/meals/meal-1").json() == {"ok": True, "deleted_id": "meal-1"}


def test_stats_recommendations_and_users_endpoints(monkeypatch):
    with make_client(monkeypatch) as client:
        assert client.get("/v1/stats?from=2026-06-19&to=2026-06-19").json()["totals"]["meals_count"] == 1
        assert client.post("/v1/recommendations").json()["text"] == "Все норм."
        assert client.get("/v1/users/me").json()["uid"] == "u1"
        assert client.patch("/v1/users/me", json={"timezone": "Europe/Helsinki"}).json()["timezone"] == "Europe/Helsinki"


def test_dependency_overrides_are_cleaned():
    app.dependency_overrides.clear()
