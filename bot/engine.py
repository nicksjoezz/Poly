import re
import asyncio
import aiohttp
import pytz
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dataclasses import dataclass
from eth_account import Account
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Constants and Mappings
CITY_DB = {
    # ── United States (NOAA) ──────────────────────────────────
    "new york":       (40.7128,  -74.0060,  "US", True,  "America/New_York"),
    "los angeles":    (34.0522, -118.2437,  "US", True,  "America/Los_Angeles"),
    "chicago":        (41.8781,  -87.6298,  "US", True,  "America/Chicago"),
    "houston":        (29.7604,  -95.3698,  "US", True,  "America/Chicago"),
    "miami":          (25.7617,  -80.1918,  "US", True,  "America/New_York"),
    "seattle":        (47.6062, -122.3321,  "US", True,  "America/Los_Angeles"),
    "denver":         (39.7392, -104.9903,  "US", True,  "America/Denver"),
    "atlanta":        (33.7490,  -84.3880,  "US", True,  "America/New_York"),
    "boston":         (42.3601,  -71.0589,  "US", True,  "America/New_York"),
    "dallas":         (32.7767,  -96.7970,  "US", True,  "America/Chicago"),
    "phoenix":        (33.4484, -112.0740,  "US", True,  "America/Phoenix"),
    "san francisco":  (37.7749, -122.4194,  "US", True,  "America/Los_Angeles"),
    "las vegas":      (36.1699, -115.1398,  "US", True,  "America/Los_Angeles"),
    "orlando":        (28.5383,  -81.3792,  "US", True,  "America/New_York"),
    "new orleans":    (29.9511,  -90.0715,  "US", True,  "America/Chicago"),
    "minneapolis":    (44.9778,  -93.2650,  "US", True,  "America/Chicago"),
    "washington":     (38.9072,  -77.0369,  "US", True,  "America/New_York"),
    "tampa":          (27.9506,  -82.4572,  "US", True,  "America/New_York"),
    "nashville":      (36.1627,  -86.7816,  "US", True,  "America/Chicago"),
    "portland":       (45.5051, -122.6750,  "US", True,  "America/Los_Angeles"),
    "gulf coast":     (29.7604,  -95.3698,  "US", True,  "America/Chicago"),

    # ── Europe (Open-Meteo) ───────────────────────────────────
    "london":         (51.5074,   -0.1278,  "UK", False, "Europe/London"),
    "paris":          (48.8566,    2.3522,  "FR", False, "Europe/Paris"),
    "berlin":         (52.5200,   13.4050,  "DE", False, "Europe/Berlin"),
    "madrid":         (40.4168,   -3.7038,  "ES", False, "Europe/Madrid"),
    "rome":           (41.9028,   12.4964,  "IT", False, "Europe/Rome"),
    "amsterdam":      (52.3676,    4.9041,  "NL", False, "Europe/Amsterdam"),
    "zurich":         (47.3769,    8.5417,  "CH", False, "Europe/Zurich"),
    "vienna":         (48.2082,   16.3738,  "AT", False, "Europe/Vienna"),
    "brussels":       (50.8503,    4.3517,  "BE", False, "Europe/Brussels"),
    "stockholm":      (59.3293,   18.0686,  "SE", False, "Europe/Stockholm"),
    "oslo":           (59.9139,   10.7522,  "NO", False, "Europe/Oslo"),
    "copenhagen":     (55.6761,   12.5683,  "DK", False, "Europe/Copenhagen"),
    "lisbon":         (38.7167,   -9.1333,  "PT", False, "Europe/Lisbon"),
    "athens":         (37.9838,   23.7275,  "GR", False, "Europe/Athens"),
    "warsaw":         (52.2297,   21.0122,  "PL", False, "Europe/Warsaw"),
    "istanbul":       (41.0082,   28.9784,  "TR", False, "Europe/Istanbul"),

    # ── Asia Pacific (Open-Meteo) ─────────────────────────────
    "tokyo":          (35.6762,  139.6503,  "JP", False, "Asia/Tokyo"),
    "beijing":        (39.9042,  116.4074,  "CN", False, "Asia/Shanghai"),
    "shanghai":       (31.2304,  121.4737,  "CN", False, "Asia/Shanghai"),
    "hong kong":      (22.3193,  114.1694,  "HK", False, "Asia/Hong_Kong"),
    "singapore":      ( 1.3521,  103.8198,  "SG", False, "Asia/Singapore"),
    "sydney":         (-33.8688, 151.2093,  "AU", False, "Australia/Sydney"),
    "melbourne":      (-37.8136, 144.9631,  "AU", False, "Australia/Melbourne"),
    "seoul":          (37.5665,  126.9780,  "KR", False, "Asia/Seoul"),
    "mumbai":         (19.0760,   72.8777,  "IN", False, "Asia/Kolkata"),
    "delhi":          (28.6139,   77.2090,  "IN", False, "Asia/Kolkata"),
    "dubai":          (25.2048,   55.2708,  "AE", False, "Asia/Dubai"),
    "bangkok":        (13.7563,  100.5018,  "TH", False, "Asia/Bangkok"),
    "jakarta":        (-6.2088,  106.8456,  "ID", False, "Asia/Jakarta"),
    "kuala lumpur":   ( 3.1390,  101.6869,  "MY", False, "Asia/Kuala_Lumpur"),
    "manila":         (14.5995,  120.9842,  "PH", False, "Asia/Manila"),

    # ── Americas ex-US (Open-Meteo) ───────────────────────────
    "toronto":        (43.6532,  -79.3832,  "CA", False, "America/Toronto"),
    "vancouver":      (49.2827, -123.1207,  "CA", False, "America/Vancouver"),
    "montreal":       (45.5017,  -73.5673,  "CA", False, "America/Toronto"),
    "mexico city":    (19.4326,  -99.1332,  "MX", False, "America/Mexico_City"),
    "sao paulo":      (-23.5505, -46.6333,  "BR", False, "America/Sao_Paulo"),
    "rio de janeiro": (-22.9068, -43.1729,  "BR", False, "America/Sao_Paulo"),
    "buenos aires":   (-34.6037, -58.3816,  "AR", False, "America/Argentina/Buenos_Aires"),
    "bogota":         ( 4.7110,  -74.0721,  "CO", False, "America/Bogota"),
    "lima":           (-12.0464, -77.0428,  "PE", False, "America/Lima"),
    "santiago":       (-33.4489, -70.6693,  "CL", False, "America/Santiago"),
    "caribbean":      (15.0000,  -65.0000,  "CB", False, "America/Puerto_Rico"),
    "atlantic":       (25.0000,  -60.0000,  "AT", False, "UTC"),

    # ── Africa & Middle East (Open-Meteo) ─────────────────────
    "cairo":          (30.0444,   31.2357,  "EG", False, "Africa/Cairo"),
    "lagos":          ( 6.5244,    3.3792,  "NG", False, "Africa/Lagos"),
    "nairobi":        (-1.2921,   36.8219,  "KE", False, "Africa/Nairobi"),
    "johannesburg":   (-26.2041,  28.0473,  "ZA", False, "Africa/Johannesburg"),
    "casablanca":     (33.5731,   -7.5898,  "MA", False, "Africa/Casablanca"),
    "accra":          ( 5.6037,   -0.1870,  "GH", False, "Africa/Accra"),
    "abuja":          ( 9.0579,    7.4951,  "NG", False, "Africa/Lagos"),
    "riyadh":         (24.7136,   46.6753,  "SA", False, "Asia/Riyadh"),
    "wellington":     (-41.2865, 174.7762,  "NZ", False, "Pacific/Auckland"),
    "ankara":         (39.9334,   32.8597,  "TR", False, "Europe/Istanbul"),
    "tel aviv":       (32.0853,   34.7818,  "IL", False, "Asia/Jerusalem"),
    "lucknow":        (26.8467,   80.9462,  "IN", False, "Asia/Kolkata"),
    "munich":         (48.1351,   11.5820,  "DE", False, "Europe/Berlin"),
    "milan":          (45.4642,    9.1899,  "IT", False, "Europe/Rome"),
    "taipei":         (25.0330,  121.5654,  "TW", False, "Asia/Taipei"),
}

