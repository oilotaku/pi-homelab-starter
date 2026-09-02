from __future__ import annotations

import httpx
import pytest
import respx

QBIT_BASE = "http://qbittorrent.test/api/v2"


@pytest.mark.asyncio
async def test_create_new_keyword_returns_matches(api_client: httpx.AsyncClient) -> None:
    with respx.mock(base_url=QBIT_BASE, assert_all_called=False) as mock:
        mock.get("/rss/items", params={"withData": "false"}).mock(return_value=httpx.Response(200, json={}))
        mock.post("/rss/addFeed").mock(return_value=httpx.Response(200, text="Ok."))
        mock.post("/torrents/createCategory").mock(return_value=httpx.Response(200, text="Ok."))
        mock.post("/rss/setRule").mock(return_value=httpx.Response(200, text="Ok."))
        mock.post("/rss/refreshItem").mock(return_value=httpx.Response(200, text="Ok."))
        mock.get("/rss/matchingArticles").mock(
            return_value=httpx.Response(200, json={"dmhy": ["[字幕組] 番名 - 01 [繁體][嵌字幕]"]})
        )

        resp = await api_client.post("/api/create", json={"keyword": "測試番"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["matched_count"] == 1
    assert data["matched_titles"] == ["[字幕組] 番名 - 01 [繁體][嵌字幕]"]


@pytest.mark.asyncio
async def test_create_no_matches_yet_returns_zero(api_client: httpx.AsyncClient) -> None:
    with respx.mock(base_url=QBIT_BASE, assert_all_called=False) as mock:
        mock.get("/rss/items", params={"withData": "false"}).mock(return_value=httpx.Response(200, json={}))
        mock.post("/rss/addFeed").mock(return_value=httpx.Response(200, text="Ok."))
        mock.post("/torrents/createCategory").mock(return_value=httpx.Response(200, text="Ok."))
        mock.post("/rss/setRule").mock(return_value=httpx.Response(200, text="Ok."))
        mock.post("/rss/refreshItem").mock(return_value=httpx.Response(200, text="Ok."))
        mock.get("/rss/matchingArticles").mock(return_value=httpx.Response(200, json={}))

        resp = await api_client.post("/api/create", json={"keyword": "新番"})

    assert resp.status_code == 200
    assert resp.json()["matched_count"] == 0


@pytest.mark.asyncio
async def test_create_empty_keyword_returns_400(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.post("/api/create", json={"keyword": "   "})
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_create_qbittorrent_timeout_returns_502(api_client: httpx.AsyncClient) -> None:
    with respx.mock(base_url=QBIT_BASE, assert_all_called=False) as mock:
        mock.get("/rss/items", params={"withData": "false"}).mock(side_effect=httpx.ReadTimeout("slow"))
        resp = await api_client.post("/api/create", json={"keyword": "測試番"})
    assert resp.status_code == 502
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_create_qbittorrent_5xx_returns_502(api_client: httpx.AsyncClient) -> None:
    with respx.mock(base_url=QBIT_BASE, assert_all_called=False) as mock:
        mock.get("/rss/items", params={"withData": "false"}).mock(return_value=httpx.Response(500, text="boom"))
        resp = await api_client.post("/api/create", json={"keyword": "測試番"})
    assert resp.status_code == 502
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_create_existing_category_409_is_tolerated(api_client: httpx.AsyncClient) -> None:
    with respx.mock(base_url=QBIT_BASE, assert_all_called=False) as mock:
        mock.get("/rss/items", params={"withData": "false"}).mock(return_value=httpx.Response(200, json={}))
        mock.post("/rss/addFeed").mock(return_value=httpx.Response(200, text="Ok."))
        mock.post("/torrents/createCategory").mock(return_value=httpx.Response(409, text="Conflict"))
        mock.post("/rss/setRule").mock(return_value=httpx.Response(200, text="Ok."))
        mock.post("/rss/refreshItem").mock(return_value=httpx.Response(200, text="Ok."))
        mock.get("/rss/matchingArticles").mock(return_value=httpx.Response(200, json={}))

        resp = await api_client.post("/api/create", json={"keyword": "已存在番"})

    assert resp.status_code == 200
    assert resp.json()["matched_count"] == 0


@pytest.mark.asyncio
async def test_healthz(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
