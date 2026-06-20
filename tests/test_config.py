from app.core.config import Settings


def test_supabase_url_strips_api_suffix():
    settings = Settings(
        SUPABASE_URL='https://example.supabase.co/rest/v1',
        SUPABASE_SECRET_KEY='sb_secret_test',
        LLM_API_KEY='test-llm-key',
    )

    assert settings.supabase_url == 'https://example.supabase.co'


def test_supabase_url_strips_trailing_slash():
    settings = Settings(
        SUPABASE_URL='https://example.supabase.co/',
        SUPABASE_SECRET_KEY='sb_secret_test',
        LLM_API_KEY='test-llm-key',
    )

    assert settings.supabase_url == 'https://example.supabase.co'
