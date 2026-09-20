"""FC27 support tests for FutbinClient.

Live tests hit https://www.futbin.com and require network access.
Parser unit tests run offline against minimal markup mirroring the
real year-scoped pages (verified 2026-09-20).
"""

import pytest

from futbin_sdk import DEFAULT_YEAR, FutbinClient, FutbinError, Platform
from futbin_sdk.models import FullPlayer


def test_default_year_is_fc27():
    assert DEFAULT_YEAR == 27
    assert FutbinClient().year == 27


def test_unsupported_year_rejected():
    with pytest.raises(FutbinError):
        FutbinClient(year=20)


def test_price_box_parser_ps():
    html = """
    <html><body>
    <div class="price-box platform-ps-only price-box-original-player" data-id="1">
      <div class="price inline-with-icon lowest-price-1">227,000<img alt="Coin"></div>
      <div class="price inline-with-icon lowest-price-2">228,000<img alt="Coin"></div>
    </div>
    <div class="price-box platform-pc-only price-box-original-player" data-id="1">
      <div class="price inline-with-icon lowest-price-1">205,000<img alt="Coin"></div>
    </div>
    </body></html>
    """
    client = FutbinClient()
    ps = client._parse_price_box(html, Platform.PS)
    assert ps.price == 227000
    assert ps.min_price == 227000
    assert ps.max_price == 228000
    pc = client._parse_price_box(html, Platform.PC)
    assert pc.price == 205000


def test_price_box_parser_review_fallback():
    html = "<html><body><p>His current price on FUT is 222,000 on PlayStation, "
    html += "222,000 on Xbox, and 205,000 on PC.</p></body></html>"
    client = FutbinClient()
    assert client._parse_price_box(html, Platform.PS).price == 222000
    assert client._parse_price_box(html, Platform.XBOX).price == 222000
    assert client._parse_price_box(html, Platform.PC).price == 205000


def test_search_item_to_player_extracts_ea_id():
    item = {
        "id": 8,
        "name": "Kylian Mbappé",
        "position": "ST",
        "ratingSquare": {"rating": "91"},
        "location": {"url": "/27/player/8/kylian-mbappe"},
        "playerImage": {"fixed": {"url": {"image1x": "https://cdn3.futbin.com/x/players/231747.png"}}},
    }
    player = FutbinClient()._search_item_to_player(item, 27)
    assert isinstance(player, FullPlayer)
    assert player.futbin_id == 8
    assert player.resource_id == 231747
    assert player.rating == 91


@pytest.mark.asyncio
async def test_live_fc27_player_price():
    async with FutbinClient() as client:
        price = await client.get_player_price(8, Platform.PS)  # Mbappe FC27
        assert price.price > 0


@pytest.mark.asyncio
async def test_live_fc27_search_and_latest():
    async with FutbinClient() as client:
        hits = await client.search_players(query="Haaland")
        assert hits and hits[0].name
        latest = await client.get_latest_players(limit=5)
        assert len(latest) > 0


@pytest.mark.asyncio
async def test_live_fc27_popular_and_totw():
    async with FutbinClient() as client:
        popular = await client.get_popular_players(limit=5)
        assert len(popular) > 0
        totw = await client.get_totw()
        assert len(totw) > 0
