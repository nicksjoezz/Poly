import re
import json
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
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
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
    "ankara":         (39.9334,   32.8597,  "TR", False, "Europe/Istanbul"),
    "tel aviv":       (32.0853,   34.7818,  "IL", False, "Asia/Jerusalem"),
    "lucknow":        (26.8467,   80.9462,  "IN", False, "Asia/Kolkata"),
    "munich":         (48.1351,   11.5820,  "DE", False, "Europe/Berlin"),
    "milan":          (45.4642,    9.1899,  "IT", False, "Europe/Rome"),
    "taipei":         (25.0330,  121.5654,  "TW", False, "Asia/Taipei"),
    "wellington":     (-41.2865, 174.7762,  "NZ", False, "Pacific/Auckland"),
    "hong kong":      (22.3193,  114.1694,  "HK", False, "Asia/Hong_Kong"),

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
    "us":             (39.8283,  -98.5795,  "US", False, "UTC"),
    "arctic":         (90.0000,    0.0000,  "AR", False, "UTC"),
    "global":         (0.0000,     0.0000,  "GL", False, "UTC"),
    "worldwide":      (0.0000,     0.0000,  "GL", False, "UTC"),
}

CITY_ALIASES = {
    "nyc": "new york",
    "la": "los angeles",
    "sf": "san francisco",
    "dc": "washington",
    "nyc": "new york",
    "new york city": "new york",
}

