from functools import lru_cache
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Food AI MVP Backend'
    app_env: str = 'local'
    api_prefix: str = '/v1'
    cors_origins_raw: str = Field(default='*', alias='CORS_ORIGINS')

    firebase_project_id: str | None = Field(default=None, alias='FIREBASE_PROJECT_ID')
    firebase_credentials_path: str | None = Field(default=None, alias='FIREBASE_CREDENTIALS_PATH')
    firebase_service_account_json: str | None = Field(default=None, alias='FIREBASE_SERVICE_ACCOUNT_JSON')
    firebase_check_revoked: bool = Field(default=False, alias='FIREBASE_CHECK_REVOKED')

    supabase_url: str = Field(alias='SUPABASE_URL')
    # New Supabase API keys use sb_secret_... for trusted server-side code.
    # SUPABASE_SERVICE_ROLE_KEY is kept only as a temporary compatibility fallback for older projects.
    supabase_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices('SUPABASE_SECRET_KEY', 'SUPABASE_SERVICE_ROLE_KEY'),
    )
    supabase_storage_bucket: str = Field(default='meal-photos', alias='SUPABASE_STORAGE_BUCKET')
    signed_url_expires_seconds: int = Field(default=3600, alias='SIGNED_URL_EXPIRES_SECONDS')

    # Vendor-neutral LLM settings. The app uses the OpenAI-compatible Python client,
    # but LLM_BASE_URL may point to any OpenAI-compatible endpoint.
    # Legacy OPENAI_* names are accepted as compatibility fallbacks.
    llm_api_key: str = Field(validation_alias=AliasChoices('LLM_API_KEY', 'OPENAI_API_KEY'))
    llm_base_url: str | None = Field(default=None, validation_alias=AliasChoices('LLM_BASE_URL', 'OPENAI_BASE_URL'))
    llm_model: str = Field(default='gpt-4.1-mini', validation_alias=AliasChoices('LLM_MODEL', 'OPENAI_MODEL'))
    llm_recommendation_model: str = Field(
        default='gpt-4.1-mini',
        validation_alias=AliasChoices('LLM_RECOMMENDATION_MODEL', 'OPENAI_RECOMMENDATION_MODEL'),
    )
    llm_timeout_seconds: float = Field(default=45.0, validation_alias=AliasChoices('LLM_TIMEOUT_SECONDS', 'OPENAI_TIMEOUT_SECONDS'))
    llm_max_retries: int = Field(default=1, validation_alias=AliasChoices('LLM_MAX_RETRIES', 'OPENAI_MAX_RETRIES'))

    default_timezone: str = Field(default='UTC', alias='DEFAULT_TIMEZONE')
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, alias='MAX_UPLOAD_BYTES')
    max_image_side_px: int = Field(default=1200, alias='MAX_IMAGE_SIDE_PX')
    webp_quality: int = Field(default=75, alias='WEBP_QUALITY')

    user_facing_ai_error: str = Field(default='Мы проебались, Босс.', alias='USER_FACING_AI_ERROR')


    @model_validator(mode='after')
    def validate_supabase_secret_key(self):
        if not self.supabase_secret_key:
            raise ValueError('Set SUPABASE_SECRET_KEY. Legacy SUPABASE_SERVICE_ROLE_KEY is accepted only for older projects.')
        return self

    @property
    def cors_origins(self) -> list[str]:
        raw = self.cors_origins_raw.strip()
        if raw == '*':
            return ['*']
        return [origin.strip() for origin in raw.split(',') if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
