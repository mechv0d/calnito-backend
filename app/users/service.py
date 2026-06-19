from fastapi import HTTPException

from app.common.time import get_zoneinfo, now_utc
from app.db.firestore_refs import user_doc


class UserService:
    def get_or_create_profile(self, uid: str, email: str | None) -> dict:
        ref = user_doc(uid)
        snapshot = ref.get()
        if snapshot.exists:
            data = snapshot.to_dict()
            return {
                'uid': uid,
                'email': data.get('email') or email,
                'timezone': data.get('timezone'),
                'created_at': data.get('created_at'),
                'updated_at': data.get('updated_at'),
            }

        current = now_utc()
        data = {
            'uid': uid,
            'email': email,
            'timezone': None,
            'created_at': current,
            'updated_at': current,
        }
        ref.set(data)
        return data

    def update_profile(self, uid: str, email: str | None, timezone_name: str) -> dict:
        try:
            get_zoneinfo(timezone_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail='Invalid timezone') from exc

        current = now_utc()
        ref = user_doc(uid)
        data = {
            'uid': uid,
            'email': email,
            'timezone': timezone_name,
            'updated_at': current,
        }
        if not ref.get().exists:
            data['created_at'] = current
        ref.set(data, merge=True)
        return self.get_or_create_profile(uid, email)