SYNONYMS = {
    "rain": ["rain", "precipitation", "rainfall", "wet"],
    "snow": ["snow", "blizzard", "winter storm", "snowfall"],
    "temperature": ["temperature", "heat", "cold", "celsius", "fahrenheit", "degrees", "warm", "hot", "hottest"],
    "hurricane": ["hurricane", "cyclone", "typhoon", "storm", "named storm"],
    "tornado": ["tornado", "twister"],
    "severe": ["severe", "storm", "wind", "natural disaster"],
    "earthquake": ["earthquake", "seismic", "quake", "megaquake"],
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
        self.seen_market_ids = set()
        self.active_snipes = set()
        self.nasa_anomaly = None
        self.scanned_markets = []
        self.news_events = []
        self.open_positions = []
        self.resolved_positions = []
        self.dev_check_logs = []
        self.metrics = {
            "total_trades": 0,
            "win_rate": 0.0,
            "total_profit": 0.0,
            "balance": float(config.get("paper_balance", 1000.0)) if config.get("paper_mode", True) else 0.0,
            "max_trades": config.get("max_trades", 10)
        }
        self.logs = []
        self.clob_client = None
        self._loop_task = None
        self._scan_event = asyncio.Event()

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

        # Tag Discovery Logic
        tag_ids = [84, 103040, 496, 832, 104180]

        # Blacklist to avoid common non-weather markets often caught in broad searches
        blacklist = [
            "stanley cup", "nhl", "nba", "fifa", "world cup", "gta", "ceasefire",
            "convicted", "sentenced", "election", "war", "qualify", "crypto",
            "bitcoin", "ethereum", "fed", "interest rate", "stock", "company",
            "ukraine", "russia", "middle east", "ceasefire", "peace", "israel",
            "palestine", "gaza", "china", "taiwan", "election", "president",
            "senate", "house", "gop", "democrat", "biden", "trump", "harris"
        ]

        async def fetch_tag(tid):
            # Using /events endpoint for tag filtering as it returns grouped markets
            url = f"https://gamma-api.polymarket.com/events"
            params = {
                "active": "true",
                "closed": "false",
                "limit": 50,
                "tag_id": tid
            }
            try:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        events = await resp.json()
                        for event in events:
                            for m in event.get("markets", []):
                                title = m.get("question", "").lower()
                                volume = float(m.get("volume", 0))

                                # Volume filter: Discard markets with less than $500 volume
                                if volume < 500: continue

                                # Simple filter for tags as they are already weather-focused
                                if not any(b in title for b in blacklist):
                                    if m["id"] not in all_markets:
                                        self.add_log(f"Market Discovery (Tag {tid}): {m.get('question')[:60]}...")
                                    all_markets[m["id"]] = m
            except Exception as e:
                log.error(f"Error fetching Polymarket Tag {tid}: {e}")

        # Fallback keywords
        keywords = ["weather", "temperature", "hurricane", "tornado", "precipitation", "hottest", "celsius", "fahrenheit", "flood"]

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
                        for m in data:
                            title = m.get("question", "").lower()
                            desc = m.get("description", "").lower()
                            full_text = title + " " + desc
                            volume = float(m.get("volume", 0))

                            # Volume filter: Discard markets with less than $500 volume
                            if volume < 500: continue

                            if any(b in title for b in blacklist): continue
                            if any(b in desc for b in ["ceasefire", "ukraine", "russia", "qualify", "world cup"]): continue
                            if "carolina hurricanes" in title or "miami heat" in title: continue

                            if re.search(rf"\b{kw}\b", full_text):
                                has_city = any(city in full_text for city in CITY_DB)
                                # Broad keywords or city match
                                if has_city or kw in ["rain", "snow", "hurricane", "flood", "precipitation", "celsius", "fahrenheit"]:
                                    if m["id"] not in all_markets:
                                        self.add_log(f"Market Discovery (KW {kw}): {m.get('question')[:60]}...")
                                    all_markets[m["id"]] = m
            except Exception as e:
                log.error(f"Error searching Polymarket for '{kw}': {e}")

        tasks = [fetch_tag(tid) for tid in tag_ids] + [fetch_kw(kw) for kw in keywords]
        await asyncio.gather(*tasks)
        return list(all_markets.values())

    def parse_numeric_threshold(self, title: str) -> dict | None:
        """Parses value, comparison type, and unit from title for temp or precip."""
        title_lower = title.lower()

        # 1. Identify Unit
        unit = "C" # Default
        if any(x in title_lower for x in ["°f", "fahrenheit"]): unit = "F"
        elif "inch" in title_lower: unit = "inch"
        elif "mm" in title_lower or "millimeter" in title_lower: unit = "mm"

        # 2. Match Ranges
        # "between 60 and 70", "80-81", "5 to 6 inches"
        range_match = re.search(r"between\s+(\d+(?:\.\d+)?)\s*(?:and|to|&)\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)\s+(?:inch|mm|degrees|°)", title_lower)
        if range_match:
            v1, v2 = None, None
            if range_match.group(1): v1, v2 = float(range_match.group(1)), float(range_match.group(2))
            elif range_match.group(3): v1, v2 = float(range_match.group(3)), float(range_match.group(4))
            elif range_match.group(5): v1, v2 = float(range_match.group(5)), float(range_match.group(6))
            if v1 is not None:
                return {"type": "range", "min": min(v1, v2), "max": max(v1, v2), "unit": unit}

        # 3. Match "At Least" / "Or Higher" / "Or More"
        at_least_patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:°?[fc]|inch|mm|inches|millimeters)?\s*or\s*(?:more|higher|above)",
            r"(?:at\s+least|above|more\s+than|greater\s+than)\s*(\d+(?:\.\d+)?)",
        ]
        for p in at_least_patterns:
            m = re.search(p, title_lower)
            if m:
                return {"type": "at_least", "value": float(m.group(1)), "unit": unit}

        # 4. Match "Less Than" / "Or Below" / "Or Fewer"
        less_than_patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:°?[fc]|inch|mm|inches|millimeters)?\s*or\s*(?:below|lower|fewer|less)",
            r"(?:less\s+than|fewer\s+than|below|under)\s*(\d+(?:\.\d+)?)",
        ]
        for p in less_than_patterns:
            m = re.search(p, title_lower)
            if m:
                return {"type": "less_than", "value": float(m.group(1)), "unit": unit}

        # 5. Match Exact Values
        exact_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:°[fc]|°|degrees|inch|mm|inches|millimeters|c|f)\b", title_lower)
        if exact_match:
            return {"type": "exact", "value": float(exact_match.group(1)), "unit": unit}

        # Last ditch: any number near a unit
        if unit != "C" or "degrees" in title_lower:
            m = re.search(r"(\d+(?:\.\d+)?)", title_lower)
            if m: return {"type": "exact", "value": float(m.group(1)), "unit": unit}

        return None

    def parse_market_date(self, text: str) -> str | None:
        """Extracts date from market text. Returns YYYY-MM-DD, YYYY-MM, or YYYY."""
        # Try full date: March 19, 2026
        full_date = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})", text, re.IGNORECASE)
        if full_date:
            month_map = {"january":"01","february":"02","march":"03","april":"04","may":"05","june":"06","july":"07","august":"08","september":"09","october":"10","november":"11","december":"12"}
            m = month_map[full_date.group(1).lower()]
            d = full_date.group(2).zfill(2)
            y = full_date.group(3)
            return f"{y}-{m}-{d}"

        # Try day of year without year: March 19
        day_month = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})\b", text, re.IGNORECASE)
        if day_month:
            month_map = {"january":"01","february":"02","march":"03","april":"04","may":"05","june":"06","july":"07","august":"08","september":"09","october":"10","november":"11","december":"12"}
            m = month_map[day_month.group(1).lower()]
            d = day_month.group(2).zfill(2)
            return f"2026-{m}-{d}" # Default to 2026 as per markets

        # Try month only: in March
        month_only = re.search(r"in (january|february|march|april|may|june|july|august|september|october|november|december)\b", text, re.IGNORECASE)
        if month_only:
            month_map = {"january":"01","february":"02","march":"03","april":"04","may":"05","june":"06","july":"07","august":"08","september":"09","october":"10","november":"11","december":"12"}
            m = month_map[month_only.group(1).lower()]
            return f"2026-{m}"

        # Try year only: in 2026
        year_match = re.search(r"\b(202[4-9])\b", text)
        if year_match:
            return year_match.group(1)

        return None

    def parse_market_location(self, text: str) -> str | None:
        """Identifies location from market text."""
        text = text.lower()
        # Check aliases first for better precision (e.g. NYC)
        for alias, real in CITY_ALIASES.items():
            if re.search(rf"\b{alias}\b", text):
                return real
        for city in CITY_DB:
            if re.search(rf"\b{city}\b", text):
                return city

        # Default for global/scientific markets
        if any(kw in text for kw in ["worldwide", "global", "earthquakes", "on record", "sea ice"]):
            return "global"

        return None

    async def get_vwap_price(self, token_id: str, side: str, size: float) -> float | None:
        try:
            if not self.clob_client: return None
            # Fetch orderbook from CLOB
            book = await asyncio.to_thread(self.clob_client.get_order_book, token_id)
            levels = book.asks if side == "BUY" else book.bids
            if not levels: return None

            acc_size, total_cost = 0.0, 0.0
            for level in levels:
                price, vol = float(level.price), float(level.size)
                take = min(vol, size - acc_size)
                total_cost += take * price
                acc_size += take
                if acc_size >= size: return total_cost / size

            # If we didn't fill the whole size, return None or partial VWAP
            if acc_size > 0: return total_cost / acc_size
            return None
        except Exception as e:
            log.debug(f"Error fetching VWAP for {token_id}: {e}")
            return None

    async def execute_trade(self, market: dict, confidence: float, event_type: str, analysis: str = "", triggering_news: list = None):
        if not self.is_trading:
            self.add_log(f"Opportunity found for {market.get('id')} but trading is DISABLED. Enable 'Start Trading' to execute.", "DEBUG")
            return

        # Check Max Trades Limit
        if len(self.open_positions) >= self.config.get("max_trades", 10):
            self.add_log(f"Max trades reached ({len(self.open_positions)}), skipping market {market.get('id')}.", "DEBUG")
            return

        tokens = market.get("clobTokenIds", [])
        if isinstance(tokens, str):
            try:
                tokens = json.loads(tokens)
            except:
                self.add_log(f"Failed to parse tokens for market {market.get('id')}", "DEBUG")
                return
        if not tokens or len(tokens) < 2:
            self.add_log(f"Insufficient tokens for market {market.get('id')}", "DEBUG")
            return

        yes_token = tokens[0]
        no_token = tokens[1]

        if yes_token in self.traded_tokens or no_token in self.traded_tokens:
            self.add_log(f"Market {market.get('id')} already traded, skipping.", "DEBUG")
            return

        # Volume filter
        volume = float(market.get("volume", 0))
        if volume < 500:
            self.add_log(f"Low volume ({volume}) for market {market.get('id')}, skipping.", "DEBUG")
            return

        # Directional Filter: Prevent betting on unlikely outcomes just because they're "cheap"
        # If confidence is neutral (0.5), we skip.
        if confidence == 0.5:
            return

        # Calculate Edge for the target side ONLY
        taker_fee = 0.015
        target_side = "YES" if confidence > 0.5 else "NO"
        target_token = yes_token if target_side == "YES" else no_token
        target_conf = confidence if target_side == "YES" else 1.0 - confidence

        # Fetch Price
        vwap = await self.get_vwap_price(target_token, "BUY", self.config["trade_amount"])
        if vwap is None or vwap <= 0:
            amm_prices = market.get("outcomePrices")
            if isinstance(amm_prices, str):
                try: amm_prices = json.loads(amm_prices)
                except: amm_prices = None
            if amm_prices and len(amm_prices) >= 2:
                vwap = float(amm_prices[0 if target_side == "YES" else 1])

        if vwap is None or vwap <= 0:
            self.add_log(f"No valid price (>0) found for {target_side} token in {market.get('id')}. Price: {vwap}", "DEBUG")
            return

        edge = target_conf - vwap - taker_fee
        best_vwap = vwap
        best_edge = edge

        if edge < self.config["min_edge"]:
            self.add_log(f"Low edge for {target_side} in {market.get('id')}: {edge:.2f} (Need {self.config['min_edge']:.2f})", "DEBUG")
            return

        if target_side:
            self.add_log(f"Opportunity Found: {target_side} for '{market['question'][:50]}...'")
            self.add_log(f"Stats: Conf={confidence if target_side=='YES' else 1-confidence:.2f}, VWAP={best_vwap:.2f}, Edge={best_edge:+.2f}")
            self.add_log(f"🚨 EXECUTING BUY {target_side} for ${self.config['trade_amount']}")

            trade_info = {
                "market_id": market.get("id"),
                "question": market["question"],
                "side": target_side,
                "amount": self.config["trade_amount"],
                "price": best_vwap,
                "token_id": target_token,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Add to Dev Check Logs
            self.dev_check_logs.append({
                "market": market,
                "confidence": confidence,
                "target_side": target_side,
                "vwap": best_vwap,
                "edge": best_edge,
                "analysis": analysis,
                "triggering_news": triggering_news or [],
                "timestamp": trade_info["timestamp"]
            })
            if len(self.dev_check_logs) > 50: self.dev_check_logs.pop(0)

            if not self.config["paper_mode"]:
                try:
                    from py_clob_client.order_builder.constants import BUY
                    mo = MarketOrderArgs(token_id=target_token, amount=self.config["trade_amount"], side=BUY, order_type=OrderType.FOK)
                    signed = await asyncio.to_thread(self.clob_client.create_market_order, mo)
                    resp = await asyncio.to_thread(self.clob_client.post_order, signed, OrderType.FOK)
                    self.add_log(f"✅ Trade confirmed: {resp}")
                    self.traded_tokens.add(target_token)
                    self.open_positions.append(trade_info)
                except Exception as e: self.add_log(f"❌ Trade failed: {e}", "ERROR")
            else:
                self.add_log(f"✅ [PAPER MODE] {target_side} Trade Simulated.")
                self.traded_tokens.add(target_token)
                self.metrics["balance"] -= self.config["trade_amount"]
                self.open_positions.append(trade_info)

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
                            type_synonyms = SYNONYMS.get(event.event_type, [event.event_type])
                            matched = []
                            for m in data:
                                text = (m.get("question", "") + " " + m.get("description", "")).lower()
                                volume = float(m.get("volume", 0))

                                # Volume filter: Discard markets with less than $500 volume
                                if volume < 500: continue

                                if any(re.search(rf"\b{s}\b", text) for s in type_synonyms):
                                    matched.append(m)

                            if matched:
                                self.add_log(f"🚨 [SNIPER HIT] Market deployed on attempt {attempt} for {event.location}!")
                                for m in matched:
                                    self.add_log(f"Sniper Matched: {m.get('question')}")
                                    await self.execute_trade(m, combined_conf, event.event_type,
                                                           analysis=f"Sniper triggered for {event.location} based on {event.source} alert.",
                                                           triggering_news=[event.__dict__])
                                return
                    await asyncio.sleep(30)
            self.add_log(f"🛑 [SNIPER EXPIRED] No market created for {event.location}.")
        except Exception as e: self.add_log(f"[SNIPER ERROR] {e}", "ERROR")
        finally:
            self.active_snipes.discard(snipe_key)

    async def get_forecast_max_temp(self, session: aiohttp.ClientSession, lat: float, lon: float, date_str: str) -> float | None:
        """Gets max temperature for a specific date from Open-Meteo."""
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
            async with session.get(url) as resp:
                data = await resp.json()
                if "daily" in data and date_str in data["daily"]["time"]:
                    idx = data["daily"]["time"].index(date_str)
                    return data["daily"]["temperature_2m_max"][idx]
            return None
        except Exception: return None

    async def get_forecast_precipitation(self, session: aiohttp.ClientSession, lat: float, lon: float, date_str: str) -> float | None:
        """Gets total precipitation for a specific date from Open-Meteo."""
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=auto"
            async with session.get(url) as resp:
                data = await resp.json()
                if "daily" in data and date_str in data["daily"]["time"]:
                    idx = data["daily"]["time"].index(date_str)
                    return data["daily"]["precipitation_sum"][idx]
            return None
        except Exception: return None

    async def fetch_earthquake_count(self, session: aiohttp.ClientSession, min_mag: float, start_date: str, end_date: str) -> int:
        """Fetches count of earthquakes of a certain magnitude from USGS."""
        try:
            url = f"https://earthquake.usgs.gov/fdsnws/event/1/count?format=geojson&starttime={start_date}&endtime={end_date}&minmagnitude={min_mag}"
            async with session.get(url) as resp:
                data = await resp.json()
                return data.get("count", 0)
        except Exception: return 0

    async def run_pipeline(self):
        self.add_log("=== Pipeline Scan Started ===")
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if self.nasa_anomaly is None: await self.update_nasa_anomaly(session)

            # 1. Fetch Alpha Alerts
            self.add_log("Fetching alerts from NOAA, GDACS, MeteoAlarm, and ReliefWeb...")
            alert_tasks = [
                self.fetch_noaa_alerts(session),
                self.fetch_gdacs(session),
                self.fetch_meteoalarm(session),
                self.fetch_reliefweb(session)
            ]
            alert_results = await asyncio.gather(*alert_tasks, return_exceptions=True)

            all_alerts = []
            for i, r in enumerate(alert_results):
                source = ["NOAA", "GDACS", "MeteoAlarm", "ReliefWeb"][i]
                if isinstance(r, list): all_alerts.extend(r)

            self.news_events = [{"source": e.source, "location": e.location, "type": e.event_type, "conf": e.confidence, "desc": e.description} for e in all_alerts]

            # 2. Discover ALL Weather Markets via Tags & Keywords
            self.add_log("Discovering Polymarket weather contracts...")
            discovered = await self.fetch_all_weather_markets(session)

            # Identify which markets are "new" since the bot started
            for m in discovered:
                mid = m.get("id")
                if mid and mid not in self.seen_market_ids:
                    m["is_new"] = True
                    # self.add_log(f"✨ New Market Detected: {m.get('question')[:60]}...")
                    self.seen_market_ids.add(mid)
                else:
                    m["is_new"] = False

            if discovered:
                self.scanned_markets = [{"id": m["id"], "question": m["question"], "volume": float(m.get("volume", 0)), "is_new": m.get("is_new")} for m in discovered]
            self.add_log(f"Scan complete: {len(discovered)} markets found.")

            cached_markets = discovered
            self.add_log(f"Discovered {len(cached_markets)} weather markets.")

            # 3. Process Each Market: Analyze supporting news/data and compare
            # Cache for forecasts within this scan to save API limits and speed up grouped processing
            local_forecast_cache = {}

            for m in cached_markets:
                analysis_steps = []
                triggering_news_objs = []
                title = m.get("question", "")
                full_text = (title + " " + m.get("description", "")).lower()

                location = self.parse_market_location(full_text)
                date_str = self.parse_market_date(title)

                if not location or not date_str:
                    log.debug(f"Missing metadata for {m.get('id')} - Loc: {location}, Date: {date_str}")
                    continue

                # Date Filter: Don't trade on past events
                current_date = self.get_local_date(location)
                if len(date_str) == 10 and date_str < current_date:
                    log.debug(f"Skipping past market: {m.get('id')} ({date_str} < {current_date})")
                    continue

                # Determine event type
                etype = "unknown"
                for t, synonyms in SYNONYMS.items():
                    if any(re.search(rf"\b{s}\b", full_text) for s in synonyms):
                        etype = t
                        break

                city_data = CITY_DB.get(location)
                confidence = 0.5 # Default neutral

                # A. News Reference Check (Only for non-quantitative markets or as secondary confirmation)
                matching_alerts = []
                for a in all_alerts:
                    if a.location == location:
                        market_words = set(re.findall(r"\w+", title.lower()))
                        alert_words = set(re.findall(r"\w+", a.description.lower()))
                        if a.event_type == etype or len(market_words.intersection(alert_words)) >= 3:
                            matching_alerts.append(a)

                if matching_alerts:
                    best_alert = max(matching_alerts, key=lambda a: a.confidence)
                    # User: Do not let news alerts override quantitative forecast logic for Temp/Rain/Quake
                    if etype not in ["temperature", "rain", "earthquake"]:
                        confidence = max(confidence, best_alert.confidence)

                    triggering_news_objs = [a.__dict__ for a in matching_alerts]
                    analysis_steps.append(f"Found {len(matching_alerts)} matching news alerts from {best_alert.source}.")
                    # self.add_log(f"  [NEWS] Found matching {best_alert.source} alert for {location}.")

                # B. Temperature and Precipitation Logic (with Local Caching)
                if etype in ["temperature", "rain"] and city_data:
                    cache_key = f"{location}_{date_str}_{etype}"
                    thresh = self.parse_numeric_threshold(title)

                    # Enforce Quantity Check: If market mentions a value/range but we couldn't parse it, skip.
                    if any(kw in title.lower() for kw in ["inch", "mm", "°", "degree", "at least", "less than"]) and not thresh:
                        self.add_log(f"  [SKIP] {m.get('id')} mentions quantity but parsing failed.")
                        continue

                    if etype == "temperature":
                        if thresh:
                            if cache_key not in local_forecast_cache:
                                local_forecast_cache[cache_key] = await self.get_forecast_max_temp(session, city_data[0], city_data[1], date_str)

                            forecast_max = local_forecast_cache[cache_key]
                            if forecast_max is not None:
                                target_val = forecast_max
                                if thresh["unit"] == "F": target_val = (forecast_max * 9/5) + 32

                                # Strict Quantitative Analysis:
                                # 1. If diff <= 0.5 -> High Confidence YES (0.95)
                                # 2. If diff >= 3.0 -> Strong NO (0.05)
                                # 3. Otherwise -> SKIP (0.5)

                                # User Rule: Diff <= 0.5 (YES), Diff >= 3.0 (NO/YES based on logic), Diff 1-2 (SKIP)
                                abs_diff = abs(target_val - (thresh.get("value") or 0 if thresh["type"] != "range" else (thresh["min"] if target_val < thresh["min"] else thresh["max"] if target_val > thresh["max"] else target_val)))

                                if thresh["type"] == "exact":
                                    if abs_diff <= 0.5: confidence = 0.95
                                    elif abs_diff >= 3.0: confidence = 0.05
                                    else: confidence = 0.5
                                elif thresh["type"] == "at_least":
                                    if target_val >= thresh["value"] + 3.0 or abs(target_val - thresh["value"]) <= 0.5:
                                        confidence = 0.95
                                    elif target_val <= thresh["value"] - 3.0:
                                        confidence = 0.05
                                    else:
                                        confidence = 0.5
                                elif thresh["type"] == "less_than":
                                    if target_val <= thresh["value"] - 3.0 or abs(target_val - thresh["value"]) <= 0.5:
                                        confidence = 0.95
                                    elif target_val >= thresh["value"] + 3.0:
                                        confidence = 0.05
                                    else:
                                        confidence = 0.5
                                elif thresh["type"] == "range":
                                    if thresh["min"] <= target_val <= thresh["max"]:
                                        dist_to_edge = min(abs(target_val - thresh["min"]), abs(target_val - thresh["max"]))
                                        if dist_to_edge <= 0.5 or (target_val - thresh["min"] >= 3.0 and thresh["max"] - target_val >= 3.0):
                                            confidence = 0.95
                                        else:
                                            confidence = 0.5
                                    else:
                                        dist_to_edge = min(abs(target_val - thresh["min"]), abs(target_val - thresh["max"]))
                                        if dist_to_edge >= 3.0: confidence = 0.05
                                        else: confidence = 0.5

                                analysis_steps.append(f"Temperature analysis: Forecast {target_val:.1f}{thresh['unit']} vs {thresh['type']} {thresh.get('value') or (str(thresh.get('min')) + '-' + str(thresh.get('max')))}. Confidence: {confidence:.2f}")
                                self.add_log(f"  [DATA] {location} Temp: {target_val:.1f}{thresh['unit']} vs Market: {thresh['type']} {thresh.get('value') or thresh.get('min')}. Conf -> {confidence:.2f}", "DEBUG")

                    elif etype == "rain":
                        if thresh:
                            if cache_key not in local_forecast_cache:
                                local_forecast_cache[cache_key] = await self.get_forecast_precipitation(session, city_data[0], city_data[1], date_str)

                            forecast_sum = local_forecast_cache[cache_key]
                            if forecast_sum is not None:
                                target_val = forecast_sum
                                # Simple unit conversion if needed (Open-Meteo returns mm by default)
                                if thresh["unit"] == "inch": target_val = forecast_sum / 25.4

                                edge_val = target_val - (thresh.get("value") or thresh.get("min") or 0)
                                if thresh["type"] == "at_least":
                                    if edge_val >= 0.5: confidence = 0.95
                                    else: confidence = 0.05
                                elif thresh["type"] == "less_than":
                                    if edge_val <= -0.5: confidence = 0.95
                                    else: confidence = 0.05
                                elif thresh["type"] == "range":
                                    if thresh["min"] <= target_val <= thresh["max"]: confidence = 0.95
                                    else: confidence = 0.05

                                analysis_steps.append(f"Precipitation forecast for {location}: {target_val:.2f}{thresh['unit']}. Market threshold: {thresh['type']} {thresh.get('value') or thresh.get('min')}. Adjusted confidence to {confidence:.2f}.")

                # C. Hottest Year Rankings (Mutual Exclusion Logic)
                if "hottest year" in title.lower() and self.nasa_anomaly is not None:
                    prev_conf = confidence
                    if self.nasa_anomaly > 1.15: # Extreme anomaly, almost certainly #1
                        if any(kw in title.lower() for kw in ["hottest", "first", "1st"]): confidence = 0.98
                        else: confidence = 0.02 # All other ranks are NO
                    elif self.nasa_anomaly > 0.95: # Very hot, likely #2 or #3
                        if any(kw in title.lower() for kw in ["second", "2nd"]): confidence = 0.85
                        elif any(kw in title.lower() for kw in ["third", "3rd"]): confidence = 0.70
                        elif any(kw in title.lower() for kw in ["hottest", "first", "1st"]): confidence = 0.15
                        else: confidence = 0.10
                    elif self.nasa_anomaly < 0.5: # Cool year relative to trend
                        if "lower" in title.lower() or "6th" in title.lower(): confidence = 0.80
                        else: confidence = 0.20
                    analysis_steps.append(f"NASA Global Anomaly: {self.nasa_anomaly}°C. Mutual Exclusion adjustment for ranking: {prev_conf:.2f} -> {confidence:.2f}.")
                    self.add_log(f"  [NASA] Global Anomaly: {self.nasa_anomaly}°C. Mutual Exclusion adjustment for ranking.")

                # D. Arctic Sea Ice
                if "arctic sea ice" in title.lower() and self.nasa_anomaly is not None:
                    if self.nasa_anomaly > 1.0 and any(kw in title.lower() for kw in ["min", "minimum", "lowest"]):
                        confidence = 0.88
                        analysis_steps.append(f"Arctic Sea Ice analysis: High NASA anomaly ({self.nasa_anomaly}) suggests record low. Confidence -> {confidence:.2f}.")

                # E. Earthquake Logic (Mutual Exclusion)
                if any(kw in title.lower() for kw in ["earthquake", "megaquake"]):
                    exactly_match = re.search(r"exactly (\d+)", title, re.IGNORECASE)
                    more_than_match = re.search(r"more than (\d+)", title, re.IGNORECASE)

                    # Determine Magnitude threshold
                    mag_val = 6.5
                    mag_match = re.search(r"(\d+\.\d+)", title)
                    if mag_match: mag_val = float(mag_match.group(1))

                    # Fetch current count for the period (assuming weekly/monthly)
                    # Use the parsed market date as the end bound
                    end_bound = date_str if "-" in date_str and len(date_str) > 7 else "2026-03-22"
                    start_bound = (datetime.strptime(end_bound, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")

                    current_count = await self.fetch_earthquake_count(session, mag_val, start_bound, end_bound)
                    self.add_log(f"  [DATA] Global {mag_val}+ Earthquake count ({start_bound} to {end_bound}): {current_count}")

                    prev_conf = confidence
                    if exactly_match:
                        target_n = int(exactly_match.group(1))
                        if current_count > target_n:
                            confidence = 0.01 # Impossible
                        elif current_count == target_n:
                            # If we hit the exact count, we only bet YES if there's very little time left
                            days_left = (datetime.strptime(end_bound, "%Y-%m-%d") - datetime.now()).days
                            if days_left <= 1: confidence = 0.85
                            else: confidence = 0.5 # Still time for more, so risky
                        else:
                            # If count < target, the user says "If the count is 0 then NO"
                            # We'll bet Strong NO (0.05) if we haven't reached the target yet.
                            confidence = 0.05
                    elif more_than_match:
                        target_n = int(more_than_match.group(1))
                        if current_count > target_n:
                            confidence = 0.99 # Already happened
                        else:
                            # User: "If count is 0 then NO"
                            confidence = 0.05

                    analysis_steps.append(f"Earthquake analysis: Global {mag_val}+ count is {current_count}. Target: {target_n if exactly_match else 'More than ' + str(target_n)}. Adjusted confidence: {prev_conf:.2f} -> {confidence:.2f}.")

                # 4. Final Trade Execution
                if confidence != 0.5:
                    await self.execute_trade(m, confidence, etype,
                                           analysis=" | ".join(analysis_steps),
                                           triggering_news=triggering_news_objs)

            self.add_log(f"Pipeline Scan Finished. Summary: {len(all_alerts)} alerts, {len(cached_markets)} markets analyzed.")

    async def resolve_trades(self, session: aiohttp.ClientSession):
        """Checks if open positions have resolved and updates metrics."""
        if not self.open_positions:
            return

        self.add_log(f"Checking resolution for {len(self.open_positions)} positions...")
        still_open = []

        for pos in self.open_positions:
            market_id = pos.get("market_id")
            if not market_id:
                still_open.append(pos)
                continue

            try:
                url = f"https://gamma-api.polymarket.com/markets/{market_id}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        m_data = await resp.json()
                        if m_data.get("closed"):
                            try:
                                prices_raw = m_data.get("outcomePrices", "[0,0]")
                                if isinstance(prices_raw, str):
                                    prices = json.loads(prices_raw)
                                else:
                                    prices = prices_raw

                                side_idx = 0 if pos["side"] == "YES" else 1
                                final_price = float(prices[side_idx])

                                # Tokens bought = amount / entry_price
                                # Payout = tokens * final_price (usually 1.0 or 0.0)
                                if pos["price"] > 0:
                                    tokens = pos["amount"] / pos["price"]
                                    payout = tokens * final_price
                                else:
                                    payout = 0
                                profit = payout - pos["amount"]

                                self.metrics["total_trades"] += 1
                                self.metrics["total_profit"] += profit
                                self.metrics["balance"] += payout

                                # Calculate win rate based on all resolved trades
                                wins = len([p for p in self.resolved_positions if p.get("profit", 0) > 0])
                                if profit > 0: wins += 1
                                self.metrics["win_rate"] = (wins / self.metrics["total_trades"]) * 100

                                pos["profit"] = profit
                                pos["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                self.resolved_positions.append(pos)
                                self.add_log(f"Trade Resolved: {pos['question'][:30]} | Profit: ${profit:+.2f}")
                            except Exception as e:
                                self.add_log(f"Error parsing resolution for {market_id}: {e}", "ERROR")
                                still_open.append(pos)
                        else:
                            still_open.append(pos)
                    else:
                        still_open.append(pos)
            except Exception as e:
                self.add_log(f"Resolution check failed for {market_id}: {e}", "WARNING")
                still_open.append(pos)

        self.open_positions = still_open

    async def _loop(self):
        async with aiohttp.ClientSession() as session:
            while self.is_running:
                try:
                    await self.run_pipeline()
                    await self.resolve_trades(session)
                except Exception as e:
                    self.add_log(f"Pipeline error: {e}", "ERROR")

                try:
                    # Wait for interval or immediate trigger
                    await asyncio.wait_for(self._scan_event.wait(), timeout=self.config["scan_interval"] * 60)
                    self._scan_event.clear()
                except (asyncio.TimeoutError, Exception):
                    pass

    def initialize(self):
        """Starts the background scanning loop."""
        if self.is_running: return
        self.is_running = True
        self.add_log("Background Scanner initialized.")

        # Initialize CLOB Client for price fetching (Paper Mode/Discovery)
        # Using a fixed placeholder for discovery and paper mode
        dummy_key = "0x" + "1" * 64
        self.clob_client = ClobClient("https://clob.polymarket.com", key=dummy_key, chain_id=137)

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
        # Trigger immediate scan
        if self._loop_task:
            try:
                self._loop_task.get_loop().call_soon_threadsafe(self._scan_event.set)
            except: pass

        if not self.config["paper_mode"]:
            try:
                pk = self.config.get("private_key")
                if not pk:
                    raise ValueError("Private key missing for live mode")
                if not pk.startswith("0x"):
                    pk = "0x" + pk

                # Extract wallet address from private key
                account = Account.from_key(pk)
                wallet_address = account.address
                self.config["wallet_address"] = wallet_address

                self.add_log(f"Initializing Live Client for: {wallet_address}")
                self.clob_client = ClobClient(
                    "https://clob.polymarket.com",
                    key=pk,
                    chain_id=137,
                    signature_type=0,
                    funder=wallet_address
                )
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
            "resolved_positions": self.resolved_positions[-10:],
            "scanned_markets": self.scanned_markets[:50],
            "total_scanned": len(self.scanned_markets),
            "news_events": self.news_events[:20],
            "dev_check_logs": self.dev_check_logs[-50:],
            "logs": self.logs[-20:],
            "config": {k: v for k, v in self.config.items() if "key" not in k} # Don't send keys to UI
        }
