# Фото и Supabase Storage

## Что происходит с фото

При `POST /v1/meals` backend:

1. принимает файл `photo` из `multipart/form-data`;
2. проверяет content type: `image/jpeg`, `image/png`, `image/webp`;
3. проверяет размер: максимум `MAX_UPLOAD_BYTES`;
4. открывает картинку через Pillow;
5. применяет EXIF orientation;
6. конвертирует в RGB;
7. уменьшает большую сторону до `MAX_IMAGE_SIDE_PX`, по умолчанию `1200`;
8. сохраняет в WebP с `WEBP_QUALITY=75`;
9. убирает EXIF/ICC metadata;
10. загружает в private Supabase Storage bucket;
11. сохраняет `storage_path`, `width`, `height` в Firestore.

## Bucket

Рекомендуемый bucket:

```text
meal-photos
```

Bucket должен быть private.

## Storage path

Формат пути:

```text
users/{uid}/meals/{meal_id}/{uuid}.webp
```

Пример:

```text
users/firebase_uid_123/meals/7f4a3e2d7e2a4d79a3ff4b78d8d20a11/abc123.webp
```

## Signed URL

В API response приходит:

```json
{
  "photo": {
    "storage_path": "users/firebase_uid_123/meals/meal_id/photo.webp",
    "signed_url": "https://your-project.supabase.co/storage/v1/object/sign/...",
    "width": 1200,
    "height": 900
  }
}
```

`signed_url` живет `SIGNED_URL_EXPIRES_SECONDS`, по умолчанию 3600 секунд.

Frontend должен использовать `signed_url` для отображения картинки. Если URL протух, надо заново запросить прием пищи:

```http
GET /v1/meals/{meal_id}
```

или день:

```http
GET /v1/meals/by-day?date=2026-06-19
```

Backend выдаст новый signed URL.

## Удаление

При:

```http
DELETE /v1/meals/{meal_id}
```

backend удаляет Firestore документ и файл из Supabase Storage.

## AI failure после upload-а

Если фото уже загружено, но LLM затем упал, backend пытается удалить orphan-файл.
