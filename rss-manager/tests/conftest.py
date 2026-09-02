from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from app.config import Settings, get_settings
from app.main import app, get_client, get_sleep_fn
from app.qbittorrent_client import QbittorrentClient

QBIT_BASE = "http://qbittorrent.test/api/v2"


async def _no_sleep(_seconds: float) -> None:
    return None


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        qbit_base=QBIT_BASE,
        media_root=str(tmp_path),
        dmhy_rss="https://share.dmhy.org/topics/rss/rss.xml",
        port=5090,
    )


@pytest_asyncio.fixture
async def qbit_client(settings: Settings) -> AsyncIterator[QbittorrentClient]:
    client = QbittorrentClient(settings.qbit_base)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def api_client(qbit_client: QbittorrentClient, settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    app.dependency_overrides[get_client] = lambda: qbit_client
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_sleep_fn] = lambda: _no_sleep
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
