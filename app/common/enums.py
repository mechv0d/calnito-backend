from enum import StrEnum


class MealType(StrEnum):
    BREAKFAST = 'breakfast'
    SECOND_BREAKFAST = 'second_breakfast'
    LUNCH = 'lunch'
    AFTERNOON_SNACK = 'afternoon_snack'
    DINNER = 'dinner'
    SNACKS = 'snacks'


MEAL_TYPE_LABELS_RU: dict[MealType, str] = {
    MealType.BREAKFAST: 'завтрак',
    MealType.SECOND_BREAKFAST: 'второй завтрак',
    MealType.LUNCH: 'обед',
    MealType.AFTERNOON_SNACK: 'полдник',
    MealType.DINNER: 'ужин',
    MealType.SNACKS: 'снеки',
}
