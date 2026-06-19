import json
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore as firebase_firestore

from app.core.config import get_settings


@lru_cache
def get_firebase_app() -> firebase_admin.App:
    settings = get_settings()

    if firebase_admin._apps:  # noqa: SLF001 - Firebase Admin exposes global app registry this way.
        return firebase_admin.get_app()

    options = {}
    if settings.firebase_project_id:
        options['projectId'] = settings.firebase_project_id

    if settings.firebase_service_account_json:
        service_account = json.loads(settings.firebase_service_account_json)
        cred = credentials.Certificate(service_account)
        return firebase_admin.initialize_app(cred, options=options)

    if settings.firebase_credentials_path:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        return firebase_admin.initialize_app(cred, options=options)

    # Good for Cloud Run/GCP with Application Default Credentials.
    cred = credentials.ApplicationDefault()
    return firebase_admin.initialize_app(cred, options=options)


@lru_cache
def get_firestore_client():
    get_firebase_app()
    return firebase_firestore.client()
