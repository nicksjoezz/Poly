import pytest
import asyncio
from bot.engine import WeatherBot

@pytest.mark.asyncio
async def test_bot_initialization():
    config = {
        "paper_balance": 1000.0,
        "paper_mode": True,
        "max_trades": 10,
        "trade_amount": 10.0,
        "min_edge": 0.05,
        "scan_interval": 5
    }
    bot = WeatherBot(config)
    assert bot.metrics["balance"] == 1000.0
    assert bot.is_running is False
    assert bot.config["paper_mode"] is True

@pytest.mark.asyncio
async def test_numeric_parsing_logic():
    config = {"trade_amount": 10.0}
    bot = WeatherBot(config)

    # Temperatures
    res = bot.parse_numeric_threshold("Will it be 80°F or more?")
    assert res["type"] == "at_least"
    assert res["value"] == 80.0
    assert res["unit"] == "F"

    res = bot.parse_numeric_threshold("between 1.15 and 1.20 C")
    assert res["type"] == "range"
    assert res["min"] == 1.15
    assert res["max"] == 1.20
    assert res["unit"] == "C"

    # Precipitation
    res = bot.parse_numeric_threshold("less than 3 inches of rain")
    assert res["type"] == "less_than"
    assert res["value"] == 3.0
    assert res["unit"] == "inch"

    res = bot.parse_numeric_threshold("8 inches or more")
    assert res["type"] == "at_least"
    assert res["value"] == 8.0
    assert res["unit"] == "inch"

def test_parse_numeric_as_method():
    config = {"trade_amount": 10.0}
    bot = WeatherBot(config)
    assert bot.parse_numeric_threshold("Will it be 1.15 C?")["value"] == 1.15
    assert bot.parse_numeric_threshold("Temperature above 0.5 degrees")["value"] == 0.5
    assert bot.parse_numeric_threshold("No number here") is None

def test_parse_market_date():
    config = {}
    bot = WeatherBot(config)
    assert bot.parse_market_date("March 19, 2026") == "2026-03-19"
    assert bot.parse_market_date("in March") == "2026-03"
    assert bot.parse_market_date("in 2027") == "2027"

def test_parse_market_location():
    config = {}
    bot = WeatherBot(config)
    assert bot.parse_market_location("Will it rain in New York City?") == "new york"
    assert bot.parse_market_location("Global temperature rise") == "global"
    assert bot.parse_market_location("Earthquakes in Tokyo") == "tokyo"
