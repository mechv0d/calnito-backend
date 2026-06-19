import json
from types import SimpleNamespace

import pytest

import app.llm.client as llm_module
from app.common.enums import MealType
from app.llm.client import AIClient
from app.llm.exceptions import AIExhaustedError


class FakeCompletions:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=output))]
        )


class FakeOpenAI:
    last_instance = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.chat = SimpleNamespace(completions=FakeCompletions([]))
        FakeOpenAI.last_instance = self


def install_fake_openai(monkeypatch, outputs):
    class ConfiguredFakeOpenAI(FakeOpenAI):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.chat = SimpleNamespace(completions=FakeCompletions(outputs))
            ConfiguredFakeOpenAI.last_instance = self

    ConfiguredFakeOpenAI.last_instance = None
    monkeypatch.setattr(llm_module, "OpenAI", ConfiguredFakeOpenAI)
    monkeypatch.setattr(llm_module.time, "sleep", lambda seconds: None)
    return ConfiguredFakeOpenAI


def test_ai_client_uses_custom_base_url(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://provider.example/v1")
    fake_cls = install_fake_openai(monkeypatch, [])

    AIClient()

    assert fake_cls.last_instance.kwargs["base_url"] == "https://provider.example/v1"
    assert fake_cls.last_instance.kwargs["api_key"] == "test-llm-key"
    assert fake_cls.last_instance.kwargs["max_retries"] == 0


def test_parse_food_retries_invalid_json_then_returns_valid_result(monkeypatch):
    valid = json.dumps(
        {
            "items": [
                {
                    "product_name": "омлет",
                    "portion_g": 180,
                    "kcal_per_100g": 154,
                    "confidence": 0.9,
                }
            ],
            "notes": None,
        },
        ensure_ascii=False,
    )
    fake_cls = install_fake_openai(monkeypatch, ["not-json", valid])

    result = AIClient().parse_food(
        description="омлет",
        meal_type=MealType.BREAKFAST,
        recent_products=[],
        same_type_products=[],
        image_webp_bytes=b"fake-webp",
    )

    completions = fake_cls.last_instance.chat.completions
    assert len(completions.calls) == 2
    assert result.items[0].product_name == "омлет"
    user_content = completions.calls[-1]["messages"][1]["content"]
    assert user_content[1]["type"] == "image_url"
    assert completions.calls[-1]["response_format"]["type"] == "json_schema"


def test_parse_food_raises_ai_exhausted_after_all_retries(monkeypatch):
    install_fake_openai(monkeypatch, [RuntimeError("timeout"), RuntimeError("timeout again")])

    with pytest.raises(AIExhaustedError):
        AIClient().parse_food("еда", MealType.DINNER, [], [])


def test_generate_recommendations_strips_text(monkeypatch):
    fake_cls = install_fake_openai(monkeypatch, ["  Ешь больше овощей.  "])

    text = AIClient().generate_recommendations([{"description": "еда"}])

    assert text == "Ешь больше овощей."
    assert fake_cls.last_instance.chat.completions.calls[0]["model"] == "test-recommendation-model"
