"""Fast, same-origin player lookup web application."""

import asyncio
import time
import unicodedata
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from futbin_sdk import FutbinClient, Platform

STATIC = Path(__file__).parent / "static"


def normalize(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c)).strip()


def relevance(player: dict[str, Any], query: str) -> tuple[int, int]:
    name, query = normalize(player["name"]), normalize(query)
    words = name.split()
    score = (
        5
        if name == query
        else 4
        if words and words[-1] == query
        else 3
        if name.startswith(query)
        else 2
        if any(w.startswith(query) for w in words)
        else 1
        if query in name
        else 0
    )
    return score, player["rating"]


def safe_image(url: str) -> str:
    parsed = urlparse(url)
    return url if parsed.scheme == "https" and (parsed.hostname or "").endswith(".futbin.com") else ""


def map_player(item: dict[str, Any]) -> dict[str, Any]:
    club = item.get("clubImage", {}).get("fixed", {})
    return {
        "id": int(item["id"]),
        "name": item.get("name", ""),
        "rating": int(item.get("ratingSquare", {}).get("rating", 0)),
        "position": item.get("position", ""),
        "version": item.get("version", ""),
        "image": safe_image(item.get("playerImage", {}).get("fixed", {}).get("url", {}).get("image1x", "")),
        "club": club.get("name", ""),
        "clubImage": safe_image(club.get("url", {}).get("night", {}).get("image1x", "")),
        "url": f"https://www.futbin.com/27/player/{int(item['id'])}/player",
    }


class Lookup:
    def __init__(self, client: FutbinClient):
        self.client = client
        self.cache: TTLCache = TTLCache(maxsize=1500, ttl=120)
        self.pending: dict[str, asyncio.Task] = {}
        self.slots = asyncio.Semaphore(5)

    async def cached(self, key, fetch):
        if key in self.cache:
            return self.cache[key]
        if key not in self.pending:

            async def run():
                try:
                    async with self.slots:
                        async with asyncio.timeout(15):
                            result = await fetch()
                    self.cache[key] = result
                    return result
                finally:
                    self.pending.pop(key, None)

            self.pending[key] = asyncio.create_task(run())
        return await asyncio.shield(self.pending[key])

    async def search(self, query):
        async def fetch():
            hits = await self.client._search_json(query, 27)
            return [map_player(h) for h in hits if str(h.get("location", {}).get("url", "")).startswith("/27/player/")]

        players = await self.cached("search:" + normalize(query), fetch)
        return sorted(players, key=lambda p: relevance(p, query), reverse=True)

    async def price(self, player_id, platform):
        async def fetch():
            price = await self.client.get_player_price(player_id, Platform(platform), year=27)
            return {"price": price.price or None, "fetchedAt": int(time.time()), "sourceUpdated": price.updated or None}

        return await self.cached(f"price:{platform}:{player_id}", fetch)


@asynccontextmanager
async def lifespan(app):
    async with FutbinClient(timeout=8, cache_ttl=120) as client:
        app.state.lookup = Lookup(client)
        yield
        tasks = list(app.state.lookup.pending.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="Touchline · FC27", lifespan=lifespan)


@app.get("/api/search")
async def search(q: str = Query(min_length=2, max_length=80)):
    if len(q.strip()) < 2:
        raise HTTPException(422, "Skriv minst två bokstäver.")
    try:
        return {"players": await app.state.lookup.search(q.strip()), "year": 27}
    except Exception as exc:
        raise HTTPException(502, "FUTBIN svarar inte just nu. Försök igen om en stund.") from exc


@app.get("/api/prices/{player_id}")
async def price(player_id: int, platform: str = Query(default="PS", pattern="^(PS|PC)$")):
    if not 0 < player_id < 10_000_000:
        raise HTTPException(400, "Ogiltigt spelar-id")
    try:
        return await app.state.lookup.price(player_id, platform)
    except Exception as exc:
        raise HTTPException(502, "Priset kunde inte hämtas.") from exc


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
