import asyncio
import pytest
from bot.engine import WeatherBot, WeatherEvent

@pytest.mark.asyncio
async def test_temp_logic():
    config = {
        "trade_amount": 10.0,
        "min_edge": 0.20,
        "scan_interval": 2,
        "paper_mode": True,
        "paper_balance": 1000.0,
        "private_key": "0x" + "0" * 64,
        "wallet_address": "0x" + "0" * 40
    }
    bot = WeatherBot(config)
    bot.is_trading = True
    bot.nasa_anomaly = 1.2 # Current global avg is 1.2 degrees above baseline (Celsius)

    # Mock Fahrenheit market
    # Threshold 80F (26.6C)
    mock_market_f = {
        "id": "temp_f",
        "question": "Will it reach 80°F in Miami?",
        "clobTokenIds": '["0xabc"]',
        "volume": "1000"
    }

    # Mock Celsius market
    # Threshold 20C
    mock_market_c = {
        "id": "temp_c",
        "question": "Will it reach 20°C in London?",
        "clobTokenIds": '["0xdef"]',
        "volume": "1000"
    }

    async def mocked_vwap(token_id, side, size):
        return 0.5

    bot.get_vwap_price = mocked_vwap

    print("Testing Fahrenheit Market (80F)...")
    # Base confidence 0.5 (even)
    await bot.execute_trade(mock_market_f, 0.5, "temperature")

    print("Testing Celsius Market (20C)...")
    # Base confidence 0.5
    await bot.execute_trade(mock_market_c, 0.5, "temperature")

    for log_msg in bot.logs:
        print(f"LOG: {log_msg}")

if __name__ == "__main__":
    asyncio.run(test_temp_logic())
