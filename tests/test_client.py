"""Tests for FutbinClient"""

import pytest

from futbin_sdk import FutbinClient, FutbinError, Platform, PlayerSearchOptions


@pytest.mark.asyncio
async def test_get_popular_players():
    """测试获取热门球员"""
    async with FutbinClient() as client:
        players = await client.get_popular_players()
        assert len(players) > 0
        assert players[0].futbin_id > 0


@pytest.mark.asyncio
async def test_get_player_price():
    """测试获取球员价格"""
    async with FutbinClient() as client:
        # 使用热门球员测试
        popular = await client.get_popular_players()
        if popular:
            player_id = popular[0].futbin_id
            price = await client.get_player_price(player_id, Platform.PS)
            assert price.price >= 0


@pytest.mark.asyncio
async def test_get_players_prices():
    """测试批量获取球员价格"""
    async with FutbinClient() as client:
        popular = await client.get_popular_players()
        if len(popular) >= 3:
            player_ids = [p.futbin_id for p in popular[:3]]
            prices = await client.get_players_prices(player_ids, Platform.PS)
            assert len(prices) == 3


@pytest.mark.asyncio
async def test_search_players():
    """测试搜索球员"""
    async with FutbinClient() as client:
        # 使用默认参数搜索
        players = await client.search_players()
        assert len(players) > 0
        assert players[0].futbin_id > 0
        assert players[0].name != ""


@pytest.mark.asyncio
async def test_search_players_with_options():
    """测试使用选项搜索球员"""
    async with FutbinClient() as client:
        options = PlayerSearchOptions(
            platform="PS",
            page=1,
            min_rating=85,
        )
        players = await client.search_players(options=options)
        assert len(players) > 0
        # 验证所有球员评分 >= 85
        for player in players:
            assert player.rating >= 85


@pytest.mark.asyncio
async def test_get_totw():
    """测试获取本周最佳球员"""
    async with FutbinClient() as client:
        players = await client.get_totw()
        # TOTW 可能为空（赛季间隙）
        if players:
            assert players[0].futbin_id > 0
            assert players[0].name != ""


@pytest.mark.asyncio
async def test_get_latest_players():
    """测试获取最新球员"""
    async with FutbinClient() as client:
        players = await client.get_latest_players()
        assert len(players) > 0
        assert players[0].futbin_id > 0
        assert players[0].name != ""


@pytest.mark.asyncio
async def test_get_leagues_and_clubs():
    """Legacy endpoint shut down with futbin.org (raises FutbinError)."""
    async with FutbinClient() as client:
        with pytest.raises(FutbinError):
            await client.get_leagues_and_clubs()


@pytest.mark.asyncio
async def test_get_card_versions():
    """Legacy endpoint shut down with futbin.org (raises FutbinError)."""
    async with FutbinClient() as client:
        with pytest.raises(FutbinError):
            await client.get_card_versions()