CITY_ALIASES = {
    "nyc": "new york",
    "la": "los angeles",
    "sf": "san francisco",
    "dc": "washington",
}

SYNONYMS = {
    "rain": ["rain", "precipitation", "rainfall", "wet"],
    "snow": ["snow", "blizzard", "winter storm", "snowfall"],
    "temperature": ["temperature", "heat", "cold", "celsius", "fahrenheit", "degrees", "warm", "hot", "hottest"],
    "hurricane": ["hurricane", "cyclone", "typhoon", "storm", "named storm"],
    "tornado": ["tornado", "twister"],
    "severe": ["severe", "storm", "wind", "natural disaster"],
}

ALERT_SEVERITY = {
    "Tornado Warning": 0.95, "Tornado Watch": 0.75, "Hurricane Warning": 0.95, "Hurricane Watch": 0.80,
    "Tropical Storm Warning": 0.88, "Tropical Storm Watch": 0.72, "Severe Thunderstorm Warning": 0.85,
    "Winter Storm Warning": 0.88, "Winter Storm Watch": 0.70, "Blizzard Warning": 0.92,
    "Flood Warning": 0.87, "Flood Watch": 0.68, "Flash Flood Warning": 0.90, "Excessive Heat Warning": 0.88,
    "Heat Advisory": 0.78, "Freeze Warning": 0.85, "Dense Fog Advisory": 0.80, "High Wind Warning": 0.82,
    "Fire Weather Watch": 0.75
}

