from bot.engine import WeatherBot

def test_parse():
    bot = WeatherBot({})
    cases = [
        ("Will it reach 80°F in Miami?", {"value": 80.0, "unit": "F"}),
        ("Will it reach 30°C in London?", {"value": 30.0, "unit": "C"}),
        ("Will it be above 25 degrees in Paris?", {"value": 25.0, "unit": "C"}),
        ("Will it be above 90 degrees in Phoenix?", {"value": 90.0, "unit": "F"}),
    ]

    for title, expected in cases:
        result = bot.parse_temp_threshold(title)
        print(f"Title: {title} | Expected: {expected} | Result: {result}")

if __name__ == "__main__":
    test_parse()
