from datetime import datetime

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    uid: str
    email: str | None = None
    timezone: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserProfileUpdate(BaseModel):
    timezone: str = Field(min_length=1, max_length=80)
