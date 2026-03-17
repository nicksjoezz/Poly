import unittest
import asyncio
from bot.engine import WeatherBot

class TestWeatherBot(unittest.TestCase):
    def setUp(self):
        self.config = {
            "trade_amount": 10.0,
            "min_edge": 0.2,
            "scan_interval": 1,
            "paper_mode": True,
            "paper_balance": 1000.0,
            "private_key": "0x" + "0" * 64,
            "wallet_address": "0x" + "0" * 40
        }
        self.bot = WeatherBot(self.config)

    def test_initial_state(self):
        status = self.bot.get_status()
        self.assertFalse(status["is_running"])
        self.assertEqual(status["metrics"]["balance"], 1000.0)
        self.assertEqual(len(status["logs"]), 0)

    def test_add_log(self):
        self.bot.add_log("Test message")
        status = self.bot.get_status()
        self.assertEqual(len(status["logs"]), 1)
        self.assertIn("Test message", status["logs"][0])

if __name__ == "__main__":
    unittest.main()
