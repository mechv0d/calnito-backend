import base64
import json
import logging
import time

from openai import OpenAI
from pydantic import ValidationError

from app.common.enums import MealType
from app.core.config import get_settings
from app.llm.exceptions import AIExhaustedError
from app.llm.prompts import build_food_parse_prompt, build_next_meal_recommendation_prompt, build_recommendation_prompt
from app.llm.schemas import FOOD_PARSE_JSON_SCHEMA, ParsedMeal

from app.llm.food_response_normalizer import normalize_food_parse_payload

logger = logging.getLogger(__name__)

def clean_json_text(text: str) -> str:
    text = text.strip()

    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()

    if text.startswith("```"):
        text = text.removeprefix("```").strip()

    if text.endswith("```"):
        text = text.removesuffix("```").strip()

    return text

def extract_llm_text(response) -> str:
    """
    Supports both:
    - OpenAI Responses API: response.output_text
    - OpenAI-compatible Chat Completions: response.choices[0].message.content
    """

    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    choices = getattr(response, "choices", None)
    if choices:
        message = choices[0].message
        content = message.content

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            return "".join(parts)

    raise ValueError("LLM response does not contain text")


class AIClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        client_kwargs = {
            'api_key': self.settings.llm_api_key,
            'timeout': self.settings.llm_timeout_seconds,
            'max_retries': 0,  # свои ретраи, чтобы ловить невалидный JSON так же, как timeout.
        }
        if self.settings.llm_base_url:
            client_kwargs['base_url'] = self.settings.llm_base_url

        self.client = OpenAI(**client_kwargs)

    def parse_food(
        self,
        description: str,
        meal_type: MealType,
        recent_products: list[dict],
        same_type_products: list[dict],
        image_webp_bytes: bytes | None = None,
    ) -> ParsedMeal:
        prompt = build_food_parse_prompt(
            description=description,
            current_meal_type=meal_type,
            recent_products=recent_products,
            same_type_products=same_type_products,
        )

        attempts = self.settings.llm_max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                return self._parse_food_once(prompt, image_webp_bytes)
            except (Exception, ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning('Food AI parse failed on attempt %s/%s: %r', attempt, attempts, exc)
                if attempt < attempts:
                    time.sleep(min(0.5 * attempt, 2.0))

        raise AIExhaustedError('Food AI parse failed after all retries') from last_error

    def _parse_food_once(self, prompt: str, image_webp_bytes: bytes | None) -> ParsedMeal:
        user_content: list[dict] = [{'type': 'text', 'text': prompt}]

        if image_webp_bytes:
            b64 = base64.b64encode(image_webp_bytes).decode('utf-8')
            user_content.append({
                'type': 'image_url',
                'image_url': {'url': f'data:image/webp;base64,{b64}'},
            })

        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {
                    'role': 'system',
                    'content': 'Ты точный backend parser. Отвечай только валидными структурированными данными.',
                },
                {'role': 'user', 'content': user_content},
            ],
            response_format=FOOD_PARSE_JSON_SCHEMA,
            temperature=0.13,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError('Empty AI response')

        raw_text = clean_json_text(extract_llm_text(response))
        data = json.loads(raw_text)
        normalized_data = normalize_food_parse_payload(data)
        return ParsedMeal.model_validate(normalized_data)

    def generate_recommendations(self, payload: dict) -> str:
        return self._generate_text_recommendation(
            prompt=build_recommendation_prompt(payload),
            model=self.settings.llm_recommendation_model,
            log_label='general recommendation',
        )

    def generate_next_meal_recommendation(self, payload: dict) -> str:
        return self._generate_text_recommendation(
            prompt=build_next_meal_recommendation_prompt(payload),
            model=self.settings.llm_next_meal_recommendation_model,
            log_label='next meal recommendation',
        )

    def _generate_text_recommendation(self, prompt: str, model: str, log_label: str) -> str:
        attempts = self.settings.llm_max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            'role': 'system',
                            'content': 'Ты аккуратный помощник по питанию. Не давай медицинских диагнозов.',
                        },
                        {'role': 'user', 'content': prompt},
                    ],
                    temperature=0.6,
                )
                content = response.choices[0].message.content
                if not content:
                    raise ValueError('Empty AI recommendation')
                return content.strip()
            except Exception as exc:
                last_error = exc
                logger.warning('%s AI failed on attempt %s/%s: %r', log_label, attempt, attempts, exc)
                if attempt < attempts:
                    time.sleep(min(0.5 * attempt, 2.0))

        raise AIExhaustedError(f'{log_label} AI failed after all retries') from last_error