GDACS_TYPE_MAP = {
    "TC": ("hurricane", 0.88), "FL": ("rain", 0.85), "DR": ("temperature", 0.78),
    "WF": ("severe", 0.80), "VO": ("severe", 0.75), "TS": ("hurricane", 0.82)
}

GDACS_COUNTRY_TO_CITY = {
    "united states of america": "houston", "united states": "houston", "usa": "houston",
    "mexico": "mexico city", "canada": "toronto", "cuba": "caribbean", "haiti": "caribbean",
    "dominican republic": "caribbean", "bahamas": "miami", "jamaica": "caribbean",
    "puerto rico": "miami", "belize": "caribbean", "honduras": "caribbean", "guatemala": "mexico city",
    "nicaragua": "caribbean", "brazil": "sao paulo", "argentina": "buenos aires", "colombia": "bogota",
    "peru": "lima", "chile": "santiago", "venezuela": "bogota", "ecuador": "lima", "bolivia": "lima",
    "paraguay": "buenos aires", "uruguay": "buenos aires", "united kingdom": "london", "france": "paris",
    "germany": "berlin", "spain": "madrid", "italy": "rome", "netherlands": "amsterdam", "belgium": "brussels",
    "switzerland": "zurich", "austria": "vienna", "sweden": "stockholm", "norway": "oslo", "denmark": "copenhagen",
    "portugal": "lisbon", "greece": "athens", "poland": "warsaw", "czech republic": "prague", "turkey": "istanbul",
    "japan": "tokyo", "china": "beijing", "hong kong": "hong kong", "south korea": "seoul", "india": "mumbai",
    "pakistan": "delhi", "bangladesh": "delhi", "sri lanka": "mumbai", "myanmar": "bangkok", "thailand": "bangkok",
    "vietnam": "bangkok", "cambodia": "bangkok", "laos": "bangkok", "malaysia": "kuala lumpur", "singapore": "singapore",
    "indonesia": "jakarta", "philippines": "manila", "taiwan": "hong kong", "united arab emirates": "dubai",
    "saudi arabia": "riyadh", "israel": "tel aviv", "iraq": "riyadh", "iran": "riyadh", "jordan": "tel aviv",
    "kuwait": "riyadh", "oman": "dubai", "qatar": "dubai", "nigeria": "lagos", "ghana": "accra", "kenya": "nairobi",
    "ethiopia": "nairobi", "tanzania": "nairobi", "uganda": "nairobi", "south africa": "johannesburg",
    "egypt": "cairo", "morocco": "casablanca", "sudan": "cairo", "mozambique": "johannesburg",
    "madagascar": "johannesburg", "somalia": "nairobi", "zimbabwe": "johannesburg", "australia": "sydney",
    "new zealand": "sydney", "fiji": "sydney", "papua new guinea": "sydney"
}

METEOALARM_FEEDS = {
    "london": "united-kingdom", "paris": "france", "berlin": "germany", "madrid": "spain", "rome": "italy",
    "amsterdam": "netherlands", "brussels": "belgium", "zurich": "switzerland", "vienna": "austria",
    "stockholm": "sweden", "oslo": "norway", "copenhagen": "denmark", "lisbon": "portugal",
    "athens": "greece", "warsaw": "poland", "istanbul": "turkey"
}

