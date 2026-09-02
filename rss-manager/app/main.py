from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .qbittorrent_client import QbittorrentClient, QbittorrentError, QbittorrentTimeoutError
from .schemas import CreateRequest, CreateResponse
from .service import SleepFn, create_rule

_client: QbittorrentClient | None = None


def get_client() -> QbittorrentClient:
    assert _client is not None, "QbittorrentClient 尚未初始化"
    return _client


def get_sleep_fn() -> SleepFn:
    return asyncio.sleep


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _client
    settings = get_settings()
    _client = QbittorrentClient(settings.qbit_base)
    try:
        yield
    finally:
        await _client.aclose()
        _client = None


app = FastAPI(title="rss-manager", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    message = str(exc.errors()[0].get("msg", "invalid request"))
    if message.startswith("Value error, "):
        message = message[len("Value error, ") :]
    return JSONResponse(status_code=400, content={"error": message})


@app.exception_handler(QbittorrentTimeoutError)
async def qbit_timeout_handler(request: Request, exc: QbittorrentTimeoutError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"error": f"qBittorrent API 逾時: {exc}"})


@app.exception_handler(QbittorrentError)
async def qbit_error_handler(request: Request, exc: QbittorrentError) -> JSONResponse:
    return JSONResponse(
        status_code=502, content={"error": f"qBittorrent API 錯誤: {exc.status_code} {exc.detail}"}
    )


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/create", response_model=CreateResponse)
async def api_create(
    payload: CreateRequest,
    client: QbittorrentClient = Depends(get_client),
    settings: Settings = Depends(get_settings),
    sleep: SleepFn = Depends(get_sleep_fn),
) -> CreateResponse:
    result = await create_rule(payload.keyword, client=client, settings=settings, sleep=sleep)
    return CreateResponse(**result)
