import asyncio
from bot.engine import WeatherBot, WeatherEvent

async def test_matching():
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

    # Mock data
    mock_event = WeatherEvent(
        source="NOAA",
        event_type="rain",
        location="new york",
        date="2023-10-27",
        confidence=0.9,
        description="Heavy rain expected in New York"
    )

    mock_market = {
        "id": "123",
        "question": "Will it rain in New York on October 27?",
        "description": "This market resolves to Yes if it rains in New York.",
        "clobTokenIds": '["0xabc", "0xdef"]',
        "volume": "1000"
    }

    print(f"Testing match: Event in {mock_event.location} vs Market '{mock_market['question']}'")

    # We need to mock get_vwap_price since it calls real API
    async def mocked_vwap(token_id, side, size):
        return 0.5 # 50 cents

    bot.get_vwap_price = mocked_vwap

    # Directly call execute_trade with the mock market
    # Note: execute_trade expects confidence and event_type which we'd get from the event
    await bot.execute_trade(mock_market, mock_event.confidence, mock_event.event_type)

    print(f"Logs: {bot.logs}")

    found_trade = False
    for log_msg in bot.logs:
        if "EXECUTING BUY YES" in log_msg:
            found_trade = True
            break

    if found_trade:
        print("SUCCESS: Trade executed for matching market.")
    else:
        print("FAILURE: Trade not executed for matching market.")

if __name__ == "__main__":
    asyncio.run(test_matching())
