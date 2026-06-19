from pydantic import BaseModel, Field, ConfigDict


class ParsedFoodItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    product_name: str = Field(min_length=1)
    portion_g: float = Field(gt=0, le=5000)
    kcal_per_100g: float = Field(ge=0, le=1000)
    confidence: float = Field(ge=0, le=1)


class ParsedMeal(BaseModel):
    model_config = ConfigDict(extra='forbid')

    items: list[ParsedFoodItem] = Field(min_length=1, max_length=20)
    notes: str | None = None


FOOD_PARSE_JSON_SCHEMA: dict = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'food_parse_result',
        'strict': True,
        'schema': {
            'type': 'object',
            'additionalProperties': False,
            'properties': {
                'items': {
                    'type': 'array',
                    'minItems': 1,
                    'maxItems': 20,
                    'items': {
                        'type': 'object',
                        'additionalProperties': False,
                        'properties': {
                            'product_name': {'type': 'string'},
                            'portion_g': {'type': 'number'},
                            'kcal_per_100g': {'type': 'number'},
                            'confidence': {'type': 'number'},
                        },
                        'required': [
                            'product_name',
                            'portion_g',
                            'kcal_per_100g',
                            'confidence',
                        ],
                    },
                },
                'notes': {'type': ['string', 'null']},
            },
            'required': ['items', 'notes'],
        },
    },
}
