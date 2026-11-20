import streamlit as st
import sqlite3
import requests
import json
import hashlib
import secrets
import urllib.parse
import re
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit.components.v1 as components

DB = Path(__file__).with_name("highway_alerts.db")
API = "https://api.open-meteo.com/v1/forecast"

# Balochistan Highway Corridors with intermediate coordinates and checkpoints
ROUTES_DATA = {
    "Quetta–Zhob (N-50)": {
        "code": "N-50",
        "distance": "331 km",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kuchlak", "lat": 30.3125, "lon": 67.0114, "elevation": "1,560m"},
            {"name": "Khan Mehtarzai", "lat": 30.4833, "lon": 67.6167, "elevation": "2,224m"},
            {"name": "Muslim Bagh", "lat": 30.8317, "lon": 67.7408, "elevation": "1,787m"},
            {"name": "Qilla Saifullah", "lat": 30.7000, "lon": 68.3600, "elevation": "1,550m"},
            {"name": "Zhob", "lat": 31.3411, "lon": 69.4481, "elevation": "1,426m"},
        ]
    },
    "Quetta–Karachi (N-25)": {
        "code": "N-25",
        "distance": "688 km",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Mastung", "lat": 29.7997, "lon": 66.8455, "elevation": "1,701m"},
            {"name": "Kalat", "lat": 29.0266, "lon": 66.5936, "elevation": "2,007m"},
            {"name": "Surab", "lat": 28.4914, "lon": 66.2585, "elevation": "1,750m"},
            {"name": "Khuzdar", "lat": 27.8000, "lon": 66.6167, "elevation": "1,237m"},
            {"name": "Wadh", "lat": 27.3436, "lon": 66.3708, "elevation": "1,220m"},
            {"name": "Lasbela", "lat": 26.2289, "lon": 66.3106, "elevation": "87m"},
            {"name": "Hub", "lat": 25.0244, "lon": 66.8906, "elevation": "24m"},
        ]
    },
    "Quetta–Sibi (N-65)": {
        "code": "N-65",
        "distance": "163 km",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kolpur (Bolan Pass)", "lat": 29.9000, "lon": 67.1500, "elevation": "1,790m"},
            {"name": "Mach", "lat": 29.8637, "lon": 67.3302, "elevation": "1,006m"},
            {"name": "Dhadar", "lat": 29.4749, "lon": 67.6514, "elevation": "132m"},
            {"name": "Sibi", "lat": 29.5430, "lon": 67.8773, "elevation": "130m"},
        ]
    },
    "Quetta–Chaman (N-25 North)": {
        "code": "N-25N",
        "distance": "125 km",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kuchlak", "lat": 30.3125, "lon": 67.0114, "elevation": "1,560m"},
            {"name": "Khojak Pass (Shelabagh)", "lat": 30.8050, "lon": 66.5680, "elevation": "2,290m"},
            {"name": "Chaman", "lat": 30.9177, "lon": 66.4526, "elevation": "1,338m"},
        ]
    },
    "Quetta–Nushki–Taftan (N-40)": {
        "code": "N-40",
        "distance": "610 km",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Lakpass", "lat": 29.9650, "lon": 66.8200, "elevation": "1,810m"},
            {"name": "Nushki", "lat": 29.5522, "lon": 66.0215, "elevation": "1,020m"},
            {"name": "Dalbandin", "lat": 28.8885, "lon": 64.4062, "elevation": "843m"},
            {"name": "Nok Kundi", "lat": 28.8261, "lon": 62.7489, "elevation": "680m"},
            {"name": "Taftan", "lat": 28.9667, "lon": 61.5833, "elevation": "910m"},
        ]
    },
    "Quetta–Loralai–DG Khan (N-70)": {
        "code": "N-70",
        "distance": "425 km",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Ziarat Cross", "lat": 30.3824, "lon": 67.7256, "elevation": "2,450m"},
            {"name": "Sanjawi", "lat": 30.2856, "lon": 68.3489, "elevation": "1,620m"},
            {"name": "Loralai", "lat": 30.3705, "lon": 68.5979, "elevation": "1,430m"},
            {"name": "Rakhni", "lat": 30.0683, "lon": 69.9214, "elevation": "1,110m"},
        ]
    },
}

ROUTES = list(ROUTES_DATA.keys())
LANGUAGES = ["Urdu", "Pashto", "Balochi"]
ROAD_STATUSES = ["Open (Verified)", "Restricted — Caution", "Closed — Emergency", "Clearance Pending"]

st.set_page_config(
    page_title="Balochistan Smart Highway Watch | Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def logo_svg(size=46):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 100 100">
    <defs>
      <linearGradient id="govGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#14b8a6"/>
        <stop offset="50%" stop-color="#0ea5e9"/>
        <stop offset="100%" stop-color="#2563eb"/>
      </linearGradient>
      <linearGradient id="shieldBg" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#0f253c"/>
        <stop offset="100%" stop-color="#071322"/>
      </linearGradient>
    </defs>
    <path d="M50 4 L90 20 V50 C90 74 72 90 50 96 C28 90 10 74 10 50 V20 Z" fill="url(#shieldBg)" stroke="url(#govGrad)" stroke-width="4"/>
    <path d="M24 68 Q38 48 52 54 T78 30" fill="none" stroke="url(#govGrad)" stroke-width="6" stroke-linecap="round"/>
    <path d="M26 75 L40 52 L49 60 L62 38 L76 52" fill="none" stroke="#e2e8f0" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.85"/>
    <circle cx="50" cy="27" r="7" fill="#14b8a6"/>
    <circle cx="50" cy="27" r="3" fill="#071322"/>
    <path d="M32 82 H68" stroke="#38bdf8" stroke-width="3" stroke-linecap="round"/>
    </svg>"""

def hash_password(password: str, salt: str | None = None) -> str:
    """Salted PBKDF2-HMAC-SHA256 password hashing (backwards-compatible with legacy SHA-256)."""
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"

def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    """Returns (is_valid, needs_upgrade_to_salted)."""
    if not stored_hash:
        return (False, False)
    if stored_hash.startswith("pbkdf2_sha256$"):
        parts = stored_hash.split("$", 2)
        if len(parts) != 3:
            return (False, False)
        _, salt, expected_hex = parts
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
        return (secrets.compare_digest(dk.hex(), expected_hex), False)
    # Legacy plain SHA-256 support
    legacy_hex = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if secrets.compare_digest(legacy_hex, stored_hash):
        return (True, True)
    return (False, False)

def is_valid_username(username: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", username))

def is_valid_pk_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-()]", "", phone.strip())
    return bool(re.fullmatch(r"(\+92|0092|0)?3\d{9}", cleaned))

def is_valid_plate(plate: str) -> bool:
    cleaned = re.sub(r"\s+", "", plate.strip().upper())
    return bool(re.fullmatch(r"[A-Z]{2,5}-?\d{2,4}[A-Z]?", cleaned))

def connect():
    con = sqlite3.connect(DB, timeout=15, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with connect() as con:
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            department TEXT DEFAULT 'PDMA / NHA Operations',
            role TEXT DEFAULT 'Control Room Operator',
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_code TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            vehicle_type TEXT DEFAULT 'Heavy Transport',
            route TEXT NOT NULL,
            language TEXT NOT NULL,
            status TEXT DEFAULT 'Active on Route',
            created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            route TEXT NOT NULL,
            location TEXT NOT NULL,
            officer_incharge TEXT DEFAULT 'Duty Officer',
            qr_scans INTEGER DEFAULT 0)""")
        con.execute("""CREATE TABLE IF NOT EXISTS road_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route TEXT NOT NULL,
            area TEXT NOT NULL,
            status TEXT NOT NULL,
            risk_score INTEGER DEFAULT 2,
            authority_note TEXT NOT NULL,
            verified_by TEXT DEFAULT 'Control Room Quetta',
            updated_at TEXT NOT NULL,
            UNIQUE(route, area))""")
        con.execute("""CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER,
            route TEXT NOT NULL,
            language TEXT DEFAULT 'Urdu',
            severity TEXT DEFAULT 'Advisory',
            message TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE SET NULL)""")

        # Auto-migrate if an older database schema exists
        existing_cols = {
            "drivers": [r[1] for r in con.execute("PRAGMA table_info(drivers)").fetchall()],
            "checkpoints": [r[1] for r in con.execute("PRAGMA table_info(checkpoints)").fetchall()],
            "road_status": [r[1] for r in con.execute("PRAGMA table_info(road_status)").fetchall()],
            "alerts": [r[1] for r in con.execute("PRAGMA table_info(alerts)").fetchall()],
        }
        if "driver_code" not in existing_cols["drivers"]:
            con.execute("ALTER TABLE drivers ADD COLUMN driver_code TEXT")
        if "vehicle_type" not in existing_cols["drivers"]:
            con.execute("ALTER TABLE drivers ADD COLUMN vehicle_type TEXT DEFAULT 'Heavy Transport'")
        if "status" not in existing_cols["drivers"]:
            con.execute("ALTER TABLE drivers ADD COLUMN status TEXT DEFAULT 'Active on Route'")
        if "code" not in existing_cols["checkpoints"]:
            con.execute("ALTER TABLE checkpoints ADD COLUMN code TEXT")
        if "officer_incharge" not in existing_cols["checkpoints"]:
            con.execute("ALTER TABLE checkpoints ADD COLUMN officer_incharge TEXT DEFAULT 'Duty Officer'")
        if "qr_scans" not in existing_cols["checkpoints"]:
            con.execute("ALTER TABLE checkpoints ADD COLUMN qr_scans INTEGER DEFAULT 0")
        if "risk_score" not in existing_cols["road_status"]:
            con.execute("ALTER TABLE road_status ADD COLUMN risk_score INTEGER DEFAULT 2")
        if "verified_by" not in existing_cols["road_status"]:
            con.execute("ALTER TABLE road_status ADD COLUMN verified_by TEXT DEFAULT 'Control Room Quetta'")
        if "language" not in existing_cols["alerts"]:
            con.execute("ALTER TABLE alerts ADD COLUMN language TEXT DEFAULT 'Urdu'")
        if "severity" not in existing_cols["alerts"]:
            con.execute("ALTER TABLE alerts ADD COLUMN severity TEXT DEFAULT 'Advisory'")

        # Ensure unique index on road_status(route, area) safely
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_road_route_area ON road_status(route, area)")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_driver_code ON drivers(driver_code)")