METEOALARM_MAP = {
    "rain": ("rain", 0.80), "thunderstorm": ("rain", 0.82), "flooding": ("rain", 0.85), "flood": ("rain", 0.85),
    "snow": ("snow", 0.83), "ice": ("snow", 0.80), "blizzard": ("snow", 0.87), "wind": ("severe", 0.78),
    "storm": ("severe", 0.80), "heat": ("temperature", 0.82), "cold": ("temperature", 0.80),
    "fog": ("severe", 0.75), "avalanche": ("severe", 0.80), "coastal": ("hurricane", 0.78)
}

NOAA_HEADERS = {"User-Agent": "WeatherArbBot/V2"}

@dataclass
class WeatherEvent:
    source: str
    event_type: str
    location: str
    date: str
    confidence: float
    description: str

class WeatherBot:
    def __init__(self, config):
        self.config = config
        self.is_running = False
        self.is_trading = False
        self.traded_tokens = set()
        self.active_snipes = set()
        self.nasa_anomaly = None
        self.scanned_markets = []
        self.news_events = []
        self.open_positions = []
        self.metrics = {
            "total_trades": 0,
            "win_rate": 0.0,
            "total_profit": 0.0,
            "balance": config.get("paper_balance", 1000.0) if config.get("paper_mode", True) else 0.0
        }
        self.logs = []
        self.clob_client = None
        self._loop_task = None

    def add_log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(log_entry)
        if len(self.logs) > 100:
            self.logs.pop(0)
        log.info(message)

    def get_local_date(self, city: str, offset_days: int = 0) -> str:
        tz_str = CITY_DB.get(city, (0,0,"",False,"UTC"))[4]
        return (datetime.now(pytz.timezone(tz_str)) + timedelta(days=offset_days)).strftime("%Y-%m-%d")

    async def fetch_noaa_alerts(self, session: aiohttp.ClientSession) -> list[WeatherEvent]:
        events = []
        try:
            async with session.get("https://api.weather.gov/alerts/active", params={"status": "actual", "message_type": "alert"}, headers=NOAA_HEADERS) as resp:
                data = await resp.json()
                for f in data.get("features", []):
                    props = f.get("properties", {})
                    alert_event = props.get("event", "")
                    area_desc = props.get("areaDesc", "").lower()

                    matched_city = next((c for c in CITY_DB if c in area_desc), None)
                    if not matched_city: continue

                    etype = "severe"
                    if any(w in alert_event.lower() for w in ["rain", "flood"]): etype = "rain"
                    elif any(w in alert_event.lower() for w in ["hurricane", "tropical"]): etype = "hurricane"
                    elif any(w in alert_event.lower() for w in ["snow", "blizzard", "winter"]): etype = "snow"
                    elif any(w in alert_event.lower() for w in ["heat", "freeze"]): etype = "temperature"
                    elif "tornado" in alert_event.lower(): etype = "tornado"

                    conf = next((c for k, c in ALERT_SEVERITY.items() if k.lower() in alert_event.lower()), None)
                    if conf:
                        events.append(WeatherEvent("NOAA", etype, matched_city, self.get_local_date(matched_city), conf, alert_event))
        except Exception as e: self.add_log(f"[NOAA] Error: {e}", "WARNING")
        return events

    async def fetch_gdacs(self, session: aiohttp.ClientSession) -> list[WeatherEvent]:
        events = []
        try:
            url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=TC,FL,DR,WF&alertlevel=Green,Orange,Red&limit=100"
            async with session.get(url) as resp:
                data = await resp.json()
                for f in data.get("features", []):
                    props = f.get("properties", {})
                    code = props.get("eventtype", "")
                    country = props.get("country", "").lower().strip()
                    level = props.get("alertlevel", "").lower()

                    if code not in GDACS_TYPE_MAP: continue
                    etype, base_conf = GDACS_TYPE_MAP[code]

                    conf = min(base_conf + {"red": 0.07, "orange": 0.03, "green": 0.0}.get(level, 0.0), 0.97)

                    matched_city = GDACS_COUNTRY_TO_CITY.get(country)
                    if not matched_city:
                        matched_city = next((c for c in CITY_DB if c in props.get("name", "").lower()), None)
                    if not matched_city:
                        matched_city = next((v for k, v in GDACS_COUNTRY_TO_CITY.items() if k in country or country in k), None)

                    if matched_city:
                        events.append(WeatherEvent("GDACS", etype, matched_city, self.get_local_date(matched_city), conf, f"GDACS {level.upper()}: {props.get('name')}"))
        except Exception as e: self.add_log(f"[GDACS] Error: {e}", "WARNING")
        return events

    async def fetch_meteoalarm(self, session: aiohttp.ClientSession) -> list[WeatherEvent]:
        events = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        async def fetch_feed(city, suffix):
            url = f"https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-{suffix}"
            try:
                async with session.get(url) as resp:
                    xml_data = await resp.read()
                    root = ET.fromstring(xml_data)
                    for entry in root.findall("atom:entry", ns)[:10]:
                        title_el = entry.find("atom:title", ns)
                        summary_el = entry.find("atom:summary", ns)
                        text = f"{(title_el.text if title_el is not None else '')} {(summary_el.text if summary_el is not None else '')}".lower()

                        etype, conf = None, None
                        for kw, (t, c) in METEOALARM_MAP.items():
                            if kw in text: etype, conf = t, c; break

                        if etype:
                            if "orange" in text: conf = min(conf + 0.05, 0.95)
                            elif "red" in text: conf = min(conf + 0.10, 0.97)
                            events.append(WeatherEvent("METEOALARM", etype, city, self.get_local_date(city), conf, text[:80]))
            except Exception: pass

        tasks = [fetch_feed(city, suffix) for city, suffix in METEOALARM_FEEDS.items()]
        await asyncio.gather(*tasks)
        return events

    async def fetch_reliefweb(self, session: aiohttp.ClientSession) -> list[WeatherEvent]:
        events = []
        try:
            # Added appname and fields parameters to ensure data richness and API compliance
            url = "https://api.reliefweb.int/v1/disasters?appname=weather-arb-bot&limit=50&preset=latest"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                for item in data.get("data", []):
                    fields = item.get("fields", {})
                    text = (fields.get("name", "") + " " + " ".join([t.get("name", "") for t in fields.get("type", [])])).lower()
                    countries = [c.get("name", "").lower() for c in fields.get("country", [])]

                    etype, conf = None, None
                    disaster_map = {"flood":("rain",0.85), "cyclone":("hurricane",0.88), "typhoon":("hurricane",0.88), "hurricane":("hurricane",0.88), "tropical":("hurricane",0.80), "landslide":("rain",0.78), "drought":("temperature",0.80), "heatwave":("temperature",0.85), "heat wave":("temperature",0.85), "snowstorm":("snow",0.85), "blizzard":("snow",0.87), "storm":("severe",0.75)}

                    for kw, (t, c) in disaster_map.items():
                        if kw in text: etype, conf = t, c; break

                    if not etype: continue

                    matched_city = None
                    for country in countries:
                        matched_city = next((v for k, v in GDACS_COUNTRY_TO_CITY.items() if k in country), None)
                        if matched_city: break

                    if not matched_city:
                        matched_city = next((c for c in CITY_DB if c in text), None)

                    if matched_city:
                        events.append(WeatherEvent("RELIEFWEB", etype, matched_city, self.get_local_date(matched_city), conf, fields.get("name", "")))
        except Exception as e: self.add_log(f"[ReliefWeb] Error: {e}", "WARNING")
        return events

    async def get_openmeteo_forecast(self, session: aiohttp.ClientSession, lat: float, lon: float, target_date: str) -> float | None:
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=precipitation_probability&timezone=auto"
            async with session.get(url) as resp:
                data = await resp.json()
                day_probs = [p/100.0 for t, p in zip(data["hourly"]["time"], data["hourly"]["precipitation_probability"]) if target_date in t and p is not None]
                return max(day_probs) if day_probs else None
        except Exception: return None

    async def update_nasa_anomaly(self, session: aiohttp.ClientSession):
        try:
            async with session.get("https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv") as resp:
                text = await resp.text()
                for line in reversed(text.strip().split("\n")):
                    if line.startswith("Year") or line.startswith("---"): continue
                    parts = line.split(",")
                    if len(parts) >= 13:
                        for val in reversed(parts[1:13]):
                            val = val.strip()
                            if val not in ("***", ""):
                                self.nasa_anomaly = float(val)
                                self.add_log(f"🌍 NASA Anomaly Updated: {self.nasa_anomaly}°C")
                                return
        except Exception as e: self.add_log(f"[NASA] Update failed: {e}", "WARNING")

    async def fetch_all_weather_markets(self, session: aiohttp.ClientSession) -> list[dict]:
        all_markets = {}
        # Extended keywords based on actual Polymarket weather categories
        keywords = [
            "weather", "rain", "temperature", "hurricane", "snow", "flood",
            "precipitation", "celsius", "fahrenheit", "hottest", "tornado",
            "earthquake", "disaster", "volcano"
        ]

        # Blacklist to avoid common non-weather markets often caught in broad searches
        blacklist = [
            "stanley cup", "nhl", "nba", "fifa", "world cup", "gta", "ceasefire",
            "convicted", "sentenced", "election", "war", "qualify", "crypto",
            "bitcoin", "ethereum", "fed", "interest rate", "stock", "company"
        ]

        async def fetch_kw(kw):
            url = f"https://gamma-api.polymarket.com/markets"
            params = {
                "active": "true",
                "closed": "false",
                "limit": 100,
                "q": kw
            }
            try:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        count = 0
                        for m in data:
                            title = m.get("question", "").lower()
                            desc = m.get("description", "").lower()
                            full_text = title + " " + desc

                            # 1. Check if ANY blacklisted term is in the title
                            if any(b in title for b in blacklist):
                                continue

                            # 2. Specific check for sports teams
                            if "carolina hurricanes" in title or "miami heat" in title:
                                continue

                            # 3. Ensure the keyword exists as a whole word
                            if re.search(rf"\b{kw}\b", full_text):
                                # 4. Secondary check: must contain at least one city from our DB
                                # or be a very specific weather term
                                has_city = any(city in full_text for city in CITY_DB)
                                if has_city or kw in ["rain", "snow", "hurricane", "flood", "precipitation", "celsius", "fahrenheit"]:
                                    all_markets[m["id"]] = m
                                    count += 1
                        log.info(f"Polymarket search for '{kw}' returned {len(data)} results, {count} matched strictly.")
            except Exception as e:
                log.error(f"Error searching Polymarket for '{kw}': {e}")

        await asyncio.gather(*(fetch_kw(kw) for kw in keywords))
        return list(all_markets.values())

    def parse_temp_threshold(self, title: str) -> dict | None:
        """Parses value and unit from title, e.g., '80°F' or '30°C'."""
        # Match Fahrenheit
        f_match = re.search(r"(\d+(?:\.\d+)?)\s*°?F", title, re.IGNORECASE)
        if f_match:
            return {"value": float(f_match.group(1)), "unit": "F"}

        # Match Celsius
        c_match = re.search(r"(\d+(?:\.\d+)?)\s*°?C", title, re.IGNORECASE)
        if c_match:
            return {"value": float(c_match.group(1)), "unit": "C"}

        # Match plain number if 'degrees' is mentioned
        if "degrees" in title.lower():
            n_match = re.search(r"(\d+(?:\.\d+)?)", title)
            if n_match:
                # Default to F if it's high (likely US market), else C
                val = float(n_match.group(1))
                unit = "F" if val > 45 else "C"
                return {"value": val, "unit": unit}

        return None

    async def get_vwap_price(self, token_id: str, side: str, size: float) -> float | None:
        try:
            book = await asyncio.to_thread(self.clob_client.get_order_book, token_id)
            levels = book.asks if side == "BUY" else book.bids
            acc_size, total_cost = 0.0, 0.0

            for level in levels:
                price, vol = float(level.price), float(level.size)
                take = min(vol, size - acc_size)
                total_cost += take * price
                acc_size += take
                if acc_size >= size: return total_cost / size
            return None
        except Exception: return None

    async def execute_trade(self, market: dict, confidence: float, event_type: str):
        if not self.is_trading: return
        tokens = market.get("clobTokenIds", [])
        if isinstance(tokens, str):
            import json
            try:
                tokens = json.loads(tokens)
            except:
                return
        if not tokens: return
        yes_token = tokens[0]

        if yes_token in self.traded_tokens: return
        # In live mode we care about volume, but in paper mode or tests we may allow lower volume
        if not self.config.get("paper_mode", True) and float(market.get("volume", 0)) < 500: return

        if event_type == "temperature" and self.nasa_anomaly is not None:
            thresh_info = self.parse_temp_threshold(market.get("question", ""))
            if thresh_info:
                # Convert threshold to Celsius for comparison with NASA anomaly
                thresh_c = thresh_info["value"]
                if thresh_info["unit"] == "F":
                    thresh_c = (thresh_info["value"] - 32) * 5/9

                # NASA anomaly is global, but we use it as a trend signal.
                # If current global anomaly is high, we lean towards "Yes" for record heat.
                if self.nasa_anomaly > 0.5:
                    confidence = max(confidence, 0.85)
                elif self.nasa_anomaly < -0.5:
                    confidence = min(confidence, 0.15)

        vwap = await self.get_vwap_price(yes_token, "BUY", self.config["trade_amount"])
        if not vwap: return

        taker_fee = 0.015
        true_edge = confidence - vwap - taker_fee
        self.add_log(f"[{market['question'][:50]}...] Conf: {confidence:.2f} | VWAP: {vwap:.2f} | Edge: {true_edge:+.2f}")

        if true_edge >= self.config["min_edge"]:
            self.add_log(f"🚨 EXECUTING BUY YES for ${self.config['trade_amount']}")
            if not self.config["paper_mode"]:
                try:
                    mo = MarketOrderArgs(token_id=yes_token, amount=self.config["trade_amount"], side=BUY, order_type=OrderType.FOK)
                    signed = await asyncio.to_thread(self.clob_client.create_market_order, mo)
                    resp = await asyncio.to_thread(self.clob_client.post_order, signed, OrderType.FOK)
                    self.add_log(f"✅ Trade confirmed: {resp}")
                    self.traded_tokens.add(yes_token)
                    self.open_positions.append({"question": market["question"], "amount": self.config["trade_amount"], "price": vwap, "token_id": yes_token})
                except Exception as e: self.add_log(f"❌ Trade failed: {e}", "ERROR")
            else:
                self.add_log("✅ [PAPER MODE] Trade Simulated.")
                self.traded_tokens.add(yes_token)
                self.metrics["total_trades"] += 1
                self.metrics["balance"] -= self.config["trade_amount"]
                self.open_positions.append({"question": market["question"], "amount": self.config["trade_amount"], "price": vwap, "token_id": yes_token})

    async def sniper_task(self, event: WeatherEvent, combined_conf: float, snipe_key: str):
        if not self.is_trading: return
        self.add_log(f"🎯 [SNIPER LAUNCHED] Watching Polymarket for new '{event.location}' market...")
        try:
            async with aiohttp.ClientSession() as session:
                for attempt in range(1, 11):
                    if not self.is_running or not self.is_trading: break
                    url = f"https://gamma-api.polymarket.com/markets?q={event.location}&active=true&closed=false"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            matched = [m for m in data if event.event_type.lower() in (m.get("question", "") + m.get("description", "")).lower()]
                            if matched:
                                self.add_log(f"🚨 [SNIPER HIT] Market deployed on attempt {attempt} for {event.location}!")
                                for m in matched:
                                    await self.execute_trade(m, combined_conf, event.event_type)
                                return
                    await asyncio.sleep(30)
            self.add_log(f"🛑 [SNIPER EXPIRED] No market created for {event.location}.")
        except Exception as e: self.add_log(f"[SNIPER ERROR] {e}", "ERROR")
        finally:
            self.active_snipes.discard(snipe_key)

    async def run_pipeline(self):
        self.add_log("=== Pipeline Scan Started ===")
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if self.nasa_anomaly is None: await self.update_nasa_anomaly(session)

            self.add_log("Fetching alerts from NOAA, GDACS, MeteoAlarm, and ReliefWeb...")
            alert_tasks = [
                self.fetch_noaa_alerts(session),
                self.fetch_gdacs(session),
                self.fetch_meteoalarm(session),
                self.fetch_reliefweb(session)
            ]
            alert_results = await asyncio.gather(*alert_tasks, return_exceptions=True)

            all_events = []
            for i, r in enumerate(alert_results):
                source = ["NOAA", "GDACS", "MeteoAlarm", "ReliefWeb"][i]
                if isinstance(r, Exception):
                    self.add_log(f"Error fetching from {source}: {r}", "ERROR")
                elif isinstance(r, list):
                    all_events.extend(r)
                    self.add_log(f"Fetched {len(r)} alerts from {source}")

            self.news_events = [{"source": e.source, "location": e.location, "type": e.event_type, "conf": e.confidence, "desc": e.description} for e in all_events]

            self.add_log("Fetching markets from Polymarket Gamma API...")
            try:
                cached_markets = await self.fetch_all_weather_markets(session)
                self.scanned_markets = [{"question": m["question"], "volume": float(m.get("volume", 0))} for m in cached_markets]
                self.add_log(f"Fetched {len(cached_markets)} markets from Polymarket")
            except Exception as e:
                self.add_log(f"Error fetching Polymarket markets: {e}", "ERROR")
                cached_markets = []

            self.add_log(f"Summary: {len(all_events)} active global alerts. {len(cached_markets)} weather markets.")

            deduped = {}
            for ev in all_events:
                k = f"{ev.location}_{ev.date}_{ev.event_type}"
                if k not in deduped or ev.confidence > deduped[k].confidence:
                    deduped[k] = ev

            for city, data in CITY_DB.items():
                if not data[3]:
                    target_date = self.get_local_date(city)
                    k = f"{city}_{target_date}_rain"
                    if k not in deduped:
                        prob = await self.get_openmeteo_forecast(session, data[0], data[1], target_date)
                        if prob and (prob > 0.60 or prob < 0.25):
                            deduped[k] = WeatherEvent("FORECAST", "rain", city, target_date, prob, f"Pure forecast: {prob:.0%}")
                            await asyncio.sleep(0.1)

            for key, event in deduped.items():
                if not self.is_running: break
                city_data = CITY_DB.get(event.location)
                if not city_data: continue

                if event.source != "FORECAST":
                    forecast = await self.get_openmeteo_forecast(session, city_data[0], city_data[1], event.date)
                    combined_conf = (event.confidence * 0.6) + (forecast * 0.4) if forecast else event.confidence
                else:
                    combined_conf = event.confidence

                # Refined matching: location (or alias) + event_type (or synonym) must both be present
                matched_markets = []
                loc_variants = [event.location.lower()]
                for alias, real_name in CITY_ALIASES.items():
                    if real_name == event.location.lower():
                        loc_variants.append(alias)

                type_synonyms = SYNONYMS.get(event.event_type, [event.event_type])

                for m in cached_markets:
                    text = (m.get("question","") + " " + m.get("description","")).lower()

                    has_loc = any(re.search(rf"\b{v}\b", text) for v in loc_variants)
                    has_type = any(re.search(rf"\b{s}\b", text) for s in type_synonyms)

                    if has_loc and has_type:
                        matched_markets.append(m)

                if matched_markets:
                    for market in matched_markets:
                        await self.execute_trade(market, combined_conf, event.event_type)

                elif not matched_markets and combined_conf >= 0.80 and event.source != "FORECAST":
                    snipe_key = f"{event.location}_{event.event_type}_{event.date}"
                    if snipe_key not in self.active_snipes:
                        self.active_snipes.add(snipe_key)
                        asyncio.create_task(self.sniper_task(event, combined_conf, snipe_key))

    async def _loop(self):
        while self.is_running:
            try:
                await self.run_pipeline()
            except Exception as e:
                self.add_log(f"Pipeline error: {e}", "ERROR")

            for _ in range(self.config["scan_interval"] * 60):
                if not self.is_running: break
                await asyncio.sleep(1)

    def initialize(self):
        """Starts the background scanning loop."""
        if self.is_running: return
        self.is_running = True
        self.add_log("Background Scanner initialized.")
        log.info("Background Scanner initialized.")

        # Initialize CLOB Client for price fetching
        self.clob_client = ClobClient("https://clob.polymarket.com", key="0"*64, chain_id=137)

        import threading
        def run_in_thread():
            log.info("Bot thread started.")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop_task = loop.create_task(self._loop())
            try:
                loop.run_until_complete(self._loop_task)
            except Exception as e:
                log.error(f"Bot thread loop failed: {e}")

        self._thread = threading.Thread(target=run_in_thread, daemon=True)
        self._thread.start()

    def start_trading(self):
        if not self.is_running: self.initialize()
        self.is_trading = True
        self.add_log("Trading activity started.")
        if not self.config["paper_mode"]:
            try:
                self.clob_client = ClobClient("https://clob.polymarket.com", key=self.config["private_key"], chain_id=137, signature_type=0, funder=self.config["wallet_address"])
                self.clob_client.set_api_creds(self.clob_client.create_or_derive_api_creds())
            except Exception as e:
                self.add_log(f"Failed to initialize live CLOB client: {e}", "ERROR")
                self.is_trading = False

    def stop_trading(self):
        self.is_trading = False
        self.add_log("Trading activity stopped.")

    def get_status(self):
        return {
            "is_running": self.is_running,
            "is_trading": self.is_trading,
            "metrics": self.metrics,
            "open_positions": self.open_positions,
            "scanned_markets": self.scanned_markets[:20],
            "news_events": self.news_events[:20],
            "logs": self.logs[-20:],
            "config": {k: v for k, v in self.config.items() if "key" not in k} # Don't send keys to UI
        }
