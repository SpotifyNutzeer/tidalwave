from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from tidalwave.db import make_engine, make_session_factory
from tidalwave.deps import get_settings
from tidalwave.routes import health


def create_app() -> FastAPI:
    settings = get_settings()
    engine = make_engine(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Resources are created eagerly below (so ASGITransport tests work without
        # lifespan events). Lifespan only disposes them on shutdown.
        yield
        await engine.dispose()

    app = FastAPI(title="tidalwave", lifespan=lifespan)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.include_router(health.router)
    return app


app = create_app()