def rows(q, p=()):
    with connect() as con:
        return [dict(x) for x in con.execute(q, p).fetchall()]

def run(q, p=()):
    with connect() as con:
        cur = con.execute(q, p)
        con.commit()
        return cur.lastrowid

def seed():
    if not rows("SELECT id FROM users LIMIT 1"):
        run(
            "INSERT OR IGNORE INTO users(full_name,username,department,role,password_hash,created_at) VALUES(?,?,?,?,?,?)",
            ("Quetta Control Admin", "admin", "PDMA / NHA Balochistan", "Chief Command Officer", hash_password("admin123"), datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
    if not rows("SELECT id FROM checkpoints LIMIT 1"):
        idx = 101
        for route, rdata in ROUTES_DATA.items():
            for pt in rdata["points"]:
                run(
                    "INSERT OR IGNORE INTO checkpoints(code,name,route,location,officer_incharge,qr_scans) VALUES(?,?,?,?,?,?)",
                    (f"CP-{idx}", f"{pt['name']} Highway Gate", route, pt["name"], "Levies / NHA Post", idx % 47 + 12)
                )
                idx += 1
    if not rows("SELECT id FROM road_status LIMIT 1"):
        for route, rdata in ROUTES_DATA.items():
            for pt in rdata["points"]:
                default_status = "Open (Verified)"
                default_risk = 2
                note = "Normal traffic flow; regular patrol active."
                if "Khan Mehtarzai" in pt["name"] or "Khojak" in pt["name"]:
                    default_status = "Restricted — Caution"
                    default_risk = 6
                    note = "High altitude pass; strong crosswinds & low night visibility."
                elif "Kolpur" in pt["name"]:
                    default_status = "Open (Verified)"
                    default_risk = 4
                    note = "Bolan sector clear; watch for slippery bends."
                run(
                    "INSERT OR IGNORE INTO road_status(route,area,status,risk_score,authority_note,verified_by,updated_at) VALUES(?,?,?,?,?,?,?)",
                    (route, pt["name"], default_status, default_risk, note, "PDMA / NHA Control Room", datetime.now().strftime("%Y-%m-%d %H:%M"))
                )
    if not rows("SELECT id FROM drivers LIMIT 1"):
        sample_drivers = [
            ("BHW-2401", "Haji Abdul Wahid", "0300-8381920", "QTA-4821", "Passenger Coach", "Quetta–Karachi (N-25)", "Urdu", "Active on Route"),
            ("BHW-2402", "Sardar Khan Kakar", "0333-7812094", "ZHB-1190", "Cargo Truck", "Quetta–Zhob (N-50)", "Pashto", "Active on Route"),
            ("BHW-2403", "Mirwais Baloch", "0321-8904412", "KZD-7734", "Oil Tanker", "Quetta–Nushki–Taftan (N-40)", "Balochi", "Verified at Gate"),
            ("BHW-2404", "Noor Muhammad", "0312-9045123", "SIB-3092", "Pickup / Utility", "Quetta–Sibi (N-65)", "Urdu", "Active on Route"),
        ]
        for d in sample_drivers:
            run(
                "INSERT OR IGNORE INTO drivers(driver_code,name,phone,vehicle,vehicle_type,route,language,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (*d, datetime.now().strftime("%Y-%m-%d %H:%M"))
            )

def generate_unique_driver_code() -> str:
    existing = {r["driver_code"] for r in rows("SELECT driver_code FROM drivers WHERE driver_code IS NOT NULL")}
    num = 2401 + len(rows("SELECT id FROM drivers"))
    while f"BHW-{num}" in existing:
        num += 1
    return f"BHW-{num}"

@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,snowfall,weather_code,wind_speed_10m,wind_gusts_10m,surface_pressure",
        "hourly": "temperature_2m,precipitation_probability,precipitation,visibility,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "forecast_days": 7,
        "timezone": "Asia/Karachi"
    }
    response = requests.get(API, params=params, timeout=12)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or "current" not in data:
        raise ValueError("Invalid weather payload received")
    return data

def safe_float(val, default=None):
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default

def weather_info(code):
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = -1
    if code == 0:
        return ("Clear Sky", "صاف موسم", "☀️", 1)
    if code in (1, 2, 3):
        return ("Partly Cloudy", "ابر آلود", "⛅", 2)
    if code in (45, 48):
        return ("Dense Fog", "گہری دھند", "🌫️", 7)
    if code in (51, 53, 55, 56, 57):
        return ("Light Drizzle", "ہلکی بوندا باندی", "🌦️", 4)
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return ("Heavy Rain", "بارش / پھسلن", "🌧️", 7)
    if code in (71, 73, 75, 77, 85, 86):
        return ("Snowfall / Ice", "برف باری", "❄️", 9)
    if code in (95, 96, 99):
        return ("Thunderstorm", "آندھی اور گرج چمک", "⛈️", 9)
    return ("Variable / Telemetry Fallback", "موسمی تبدیلی", "🌤️", 3)

def compute_risk_score(cur, road_status_str, manual_risk=None):
    if "Closed" in (road_status_str or ""):
        return 10
    score = 1
    if "Restricted" in (road_status_str or ""):
        score = max(score, 6)
    elif "Pending" in (road_status_str or ""):
        score = max(score, 4)
    if manual_risk is not None:
        try:
            score = max(score, int(manual_risk))
        except (TypeError, ValueError):
            pass
    if cur:
        code = cur.get("weather_code")
        if code is not None:
            _, _, _, w_risk = weather_info(code)
            score = max(score, w_risk)
        wind = safe_float(cur.get("wind_speed_10m"), 0.0)
        precip = safe_float(cur.get("precipitation"), 0.0)
        if wind > 35:
            score = max(score, 7)
        elif wind > 22:
            score = max(score, 5)
        if precip > 2.0:
            score = max(score, 8)
    return max(1, min(int(score), 10))

def risk_meta(score):
    if score <= 2:
        return ("SAFE / NORMAL", "#10b981", "rgba(16,185,129,0.16)")
    if score <= 4:
        return ("MARGINAL", "#38bdf8", "rgba(56,189,248,0.16)")
    if score <= 6:
        return ("MODERATE CAUTION", "#f59e0b", "rgba(245,158,11,0.18)")
    if score <= 8:
        return ("HIGH RISK", "#f97316", "rgba(249,115,22,0.20)")
    return ("EXTREME / CLOSED", "#ef4444", "rgba(239,68,68,0.22)")

def generate_multilingual_alert(area, route, weather_en, weather_ur, road, lang):
    if lang == "Urdu":
        if "Closed" in road:
            return (
                f"ہنگامی شاہراہ الرٹ ({route}): {area} کے مقام پر سڑک ٹریفک کے لیے بند کر دی گئی ہے۔ "
                f"موسمی صورتحال: {weather_ur}۔ براہِ کرم غیر ضروری سفر سے گریز کریں اور قریبی چیک پوسٹ پر انتظار کریں۔",
                "مقام بند ہے — متبادل راستہ اختیار کریں یا سرکاری کلیئرنس کا انتظار کریں۔"
            )
        if "Restricted" in road:
            return (
                f"سفری انتباہ ({route}): {area} سیکٹر میں {weather_ur} کے باعث احتیاطی پابندی نافذ ہے۔ "
                f"رفتار کم رکھیں، فوگ لائٹس آن رکھیں اور اگلی گاڑی سے محفوظ فاصلہ برقرار رکھیں۔",
                "رات کے اوقات میں پہاڑی دروں پر سفر سے اجتناب کریں۔"
            )
        return (
            f"موسمی اپ ڈیٹ ({route}): {area} کے اطراف میں موسم {weather_ur} ہے اور شاہراہ کھلی ہے۔ "
            f"محفوظ ڈرائیونگ کے اصولوں پر عمل کریں اور چیک پوسٹ پر کیو آر کوڈ اسکین کروائیں۔",
            "سفر جاری رکھا جا سکتا ہے — رفتار کی حد کی پابندی کریں۔"
        )
    elif lang == "Pashto":
        if "Closed" in road:
            return (
                f"بیړنی خبرتیا ({route}): د {area} په سیمه کې لویه لاره د ترافیکو پر مخ تړل شوې ده. "
                f"مهرباني وکړئ سفر مه کوئ او د چارواکو تر بلې خبرتیا پورې په نږدې پوسته کې تم شئ.",
                "لاره تړلې ده — د رسمي تایید انتظار وکړئ."
            )
        if "Restricted" in road:
            return (
                f"د احتیاط خبرتیا ({route}): په {area} کې د خرابې هوا ({weather_en}) له امله احتیاط اړین دی. "
                f"مهرباني وکړئ سرعت کم کړئ او د موټرو ترمنځ فاصله وساتئ.",
                "په غرنیو لارو کې په احتیاط سره موټر چلوئ."
            )
        return (
            f"د هوا تازه معلومات ({route}): د {area} په سیمه کې لاره خلاصه ده او هوا {weather_en} ده. "
            f"خپل سفر په خوندي توګه ترسره کړئ.",
            "لاره خلاصه ده — د ترافیکي قوانینو مراعات وکړئ."
        )
    else:  # Balochi
        if "Closed" in road:
            return (
                f"هنگامی حال ({route}): {area} ءِ دمگ ءَ شاهراه ٹریفک ءِ واستہ بند کنگ بوتگ۔ "
                f"مهربانی کن ات سفر مه کن ات ءُ نزیکیں چیک پوسٹ ءَ ودار کن ات۔",
                "راه بند انت — سرکاری موکل ءِ ودار ءَ کن ات۔"
            )
        if "Restricted" in road:
            return (
                f"هوشیاری حال ({route}): {area} ءِ تها موسم ({weather_en}) ءِ سوب ءَ هوشیاری المی انت۔ "
                f"گاڑی ءِ رفتار کم کن ات ءُ دگہ گاڑیاں چہ دور دار ات۔",
                "شپ ءِ وهد ءَ کوهی راهانی سر ءَ سفر مه کن ات۔"
            )
        return (
            f"موسمی حال ({route}): {area} ءِ دمگ ءَ شاهراه پچ انت ءُ موسم {weather_en} انت۔ "
            f"سلامتی ءَ گوں وتی سفر ءَ برجاہ دار ات۔",
            "شاهراه پچ انت — چیک پوسٹ ءَ کیو آر کوڈ اسکین کنائین ات۔"
        )

def render_balochistan_map(selected_route, weather_cache, road_map, layers):
    routes_payload = []
    for r_name, r_data in ROUTES_DATA.items():
        pts_out = []
        max_r = 1
        for pt in r_data["points"]:
            w_cur = weather_cache.get(pt["name"], {})
            r_row = road_map.get((r_name, pt["name"]), {})
            r_stat = r_row.get("status", "Open (Verified)")
            r_score = compute_risk_score(w_cur, r_stat, r_row.get("risk_score"))
            max_r = max(max_r, r_score)
            has_weather = bool(w_cur and ("temperature_2m" in w_cur or "weather_code" in w_cur))
            label_txt, _, _, _ = weather_info(w_cur.get("weather_code")) if has_weather else ("Cached / Offline", "", "🛰️", 2)
            temp_disp = f"{safe_float(w_cur.get('temperature_2m')):.1f}" if safe_float(w_cur.get("temperature_2m")) is not None else "—"
            wind_disp = f"{safe_float(w_cur.get('wind_speed_10m')):.1f}" if safe_float(w_cur.get("wind_speed_10m")) is not None else "—"
            precip_disp = f"{safe_float(w_cur.get('precipitation')):.1f}" if safe_float(w_cur.get("precipitation")) is not None else "—"
            pts_out.append({
                "name": pt["name"],
                "lat": pt["lat"],
                "lon": pt["lon"],
                "elev": pt["elevation"],
                "temp": temp_disp,
                "wind": wind_disp,
                "precip": precip_disp,
                "weather": label_txt,
                "status": r_stat,
                "risk": r_score
            })
        _, color_hex, _ = risk_meta(max_r)
        routes_payload.append({
            "name": r_name,
            "code": r_data["code"],
            "distance": r_data["distance"],
            "selected": (r_name == selected_route),
            "color": color_hex,
            "max_risk": max_r,
            "points": pts_out
        })

    payload_json = json.dumps(routes_payload).replace("</", "<\\/")
    layers_json = json.dumps(layers).replace("</", "<\\/")
    hud_route_safe = json.dumps(selected_route).replace("</", "<\\/")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <style>
        html, body, #map {{
          height: 100%; width: 100%; margin: 0; padding: 0;
          background: #060e1a; font-family: 'Inter', system-ui, sans-serif;
        }}
        .leaflet-container {{ background: #060e1a !important; }}
        .legend-bar {{
          position: absolute; top: 12px; left: 54px; z-index: 999;
          background: rgba(9, 20, 36, 0.90); backdrop-filter: blur(10px);
          border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px;
          padding: 8px 14px; color: #e2e8f0; font-size: 11px;
          display: flex; align-items: center; gap: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }}
        .scale-boxes {{ display: flex; gap: 2px; }}
        .scale-box {{
          width: 18px; height: 14px; display: flex; align-items: center; justify-content: center;
          font-weight: 700; font-size: 9px; color: #04101d; border-radius: 2px;
        }}
        .map-hud {{
          position: absolute; bottom: 16px; left: 16px; z-index: 999;
          background: rgba(9, 20, 36, 0.92); backdrop-filter: blur(10px);
          border: 1px solid rgba(20, 184, 166, 0.35); border-radius: 12px;
          padding: 12px 16px; color: #f1f5f9; min-width: 240px; max-width: 340px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        }}
        .hud-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #2dd4bf; font-weight: 700; }}
        .hud-route {{ font-size: 15px; font-weight: 800; margin: 3px 0 6px 0; }}
        .hud-meta {{ font-size: 11px; color: #94a3b8; line-height: 1.5; }}
        .custom-popup .leaflet-popup-content-wrapper {{
          background: #0b192c; color: #f1f5f9; border: 1px solid #1e3a5f; border-radius: 12px;
        }}
        .custom-popup .leaflet-popup-tip {{ background: #0b192c; }}
      </style>
    </head>
    <body>
      <div id="map"></div>
      <div class="legend-bar">
        <span style="font-weight:700;color:#94a3b8;">ROAD DANGER INDEX</span>
        <div class="scale-boxes">
          <div class="scale-box" style="background:#10b981;">1</div>
          <div class="scale-box" style="background:#34d399;">2</div>
          <div class="scale-box" style="background:#38bdf8;">3</div>
          <div class="scale-box" style="background:#60a5fa;">4</div>
          <div class="scale-box" style="background:#facc15;">5</div>
          <div class="scale-box" style="background:#f59e0b;">6</div>
          <div class="scale-box" style="background:#fb923c;">7</div>
          <div class="scale-box" style="background:#f97316;">8</div>
          <div class="scale-box" style="background:#ef4444;color:#fff;">9</div>
          <div class="scale-box" style="background:#dc2626;color:#fff;">10</div>
        </div>
        <span style="color:#64748b;">Safe → Extreme</span>
      </div>

      <div class="map-hud" id="hudCard">
        <div class="hud-title">ACTIVE CORRIDOR TELEMETRY</div>
        <div class="hud-route" id="hudRouteName"></div>
        <div class="hud-meta" id="hudRouteMeta">Click any checkpoint node for live meteorological & clearance telemetry.</div>
      </div>

      <script>
        const routesData = {payload_json};
        const activeLayers = {layers_json};
        document.getElementById('hudRouteName').innerText = {hud_route_safe};

        const map = L.map('map', {{
          center: [28.95, 65.85],
          zoom: 6,
          zoomControl: true
        }});

        const primaryTiles = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
          attribution: '&copy; OpenStreetMap &copy; CARTO | Balochistan Highway Watch',
          subdomains: 'abcd',
          maxZoom: 18
        }});
        const fallbackTiles = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
          attribution: '&copy; OpenStreetMap contributors',
          maxZoom: 18
        }});

        let fallbackApplied = false;
        primaryTiles.on('tileerror', () => {{
          if (!fallbackApplied) {{
            fallbackApplied = true;
            map.removeLayer(primaryTiles);
            fallbackTiles.addTo(map);
          }}
        }});
        primaryTiles.addTo(map);

        let selectedBounds = [];

        routesData.forEach(route => {{
          const latlngs = route.points.map(p => [p.lat, p.lon]);
          const isSel = route.selected;

          if (activeLayers.highways) {{
            L.polyline(latlngs, {{
              color: route.color,
              weight: isSel ? 12 : 6,
              opacity: isSel ? 0.25 : 0.12
            }}).addTo(map);

            const line = L.polyline(latlngs, {{
              color: route.color,
              weight: isSel ? 4.5 : 2.5,
              opacity: isSel ? 0.95 : 0.65,
              dashArray: isSel ? null : '6, 6'
            }}).addTo(map);

            line.bindTooltip(`${{route.name}} (${{route.distance}}) • Max Risk: ${{route.max_risk}}/10`, {{sticky: true}});
          }}

          route.points.forEach(pt => {{
            if (isSel) selectedBounds.push([pt.lat, pt.lon]);

            let ptColor = '#10b981';
            if (pt.risk >= 9) ptColor = '#ef4444';
            else if (pt.risk >= 7) ptColor = '#f97316';
            else if (pt.risk >= 5) ptColor = '#f59e0b';
            else if (pt.risk >= 3) ptColor = '#38bdf8';

            if (activeLayers.weather_radar) {{
              L.circle([pt.lat, pt.lon], {{
                radius: isSel ? 34000 : 22000,
                color: ptColor,
                weight: 1,
                fillColor: ptColor,
                fillOpacity: isSel ? 0.16 : 0.08
              }}).addTo(map);
            }}

            if (activeLayers.checkpoints) {{
              const marker = L.circleMarker([pt.lat, pt.lon], {{
                radius: isSel ? 7.5 : 5,
                fillColor: ptColor,
                color: '#ffffff',
                weight: isSel ? 2 : 1,
                opacity: 1,
                fillOpacity: 0.95
              }}).addTo(map);

              const popupHtml = `
                <div style="min-width:210px;font-family:Inter,sans-serif;">
                  <div style="font-size:10px;color:#2dd4bf;font-weight:700;letter-spacing:0.8px;">${{route.code}} CHECKPOINT</div>
                  <div style="font-size:15px;font-weight:800;margin:2px 0 8px 0;">${{pt.name}} <span style="font-size:11px;color:#94a3b8;font-weight:400;">(${{pt.elev}})</span></div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;background:#07111f;padding:8px;border-radius:8px;margin-bottom:8px;">
                    <div><span style="color:#64748b;">Temp:</span> <b>${{pt.temp}} °C</b></div>
                    <div><span style="color:#64748b;">Wind:</span> <b>${{pt.wind}} km/h</b></div>
                    <div><span style="color:#64748b;">Rain:</span> <b>${{pt.precip}} mm</b></div>
                    <div><span style="color:#64748b;">Risk:</span> <b style="color:${{ptColor}};">${{pt.risk}}/10</b></div>
                  </div>
                  <div style="font-size:11px;"><b>Condition:</b> ${{pt.weather}}</div>
                  <div style="font-size:11px;margin-top:3px;"><b>Clearance:</b> <span style="color:${{ptColor}};">${{pt.status}}</span></div>
                </div>
              `;
              marker.bindPopup(popupHtml, {{className: 'custom-popup'}});
              marker.on('click', () => {{
                document.getElementById('hudRouteMeta').innerHTML =
                  `<b>${{pt.name}}</b> (${{pt.elev}}) • Temp: <b>${{pt.temp}}°C</b> • Wind: <b>${{pt.wind}} km/h</b><br/>Status: <span style="color:${{ptColor}};">${{pt.status}}</span> (Risk ${{pt.risk}}/10)`;
              }});

              if (isSel) {{
                marker.bindTooltip(`${{pt.name}} (${{pt.temp}}°C)`, {{
                  permanent: true,
                  direction: 'top',
                  offset: [0, -8]
                }});
              }}
            }}
          }});
        }});

        if (selectedBounds.length > 1) {{
          map.fitBounds(selectedBounds, {{padding: [55, 55]}});
        }}
      </script>
    </body>
    </html>
    """
    components.html(html, height=490, scrolling=False)

# Initialize database & seed once per process
if "_db_initialized" not in st.session_state:
    init_db()
    seed()
    st.session_state["_db_initialized"] = True

# Custom Dark Tactical Government Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&family=Noto+Nastaliq+Urdu:wght@400;600;700&display=swap');

:root {
  --bg-deep: #050b14;
  --bg-panel: #0a1626;
  --bg-card: #0e1e33;
  --border-subtle: rgba(56, 189, 248, 0.16);
  --teal: #14b8a6;
  --cyan: #38bdf8;
  --text-main: #f1f5f9;
  --text-muted: #94a3b8;
}

.stApp {
  background: radial-gradient(circle at 18% 0%, #0d263d 0%, #060e1a 45%, #040811 100%);
  color: var(--text-main);
  font-family: 'Inter', sans-serif;
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #071220 0%, #0a192c 100%);
  border-right: 1px solid rgba(20, 184, 166, 0.2);
}

.block-container {
  padding-top: 1.1rem;
  padding-bottom: 2rem;
  max-width: 1580px;
}

h1, h2, h3, h4 {
  color: #f8fafc !important;
  font-family: 'Inter', sans-serif;
  letter-spacing: -0.02em;
}

.cmd-topbar {
  background: linear-gradient(90deg, rgba(10, 25, 44, 0.92) 0%, rgba(13, 39, 64, 0.88) 100%);
  border: 1px solid rgba(45, 212, 191, 0.25);
  border-radius: 16px;
  padding: 14px 22px;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
}
.cmd-title { font-size: 20px; font-weight: 800; color: #f8fafc; margin: 0; }
.cmd-sub { font-size: 12px; color: #94a3b8; margin-top: 2px; }
.live-badge {
  display: inline-flex; align-items: center; gap: 7px;
  background: rgba(16, 185, 129, 0.14); border: 1px solid rgba(16, 185, 129, 0.45);
  color: #34d399; padding: 5px 12px; border-radius: 999px;
  font-size: 11px; font-weight: 700; letter-spacing: 0.6px;
}
.live-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.stat-card {
  background: linear-gradient(155deg, #0e1f36 0%, #091423 100%);
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}
.stat-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8; font-weight: 600; }
.stat-val { font-size: 26px; font-weight: 800; color: #f8fafc; margin: 4px 0; font-family: 'JetBrains Mono', monospace; }
.stat-foot { font-size: 11px; color: #2dd4bf; }

.gauge-box {
  background: #0b1829;
  border: 1px solid rgba(56, 189, 248, 0.16);
  border-radius: 14px;
  padding: 12px 8px;
  text-align: center;
}
.gauge-ring {
  width: 68px; height: 68px; border-radius: 50%;
  margin: 6px auto;
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace; font-weight: 800; font-size: 15px; color: #f8fafc;
}
.gauge-title { font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8; font-weight: 700; }
.gauge-sub { font-size: 10px; color: #64748b; }

.side-panel-card {
  background: linear-gradient(180deg, #0c1b2e 0%, #081220 100%);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 14px;
}
.auth-card {
  background: linear-gradient(160deg, rgba(14, 31, 54, 0.96) 0%, rgba(8, 19, 34, 0.98) 100%);
  border: 1px solid rgba(45, 212, 191, 0.32);
  border-radius: 20px;
  padding: 28px 30px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.65);
}
.notif-item {
  background: rgba(15, 31, 53, 0.85);
  border-left: 3px solid #f59e0b;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 9px;
}
.notif-item.danger { border-left-color: #ef4444; }
.notif-item.safe { border-left-color: #10b981; }
.urdu-box {
  font-family: 'Noto Nastaliq Urdu', 'Inter', sans-serif;
  direction: rtl;
  text-align: right;
  line-height: 2.0;
  font-size: 15px;
  background: #081322;
  border: 1px solid rgba(20, 184, 166, 0.35);
  border-radius: 12px;
  padding: 14px 18px;
  color: #f1f5f9;
}

.stButton > button {
  border-radius: 10px;
  border: 1px solid rgba(45, 212, 191, 0.45);
  background: linear-gradient(90deg, #0d9488 0%, #0284c7 100%);
  color: #ffffff;
  font-weight: 700;
  transition: all 0.2s ease;
}
.stButton > button:hover {
  border-color: #5eead4;
  box-shadow: 0 0 16px rgba(20, 184, 166, 0.45);
  color: #ffffff;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# AUTHENTICATION GATE (SIGN IN / SIGN UP)
# ==============================================================================
if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

if st.session_state["auth_user"] is None:
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1.05, 1.35, 1.05])

    with center_col:
        st.markdown(f"""
        <div class="auth-card" style="text-align:center;margin-bottom:14px;">
          {logo_svg(68)}
          <div style="font-size:22px;font-weight:800;color:#f8fafc;margin-top:10px;letter-spacing:-0.3px;">
            Balochistan Smart Highway Watch
          </div>
          <div style="font-size:12px;color:#2dd4bf;font-weight:700;letter-spacing:1px;margin-top:3px;">
            GOVERNMENT COMMAND & WEATHER INTELLIGENCE PORTAL
          </div>
          <div style="font-size:12px;color:#94a3b8;margin-top:8px;">
            Authorized access for PDMA, NHA, Levies Checkpoints & Control Room Operators
          </div>
        </div>
        """, unsafe_allow_html=True)

        tab_signin, tab_signup = st.tabs(["🔐 Sign In (Operator Login)", "📝 Sign Up (Register Officer)"])

        with tab_signin:
            with st.form("signin_form"):
                u_login = st.text_input("Username", placeholder="Enter username (default: admin)")
                p_login = st.text_input("Password", type="password", placeholder="Enter password (default: admin123)")
                btn_login = st.form_submit_button("Sign In to Command Center", use_container_width=True)

            if btn_login:
                uname_clean = u_login.strip()
                if uname_clean and p_login:
                    matched = rows("SELECT * FROM users WHERE LOWER(username)=LOWER(?)", (uname_clean,))
                    if matched:
                        user_rec = matched[0]
                        is_ok, needs_upg = verify_password(p_login, user_rec["password_hash"])
                        if is_ok:
                            if needs_upg:
                                new_h = hash_password(p_login)
                                run("UPDATE users SET password_hash=? WHERE id=?", (new_h, user_rec["id"]))
                                user_rec["password_hash"] = new_h
                            st.session_state["auth_user"] = user_rec
                            st.rerun()
                        else:
                            st.error("Invalid username or password. Please try again.")
                    else:
                        st.error("Invalid username or password. Please try again.")
                else:
                    st.warning("Please enter both username and password.")

            st.caption("Default Control Room Credentials: Username `admin` • Password `admin123`")

        with tab_signup:
            with st.form("signup_form", clear_on_submit=True):
                s_fullname = st.text_input("Officer Full Name", placeholder="e.g., Capt. Tariq Mahmood")
                s_username = st.text_input("Choose Username", placeholder="e.g., tariq_nha (letters, numbers, _, .)")
                c_dept, c_role = st.columns(2)
                s_dept = c_dept.selectbox("Department / Wing", ["PDMA Balochistan", "National Highway Authority (NHA)", "Balochistan Levies Force", "Highway Police", "District Administration"])
                s_role = c_role.selectbox("Designation / Role", ["Control Room Operator", "Checkpoint Supervisor", "Regional Coordinator", "Command Officer"])
                c_p1, c_p2 = st.columns(2)
                s_pass1 = c_p1.text_input("Create Password", type="password", placeholder="Min 6 characters")
                s_pass2 = c_p2.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                btn_signup = st.form_submit_button("Create Official Account", use_container_width=True)

            if btn_signup:
                fn = s_fullname.strip()
                un = s_username.strip()
                if not (fn and un and s_pass1):
                    st.error("Please fill all required fields.")
                elif not is_valid_username(un):
                    st.error("Username must be 3–30 characters using only letters, numbers, '_', '.', or '-'.")
                elif len(s_pass1) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif s_pass1 != s_pass2:
                    st.error("Passwords do not match.")
                else:
                    exists = rows("SELECT id FROM users WHERE LOWER(username)=LOWER(?)", (un,))
                    if exists:
                        st.error("This username is already taken. Choose another username.")
                    else:
                        try:
                            new_uid = run(
                                "INSERT INTO users(full_name,username,department,role,password_hash,created_at) VALUES(?,?,?,?,?,?)",
                                (fn, un, s_dept, s_role, hash_password(s_pass1), datetime.now().strftime("%Y-%m-%d %H:%M"))
                            )
                            created_user = rows("SELECT * FROM users WHERE id=?", (new_uid,))[0]
                            st.session_state["auth_user"] = created_user
                            st.success("Account created! Entering Command Center...")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("This username is already registered.")

    st.stop()

# ==============================================================================
# AUTHENTICATED COMMAND CENTER APPLICATION
# ==============================================================================
current_user = st.session_state["auth_user"]
road_rows_all = rows("SELECT * FROM road_status")
road_lookup = {(r["route"], r["area"]): r for r in road_rows_all}

with st.sidebar:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;padding:6px 0 14px 0;">
      {logo_svg(48)}
      <div>
        <div style="font-weight:800;font-size:15px;color:#f8fafc;letter-spacing:0.3px;">HIGHWAY WATCH</div>
        <div style="font-size:10px;color:#2dd4bf;font-weight:700;letter-spacing:1.1px;">GOVT. OF BALOCHISTAN</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#081322;border:1px solid rgba(45,212,191,0.3);border-radius:12px;padding:10px 12px;margin-bottom:14px;">
      <div style="font-size:10px;color:#2dd4bf;font-weight:700;letter-spacing:0.8px;">SIGNED IN OPERATOR</div>
      <div style="font-size:13px;font-weight:800;color:#f8fafc;margin-top:2px;">{current_user['full_name']}</div>
      <div style="font-size:11px;color:#94a3b8;">{current_user['role']} • {current_user['department']}</div>
    </div>
    """, unsafe_allow_html=True)

    nav_choice = st.radio(
        "OPERATIONS MENU",
        [
            "Command Dashboard",
            "Highway Live Map",
            "Driver Management & QR",
            "Multilingual Alert Center",
            "Road Clearance Control",
            "Alert History & Logs"
        ],
        label_visibility="visible"
    )

    st.markdown("---")
    selected_corridor = st.selectbox("Active Highway Corridor", ROUTES, index=0)

    if st.button("Sync Live Weather Feed", use_container_width=True):
        fetch_weather.clear()
        st.rerun()

    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state["auth_user"] = None
        st.rerun()

    st.markdown("""
    <div style="margin-top:14px;padding:12px;background:#081322;border:1px solid rgba(56,189,248,0.18);border-radius:12px;font-size:11px;color:#94a3b8;">
      <div style="color:#2dd4bf;font-weight:700;margin-bottom:4px;">SYSTEM TELEMETRY</div>
      <div>• Feed: Open-Meteo Real-Time</div>
      <div>• Zone: Asia/Karachi (PKT)</div>
      <div>• Alerts: Urdu / Pashto / Balochi</div>
    </div>
    """, unsafe_allow_html=True)

now_str = datetime.now().strftime("%d %b %Y • %H:%M PKT")
st.markdown(f"""
<div class="cmd-topbar">
  <div style="display:flex;align-items:center;gap:14px;">
    {logo_svg(44)}
    <div>
      <div class="cmd-title">Balochistan Smart Highway & Weather Intelligence</div>
      <div class="cmd-sub">Provincial Disaster & Highway Operations Center • Operator: {current_user['full_name']}</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:14px;">
    <span style="font-size:12px;color:#94a3b8;font-family:'JetBrains Mono',monospace;">{now_str}</span>
    <span class="live-badge"><span class="live-dot"></span> LIVE TELEMETRY</span>
  </div>
</div>
""", unsafe_allow_html=True)

def get_corridor_weather(route_name):
    cache = {}
    full_payloads = {}
    failed_points = []
    for pt in ROUTES_DATA[route_name]["points"]:
        try:
            res = fetch_weather(pt["lat"], pt["lon"])
            cache[pt["name"]] = res.get("current", {})
            full_payloads[pt["name"]] = res
        except Exception:
            cache[pt["name"]] = {}
            failed_points.append(pt["name"])
    return cache, full_payloads, failed_points

# 1. COMMAND DASHBOARD
if nav_choice == "Command Dashboard":
    drivers = rows("SELECT * FROM drivers")
    checkpoints = rows("SELECT * FROM checkpoints")
    alerts_log = rows("SELECT * FROM alerts ORDER BY id DESC")
    restricted_count = sum(1 for r in road_rows_all if "Closed" in r["status"] or "Restricted" in r["status"])

    w_cache, w_full, failed_pts = get_corridor_weather(selected_corridor)
    if failed_pts:
        st.caption(f"⚠️ Live weather feed temporarily unavailable for: {', '.join(failed_pts)} — showing fallback telemetry.")

    hub_point = ROUTES_DATA[selected_corridor]["points"][-1]["name"]
    hub_cur = w_cache.get(hub_point, {})
    hub_full = w_full.get(hub_point, {})
    hub_road_obj = road_lookup.get((selected_corridor, hub_point), {})
    hub_road = hub_road_obj.get("status", "Open (Verified)")

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="stat-card"><div class="stat-label">Registered Drivers</div><div class="stat-val">{len(drivers)}</div><div class="stat-foot">Active Fleet Monitored</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="stat-card"><div class="stat-label">Active Checkpoints</div><div class="stat-val">{len(checkpoints)}</div><div class="stat-foot">QR Verification Gates</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="stat-card"><div class="stat-label">High-Risk Sectors</div><div class="stat-val" style="color:#f59e0b;">{restricted_count}</div><div class="stat-foot">Caution / Restricted Zones</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="stat-card"><div class="stat-label">Dispatched Alerts</div><div class="stat-val" style="color:#38bdf8;">{len(alerts_log)}</div><div class="stat-foot">Multilingual Warnings</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    col_main, col_right = st.columns([2.25, 1.0], gap="medium")

    with col_main:
        render_balochistan_map(
            selected_corridor,
            w_cache,
            road_lookup,
            {"highways": True, "weather_radar": True, "checkpoints": True}
        )

        wind_f = safe_float(hub_cur.get("wind_speed_10m"))
        rain_f = safe_float(hub_cur.get("precipitation"))
        press_f = safe_float(hub_cur.get("surface_pressure"))
        hum_f = safe_float(hub_cur.get("relative_humidity_2m"))

        wind_disp = f"{wind_f:.1f}" if wind_f is not None else "—"
        rain_disp = f"{rain_f:.1f}" if rain_f is not None else "—"
        press_disp = f"{int(press_f)}" if press_f is not None else "—"
        hum_disp = f"{int(hum_f)}%" if hum_f is not None else "—"

        r_score = compute_risk_score(hub_cur, hub_road, hub_road_obj.get("risk_score"))
        r_label, r_color, _ = risk_meta(r_score)

        g1, g2, g3, g4, g5 = st.columns(5)
        gauges = [
            (g1, "WIND SPEED", wind_disp, "km/h", "#38bdf8", min(int((wind_f or 0) * 2), 100)),
            (g2, "RAINFALL", rain_disp, "mm/hr", "#14b8a6", min(int((rain_f or 0) * 15), 100)),
            (g3, "PRESSURE", press_disp, "hPa", "#818cf8", min(max(int(((press_f or 1012) - 960) * 1.1), 10), 100)),
            (g4, "HUMIDITY", hum_disp, "Relative", "#2dd4bf", min(max(int(hum_f or 0), 0), 100)),
            (g5, "ROAD RISK", f"{r_score}/10", r_label.split()[0], r_color, r_score * 10),
        ]
        for col_obj, title, val, sub, color, pct in gauges:
            col_obj.markdown(f"""
            <div class="gauge-box">
              <div class="gauge-title">{title}</div>
              <div class="gauge-ring" style="background: radial-gradient(closest-side, #0b1829 76%, transparent 80% 100%), conic-gradient({color} {pct}%, #172a45 0);">{val}</div>
              <div class="gauge-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_right:
        temp_f = safe_float(hub_cur.get("temperature_2m"))
        feels_f = safe_float(hub_cur.get("apparent_temperature"))
        temp_now = f"{temp_f:.1f}°C" if temp_f is not None else "—"
        feels_now = f"{feels_f:.1f}°C" if feels_f is not None else "—"
        has_w_code = hub_cur is not None and hub_cur.get("weather_code") is not None
        w_en, w_ur, w_icon, _ = weather_info(hub_cur.get("weather_code")) if has_w_code else ("Live Feed Pending", "موسمی معلومات", "🛰️", 2)

        st.markdown(f"""
        <div class="side-panel-card">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:11px;font-weight:700;color:#2dd4bf;letter-spacing:0.8px;">CURRENT CONDITIONS • {hub_point.upper()}</span>
            <span style="font-size:22px;">{w_icon}</span>
          </div>
          <div style="display:flex;align-items:baseline;gap:12px;margin:8px 0;">
            <span style="font-size:38px;font-weight:800;font-family:'JetBrains Mono',monospace;">{temp_now}</span>
            <div>
              <div style="font-size:13px;font-weight:700;color:#f1f5f9;">{w_en} ({w_ur})</div>
              <div style="font-size:11px;color:#94a3b8;">Feels like {feels_now}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        hourly = hub_full.get("hourly", {})
        if hourly and "time" in hourly and "temperature_2m" in hourly:
            n_pts = min(10, len(hourly["time"]), len(hourly["temperature_2m"]))
            rain_prob = hourly.get("precipitation_probability", [0] * n_pts)[:n_pts]
            if n_pts > 0:
                df_hr = pd.DataFrame({
                    "Hour": [str(t).split("T")[-1][:5] for t in hourly["time"][:n_pts]],
                    "Temp (°C)": hourly["temperature_2m"][:n_pts],
                    "Rain %": rain_prob
                }).set_index("Hour")
                st.caption(f"Hourly Forecast • {hub_point}")
                st.line_chart(df_hr, height=145)

        st.markdown('<div style="font-size:12px;font-weight:800;letter-spacing:0.8px;color:#f8fafc;margin:8px 0;">ACTIVE ROUTE NOTIFICATIONS</div>', unsafe_allow_html=True)
        for pt in ROUTES_DATA[selected_corridor]["points"]:
            st_obj = road_lookup.get((selected_corridor, pt["name"]), {})
            status_txt = st_obj.get("status", "Open (Verified)")
            note_txt = st_obj.get("authority_note", "Route monitored.")
            cls = "danger" if "Closed" in status_txt else ("safe" if "Open" in status_txt else "")
            st.markdown(f"""
            <div class="notif-item {cls}">
              <div style="display:flex;justify-content:space-between;font-size:11px;font-weight:700;">
                <span style="color:#f8fafc;">{pt['name']} ({pt['elevation']})</span>
                <span style="color:#2dd4bf;">{status_txt}</span>
              </div>
              <div style="font-size:11px;color:#94a3b8;margin-top:3px;">{note_txt}</div>
            </div>
            """, unsafe_allow_html=True)

# 2. HIGHWAY LIVE MAP
elif nav_choice == "Highway Live Map":
    st.subheader("Interactive Balochistan Highway Risk & Weather Radar")
    c_opt, c_map = st.columns([1, 3.1], gap="medium")

    with c_opt:
        st.markdown('<div class="side-panel-card"><div style="font-weight:800;font-size:14px;margin-bottom:8px;">Map Layer Controls</div>', unsafe_allow_html=True)
        map_route = st.selectbox("Focus Highway", ROUTES, index=ROUTES.index(selected_corridor))
        show_hw = st.checkbox("Highway Corridors (N-25/N-50/N-40)", value=True)
        show_radar = st.checkbox("Weather Impact Zones", value=True)
        show_cp = st.checkbox("QR Checkpoints & Elevation", value=True)
        st.markdown("</div>", unsafe_allow_html=True)

        w_cache, _, _ = get_corridor_weather(map_route)
        st.markdown("**Sector Breakdown**")
        for pt in ROUTES_DATA[map_route]["points"]:
            cur = w_cache.get(pt["name"], {})
            st_row = road_lookup.get((map_route, pt["name"]), {})
            sc = compute_risk_score(cur, st_row.get("status", "Open (Verified)"), st_row.get("risk_score"))
            _, col_h, bg_h = risk_meta(sc)
            t_val = safe_float(cur.get("temperature_2m"))
            w_val = safe_float(cur.get("wind_speed_10m"))
            t_str = f"{t_val:.1f}°C" if t_val is not None else "—"
            w_str = f"{w_val:.1f} km/h" if w_val is not None else "—"
            st.markdown(f"""
            <div style="background:{bg_h};border:1px solid {col_h};border-radius:10px;padding:8px 10px;margin-bottom:7px;">
              <div style="display:flex;justify-content:space-between;font-weight:700;font-size:12px;">
                <span>{pt['name']}</span>
                <span style="color:{col_h};">{sc}/10</span>
              </div>
              <div style="font-size:11px;color:#cbd5e1;">Temp: {t_str} • Wind: {w_str}</div>
            </div>
            """, unsafe_allow_html=True)

    with c_map:
        render_balochistan_map(
            map_route,
            w_cache,
            road_lookup,
            {"highways": show_hw, "weather_radar": show_radar, "checkpoints": show_cp}
        )

# 3. DRIVER MANAGEMENT & QR CHECKPOINTS
elif nav_choice == "Driver Management & QR":
    drivers = rows("SELECT * FROM drivers ORDER BY id DESC")
    checkpoints = rows("SELECT * FROM checkpoints ORDER BY id ASC")

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f'<div class="stat-card"><div class="stat-label">Total Fleet</div><div class="stat-val">{len(drivers)}</div><div class="stat-foot">Registered Vehicles</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="stat-card"><div class="stat-label">Active on Highway</div><div class="stat-val" style="color:#10b981;">{sum(1 for d in drivers if "Active" in (d.get("status") or ""))}</div><div class="stat-foot">Live Route Tracking</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="stat-card"><div class="stat-label">QR Gate Passes</div><div class="stat-val" style="color:#38bdf8;">{len(drivers)}</div><div class="stat-foot">Digital ID Issued</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="stat-card"><div class="stat-label">Total QR Scans</div><div class="stat-val" style="color:#f59e0b;">{sum(int(c.get("qr_scans") or 0) for c in checkpoints)}</div><div class="stat-foot">Across {len(checkpoints)} Gates</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    col_reg, col_qr = st.columns([1.4, 1.0], gap="large")

    with col_reg:
        st.subheader("Register New Driver & Vehicle")
        with st.form("driver_reg_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d_name = c1.text_input("Driver Full Name", placeholder="e.g., Muhammad Aslam")
            d_phone = c2.text_input("Mobile Number (SMS/Voice)", placeholder="0300-XXXXXXX")
            c3, c4 = st.columns(2)
            d_veh = c3.text_input("Vehicle Plate No.", placeholder="QTA-9081")
            d_vtype = c4.selectbox("Vehicle Category", ["Passenger Coach", "Cargo Truck", "Oil Tanker", "Ambulance / Emergency", "Private SUV / Car"])
            c5, c6 = st.columns(2)
            d_route = c5.selectbox("Assigned Highway Corridor", ROUTES)
            d_lang = c6.selectbox("Preferred Alert Language", LANGUAGES)
            submitted = st.form_submit_button("Register & Issue Digital QR Pass", use_container_width=True)

        if submitted:
            fn_d = d_name.strip()
            ph_d = d_phone.strip()
            vh_d = re.sub(r"\s+", "", d_veh.strip().upper())
            if not (fn_d and ph_d and vh_d):
                st.error("Please fill Driver Name, Mobile Number, and Vehicle Plate.")
            elif not is_valid_pk_phone(ph_d):
                st.error("Please enter a valid Pakistani mobile number (e.g., 0300-1234567 or 03001234567).")
            elif not is_valid_plate(vh_d):
                st.error("Please enter a valid vehicle plate number (e.g., QTA-9081).")
            else:
                d_code = generate_unique_driver_code()
                run(
                    "INSERT INTO drivers(driver_code,name,phone,vehicle,vehicle_type,route,language,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (d_code, fn_d, ph_d, vh_d, d_vtype, d_route, d_lang, "Active on Route", datetime.now().strftime("%Y-%m-%d %H:%M"))
                )
                st.success(f"Driver registered with Digital Checkpoint ID: {d_code}")
                st.rerun()

    with col_qr:
        st.subheader("Checkpoint QR Pass Preview")
        if drivers:
            label_to_driver = {f"{d.get('driver_code') or 'BHW-' + str(d['id'])} • {d['name']} ({d['vehicle']})": d for d in drivers}
            sel_driver_label = st.selectbox("Select Driver for QR Gate Pass", list(label_to_driver.keys()))
            sel_d = label_to_driver[sel_driver_label]
            code_disp = sel_d.get("driver_code") or f"BHW-{sel_d['id']}"
            qr_payload = urllib.parse.quote(f"BHW-PASS|{code_disp}|{sel_d['name']}|{sel_d['vehicle']}|{sel_d['route']}")
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=170x170&data={qr_payload}&bgcolor=0b1829&color=2dd4bf"

            cp_options = [c for c in checkpoints if c["route"] == sel_d["route"]] or checkpoints
            cp_map = {f"{c['code']} • {c['name']}": c for c in cp_options}
            chosen_cp_label = st.selectbox("Target Checkpoint Gate", list(cp_map.keys()))
            chosen_cp = cp_map[chosen_cp_label]

            st.markdown(f"""
            <div class="side-panel-card" style="text-align:center;">
              <div style="font-size:11px;color:#2dd4bf;font-weight:700;letter-spacing:1px;">BALOCHISTAN HIGHWAY AUTHORITY</div>
              <div style="font-size:17px;font-weight:800;margin:4px 0;">{sel_d['name']}</div>
              <div style="font-size:12px;color:#94a3b8;margin-bottom:10px;">{sel_d['vehicle']} • {sel_d.get('vehicle_type','Transport')}</div>
              <img src="{qr_url}" alt="QR Code Pass" style="border-radius:12px;border:2px solid #14b8a6;padding:6px;background:#0b1829;"/>
              <div style="font-family:'JetBrains Mono',monospace;font-size:13px;color:#38bdf8;margin-top:8px;">ID: {code_disp}</div>
              <div style="font-size:11px;color:#94a3b8;">Corridor: {sel_d['route']} | Lang: {sel_d['language']}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Simulate Checkpoint QR Scan", use_container_width=True):
                run("UPDATE checkpoints SET qr_scans = COALESCE(qr_scans, 0) + 1 WHERE id = ?", (chosen_cp["id"],))
                run("UPDATE drivers SET status = 'Verified at Gate' WHERE id = ?", (sel_d["id"],))
                st.success(f"Verified {sel_d['name']} at {chosen_cp['name']}!")
                st.rerun()

    st.markdown("### Registered Fleet Directory")
    if drivers:
        df_drv = pd.DataFrame(drivers)[["driver_code", "name", "phone", "vehicle", "vehicle_type", "route", "language", "status", "created_at"]]
        df_drv.columns = ["Pass ID", "Driver Name", "Phone", "Vehicle", "Type", "Corridor", "Language", "Status", "Registered"]
        st.dataframe(df_drv, use_container_width=True, hide_index=True)

# 4. MULTILINGUAL ALERT CENTER
elif nav_choice == "Multilingual Alert Center":
    st.subheader("Multilingual Emergency & Weather Alert Dispatch")
    drivers = rows("SELECT * FROM drivers ORDER BY id DESC")

    c_left, c_right = st.columns([1.2, 1.3], gap="large")
    with c_left:
        target_mode = st.radio("Target Audience", ["All Drivers on Corridor", "Individual Registered Driver"], horizontal=True)
        al_route = st.selectbox("Highway Corridor", ROUTES, index=ROUTES.index(selected_corridor))
        al_area = st.selectbox("Checkpoint / Sector", [p["name"] for p in ROUTES_DATA[al_route]["points"]])
        al_lang = st.selectbox("Broadcast Language", LANGUAGES)
        al_channel = st.multiselect("Dispatch Channels", ["SMS Gateway", "Automated Voice Call (IVR)", "Checkpoint Siren / Display"], default=["SMS Gateway", "Automated Voice Call (IVR)"])

        sel_driver_id = None
        if target_mode == "Individual Registered Driver":
            if drivers:
                d_opts = {f"{d.get('driver_code') or 'BHW-' + str(d['id'])} • {d['name']} ({d['phone']})": d for d in drivers}
                chosen_d = d_opts[st.selectbox("Select Driver", list(d_opts.keys()))]
                sel_driver_id = chosen_d["id"]
            else:
                st.warning("No registered drivers found. Register a driver first or switch to Corridor Broadcast.")

    with c_right:
        w_cache, _, _ = get_corridor_weather(al_route)
        cur_w = w_cache.get(al_area, {})
        has_w = cur_w is not None and cur_w.get("weather_code") is not None
        w_en, w_ur, _, _ = weather_info(cur_w.get("weather_code")) if has_w else ("Current Weather", "موسمی صورتحال", "", 2)
        road_st = road_lookup.get((al_route, al_area), {}).get("status", "Open (Verified)")

        msg_body, travel_guidance = generate_multilingual_alert(al_area, al_route, w_en, w_ur, road_st, al_lang)
        edited_msg = st.text_area(f"{al_lang} Alert Message Preview", value=msg_body, height=115)

        st.markdown(f'<div class="urdu-box">{edited_msg}</div>', unsafe_allow_html=True)
        st.info(f"**Suggested Travel Guidance:** {travel_guidance}")

        safe_speech_text = json.dumps(edited_msg).replace("</", "<\\/")
        speech_lang_code = "ur-PK" if al_lang == "Urdu" else ("ps-AF" if al_lang == "Pashto" else "ur-PK")
        components.html(f"""
        <div style="display:flex;align-items:center;gap:10px;margin:6px 0;">
          <button onclick="playAlertVoice()" style="background:#0ea5e9;color:#fff;border:none;padding:9px 16px;border-radius:8px;font-weight:700;cursor:pointer;font-family:Inter,sans-serif;">
            🔊 Play Voice Call Preview ({al_lang})
          </button>
          <button onclick="window.speechSynthesis.cancel()" style="background:#1e293b;color:#cbd5e1;border:1px solid #334155;padding:9px 14px;border-radius:8px;font-weight:600;cursor:pointer;font-family:Inter,sans-serif;">
            ⏹ Stop
          </button>
          <span id="vstat" style="font-size:12px;color:#94a3b8;font-family:Inter,sans-serif;">Ready for audio synthesis</span>
        </div>
        <script>
          function playAlertVoice() {{
            if (!('speechSynthesis' in window)) {{
              document.getElementById('vstat').innerText = 'Speech synthesis not supported in this browser.';
              return;
            }}
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance({safe_speech_text});
            utter.lang = '{speech_lang_code}';
            utter.rate = 0.92;
            utter.onstart = () => document.getElementById('vstat').innerText = 'Broadcasting voice preview...';
            utter.onend = () => document.getElementById('vstat').innerText = 'Playback complete.';
            window.speechSynthesis.speak(utter);
          }}
        </script>
        """, height=52)

        if st.button("Dispatch Official Alert Now", use_container_width=True):
            if not edited_msg.strip():
                st.error("Alert message cannot be empty.")
            elif target_mode == "Individual Registered Driver" and sel_driver_id is None:
                st.error("Please select a valid individual driver before dispatching.")
            else:
                ch_str = ", ".join(al_channel) if al_channel else "SMS Gateway"
                sev = "Emergency" if "Closed" in road_st else ("Warning" if "Restricted" in road_st else "Advisory")
                run(
                    "INSERT INTO alerts(driver_id,route,language,severity,message,channel,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (sel_driver_id, al_route, al_lang, sev, edited_msg.strip(), ch_str, "Dispatched & Logged", datetime.now().strftime("%Y-%m-%d %H:%M"))
                )
                st.success(f"Alert dispatched via {ch_str} and recorded in provincial log.")

# 5. ROAD CLEARANCE CONTROL
elif nav_choice == "Road Clearance Control":
    st.subheader("Official Road Closure & Reopening Verification")
    all_roads = rows("SELECT * FROM road_status ORDER BY route, id")
    seg_map = {f"{r['route']}  |  {r['area']}  ({r['status']})": r for r in all_roads}

    c1, c2 = st.columns([1.1, 1.5], gap="large")
    with c1:
        if seg_map:
            chosen_seg_key = st.selectbox("Select Highway Segment", list(seg_map.keys()))
            seg = seg_map[chosen_seg_key]
            with st.form("clearance_form"):
                new_st = st.selectbox("Official Road Status", ROAD_STATUSES, index=ROAD_STATUSES.index(seg["status"]) if seg["status"] in ROAD_STATUSES else 0)
                new_risk = st.slider("Operator Risk Override (1 = Safe, 10 = Extreme)", 1, 10, int(seg.get("risk_score") or 3))
                new_officer = st.text_input("Verifying Authority / Officer", value=seg.get("verified_by") or current_user["full_name"])
                new_note = st.text_area("Official Directive / Reason", value=seg.get("authority_note") or "", height=90)
                if st.form_submit_button("Verify & Publish Status", use_container_width=True):
                    if not new_officer.strip() or not new_note.strip():
                        st.error("Verifying authority and official directive cannot be empty.")
                    else:
                        run(
                            "UPDATE road_status SET status=?, risk_score=?, verified_by=?, authority_note=?, updated_at=? WHERE id=?",
                            (new_st, new_risk, new_officer.strip(), new_note.strip(), datetime.now().strftime("%Y-%m-%d %H:%M"), seg["id"])
                        )
                        st.success("Road clearance status updated across live map and alert center.")
                        st.rerun()

    with c2:
        st.markdown("**Provincial Highway Clearance Matrix**")
        if all_roads:
            df_roads = pd.DataFrame(all_roads)[["route", "area", "status", "risk_score", "verified_by", "updated_at"]]
            df_roads.columns = ["Corridor", "Sector", "Clearance Status", "Risk Index", "Verified By", "Last Updated"]
            st.dataframe(df_roads, use_container_width=True, hide_index=True, height=420)

# 6. ALERT HISTORY & LOGS
elif nav_choice == "Alert History & Logs":
    st.subheader("Provincial Alert Dispatch & Audit History")
    logs = rows("""
        SELECT alerts.id, alerts.created_at, alerts.route, alerts.language, alerts.severity,
               COALESCE(drivers.name, 'Corridor Broadcast') AS recipient,
               alerts.channel, alerts.status, alerts.message
        FROM alerts
        LEFT JOIN drivers ON drivers.id = alerts.driver_id
        ORDER BY alerts.id DESC
    """)
    if logs:
        df_logs = pd.DataFrame(logs)
        df_logs.columns = ["ID", "Timestamp", "Corridor", "Language", "Severity", "Recipient", "Channels", "Delivery Status", "Message"]
        st.dataframe(df_logs, use_container_width=True, hide_index=True)
    else:
        st.info("No alerts dispatched yet. Use the Multilingual Alert Center to send your first warning.")
