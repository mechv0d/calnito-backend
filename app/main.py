import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.warmup import warm_backend_dependencies

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.middleware('http')
    async def add_request_timing(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers['X-Process-Time-Ms'] = f'{elapsed_ms:.1f}'

        if request.url.path.startswith(settings.api_prefix):
            log = logger.warning if elapsed_ms >= 1000 else logger.info
            log(
                'HTTP %s %s -> %s %.1fms',
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )

        return response

    @app.on_event('startup')
    def startup_warmup() -> None:
        warm_backend_dependencies()

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
