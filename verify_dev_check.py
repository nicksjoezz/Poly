import asyncio
import aiohttp
import logging
from bot.engine import WeatherBot

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def main():
    config = {
        "paper_mode": True,
        "paper_balance": 1000.0,
        "trade_amount": 10.0,
        "min_edge": 0.01, # Lower edge to trigger trades easily in test
        "scan_interval": 1,
        "max_trades": 10
    }
    bot = WeatherBot(config)

    print("Initializing bot...")
    bot.initialize()

    print("Starting trading (Paper Mode)...")
    bot.start_trading()

    # Wait for the first scan to complete
    print("Waiting for initial scan and potential trades (up to 40s)...")
    for i in range(40):
        await asyncio.sleep(1)
        status = bot.get_status()
        if len(status['dev_check_logs']) > 0:
            print(f"Success: {len(status['dev_check_logs'])} dev check logs captured.")
            break
        if i % 10 == 0:
            print(f"Still waiting... {i}s elapsed. Scanned: {status['total_scanned']}")

    status = bot.get_status()
    print(f"Bot Status: Running={status['is_running']}, Trading={status['is_trading']}")
    print(f"Markets Scanned: {status['total_scanned']}")
    print(f"Dev Check Logs: {len(status['dev_check_logs'])}")

    if len(status['dev_check_logs']) > 0:
        log_entry = status['dev_check_logs'][0]
        print("\n--- Sample Dev Check Log ---")
        print(f"Market: {log_entry['market']['question']}")
        print(f"Analysis: {log_entry['analysis']}")
        print(f"Triggering News Count: {len(log_entry['triggering_news'])}")
        print("----------------------------\n")
    else:
        print("Observation: No trades triggered, so no dev check logs. This is expected if edge is not met.")

    bot.stop_trading()
    bot.is_running = False
    print("Test complete.")

if __name__ == "__main__":
    asyncio.run(main())
