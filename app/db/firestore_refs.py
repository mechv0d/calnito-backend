from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.firebase import get_firestore_client


def user_doc(uid: str):
    return get_firestore_client().collection('users').document(uid)


def meals_collection(uid: str):
    return user_doc(uid).collection('meals')


def meal_doc(uid: str, meal_id: str):
    return meals_collection(uid).document(meal_id)


__all__ = [
    'FieldFilter',
    'get_firestore_client',
    'user_doc',
    'meals_collection',
    'meal_doc',
]
