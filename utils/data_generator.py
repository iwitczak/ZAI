#!/usr/bin/env python3
"""
Example data generator

Modes:
  1. Example data - Requires 3 API keys, 15 predefined temperature measurements per key
  2. Custom data  - your own input:
       a) Future mode: sends a measurement every <int> seconds from now
       b) Past mode:   sends value:time pairs from the past
  3. Real data    - downloads data from the IMGW API (Requires API key and location name)
"""

import argparse
import random
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from getpass import getpass

import requests

# ***
# CONFIGURATION
# ***
SERVER_API_URL = 'http://127.0.0.1:8000/api/'
SERVER_MEASUREMENTS_URL = SERVER_API_URL + "measurements"  # endpoint for inserting data (defaults to Django development server)
API_KEY_HEADER = "X-API-Key"                           # header carrying the API key
REQUEST_TIMEOUT = 10                                   # seconds

IMGW_SYNOP_URL = "https://danepubliczne.imgw.pl/api/data/synop"
# Fields available in IMGW synop data: temperatura, predkosc_wiatru, kierunek_wiatru, wilgotnosc_wzgledna, suma_opadu, cisnienie
IMGW_DEFAULT_FIELD = "temperatura"

# Predefined temperature measurements for example mode
SERVER_LOGIN_URL = SERVER_API_URL + 'auth/login'
SERVER_SERIES_URL = SERVER_API_URL + 'series'
SERVER_SENSOR_URL = SERVER_API_URL + 'sensors'

EXAMPLE_SERIES_VALUES = [
    [12.1, 12.4, 12.9, 13.5, 14.2, 15.0, 15.8, 16.3, 16.9, 17.2, 17.0, 16.5, 15.9, 15.1, 14.4, 14],
    [8.5, 8.7, 9.0, 9.6, 10.3, 11.1, 11.8, 12.4, 12.9, 13.1, 12.8, 12.2, 11.5, 10.7, 10.0, 10.2],
    [19.8, 20.1, 20.6, 21.2, 21.9, 22.5, 23.1, 23.4, 23.2, 22.8, 22.3, 21.7, 21.0, 20.4, 19.9, 20.0],
]
EXAMPLE_STEP_MINUTES = 10  # interval between example measurements
EXAMPLE_SERIES = [
    {"name": "example1","minValue": -40,"maxValue": 50,"color": "#1f77b4","icon": "string","unit": "°C"},
    {"name": "example2","minValue": -40,"maxValue": 50,"color": "#0ba82d","icon": "string","unit": "°C"},
    {"name": "example3","minValue": -40,"maxValue": 50,"color": "#b41f1f","icon": "string","unit": "°C"},
]
EXAMPLE_SENSORS = [
    {"name": "sensor_ex1"},
    {"name": "sensor_ex2"},
    {"name": "sensor_ex3"},
]


# ***
# Helpers
# ***
def format_timestamp(dt: datetime) -> str:
    """Timestamp format sent to the server"""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def send_measurement(api_key: str, value: float, dt: datetime, dry_run: bool = False) -> bool:
    """Sends a single measurement {value, timestamp}."""
    payload = {"value": value, "timestamp": format_timestamp(dt)}
    if dry_run:
        print(f"[DRY-RUN] key=...{api_key[-4:]} -> {payload}")
        return True
    try:
        resp = requests.post(
            SERVER_MEASUREMENTS_URL,
            json=payload,
            headers={API_KEY_HEADER: api_key},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        print(f"[OK {resp.status_code}] key=...{api_key[-4:]} -> {payload}")
        return True
    except requests.RequestException as e:
        print(f"[ERROR] key=...{api_key[-4:]} -> {payload}: {e}")
        return False


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{prompt}{suffix}: ").strip()
        if raw:
            return raw
        if default is not None:
            return default


def ask_int(prompt: str, default: int | None = None, min_value: int = 1) -> int:
    while True:
        raw = ask(prompt, str(default) if default is not None else None)
        try:
            n = int(raw)
            if n >= min_value:
                return n
        except ValueError:
            pass
        print(f"Enter an integer >= {min_value}.")


def ask_float(prompt: str, default: float | None = None) -> float:
    while True:
        raw = ask(prompt, str(default) if default is not None else None)
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            print("Enter a number.")


def parse_values(raw: str) -> list[float]:
    return [float(x.replace(",", ".")) for x in raw.replace(";", ",").split(",") if x.strip()]


def validate_range(values: list[float], v_min: float, v_max: float) -> None:
    bad = [v for v in values if not (v_min <= v <= v_max)]
    if bad:
        raise ValueError(f"Values outside the series range [{v_min}, {v_max}]: {bad}")


def normalize(text: str) -> str:
    """Lowercase, no Polish diacritics - used for comparing station names."""
    text = text.replace("ł", "l").replace("Ł", "L")
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()

def generate_random_values(count: int, v_min: float, v_max: float, max_step: float | None = None, start: float | None = None) -> list[float]:
    """Random series where each value differs from the previous one by at most max_step.
    max_step defaults to 5% of the series range; start defaults to a random value within min-max. Values reaching the range edge bounce back inside.
    """
    if max_step is None:
        max_step = (v_max - v_min) * 0.05

    value = start if start is not None else random.uniform(v_min, v_max)
    values = []
    for _ in range(count):
        values.append(round(value, 2))
        value += random.uniform(-max_step, max_step)
        # bounce off the edges instead of sticking to them
        if value > v_max:
            value = 2 * v_max - value
        elif value < v_min:
            value = 2 * v_min - value
        value = max(v_min, min(v_max, value))  # safety clamp for very large steps
    return values


# ***
# Mode 1: Example data
# ***
def mode_example(dry_run: bool) -> None:
    print("\n--- Example data: Admin login required ---")
    # 0. Admin login
    admin_login = ask('Admin login')
    admin_password = getpass()

    json = {'username': admin_login, 'password': admin_password}
    resp = requests.post(
        url=SERVER_LOGIN_URL,
        json = json,
        timeout=REQUEST_TIMEOUT
        )

    key = resp.json().get('accessToken')
    if key is None:
        print('Login error - did not receive token')
        return

    # 1. Create 3 example series
    series_ids = []
    for s in EXAMPLE_SERIES:
        resp = requests.post(
                url=SERVER_SERIES_URL,
                json = s,
                headers={'Authorization': f'Bearer {key}'},
                timeout=REQUEST_TIMEOUT
                )
        id = resp.json().get('id')
        if id is None:
            print('Error - did not receive series id')
            return
        series_ids.append(id)
        
    # 2. Create 3 example sensors and save their key
    keys = []
    for i, s in enumerate(EXAMPLE_SENSORS):
        sensor_json = s
        sensor_json["seriesId"] = series_ids[i]
        resp = requests.post(
                url=SERVER_SENSOR_URL,
                json = sensor_json,
                headers={'Authorization': f'Bearer {key}'},
                timeout=REQUEST_TIMEOUT
                )
        api_key = resp.json().get('apiKey')
        if api_key is None:
            print('Error - did not receive sensor apiKey')
            return
        keys.append(api_key)


    # 3. Input values for each sensor
    now = datetime.now(timezone.utc)
    for key, series in zip(keys, EXAMPLE_SERIES_VALUES):
        n = len(series)
        for i, value in enumerate(series):
            # oldest measurement first, the last one = now
            dt = now - timedelta(minutes=EXAMPLE_STEP_MINUTES * (n - 1 - i))
            send_measurement(key, value, dt, dry_run)


# ***
# Mode 2: Custom data
# ***
def read_values(count_hint: int | None, v_min: float, v_max: float) -> list[float]:
    """Values: either a custom list or random within min-max."""
    print("Values: 1) custom list  2) random within min-max")
    choice = ask("Choice", "2")
    if choice == "1":
        values = parse_values(ask("Enter values separated by commas"))
        validate_range(values, v_min, v_max)  # raises ValueError if out of range
        return values
    count = count_hint or ask_int("How many measurements to generate", 10)
    max_step = ask_float("Max change between consecutive values", (v_max - v_min) * 0.05)
    return generate_random_values(count, v_min, v_max, max_step)


def custom_future(api_key: str, v_min: float, v_max: float, dry_run: bool) -> None:
    interval = ask_int("Time between measurements (seconds)", 5)
    values = read_values(None, v_min, v_max)

    print(f"\nSending {len(values)} measurements every {interval} s (Ctrl+C to stop)...")
    try:
        for i, value in enumerate(values):
            send_measurement(api_key, value, datetime.now(timezone.utc), dry_run)
            if i < len(values) - 1:
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\nInterrupted.")


def read_past_times(count: int | None) -> list[datetime]:
    """Times: either a custom list (ISO) or random times from the past."""
    now = datetime.now(timezone.utc)
    print("Times: 1) custom list (e.g. 2026-10-29T14:30:00)  2) random past times")
    choice = ask("Choice", "2")
    if choice == "1":
        times = []
        for part in ask("Enter times separated by commas").split(","):
            dt = datetime.fromisoformat(part.strip().replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt > now:
                raise ValueError(f"Time {dt.isoformat()} is not in the past")
            times.append(dt)
        return times
    days = ask_int("Pick random times from the last N days", 7)
    n = count or ask_int("How many measurements", 10)
    span = days * 86400
    return sorted(now - timedelta(seconds=random.randint(60, span)) for _ in range(n))


def custom_past(api_key: str, v_min: float, v_max: float, dry_run: bool) -> None:
    values = read_values(None, v_min, v_max)
    times = read_past_times(len(values))
    if len(times) != len(values):
        raise ValueError(f"Number of values ({len(values)}) != number of times ({len(times)})")

    print(f"\nSending {len(values)} value:time pairs from the past...")
    for value, dt in zip(values, times):
        send_measurement(api_key, value, dt, dry_run)


def mode_custom(dry_run: bool) -> None:
    print("\n--- Custom data ---")
    api_key = ask("API key")
    v_min = ask_float("Series minimum (min)", -50)
    v_max = ask_float("Series maximum (max)", 50)
    if v_min >= v_max:
        raise ValueError("min must be lower than max")

    print("Time mode: 1) Future (every N seconds)  2) Past (value:time pairs from the past)")
    choice = ask("Choice", "1")
    try:
        if choice == "1":
            custom_future(api_key, v_min, v_max, dry_run)
        elif choice == "2":
            custom_past(api_key, v_min, v_max, dry_run)
        else:
            print("Unknown choice.")
    except ValueError as e:
        print(f"[VALIDATION ERROR] {e}")


# ***
# Mode 3: Real data (IMGW)
# ***
def mode_real(dry_run: bool) -> None:
    print("\n--- Real data (IMGW) ---")
    api_key = ask("API key")
    location = ask("Location name (synoptic station, e.g. Warszawa, Poznan, Zakopane)")
    field = ask("IMGW field (temperatura, predkosc_wiatru, wilgotnosc_wzgledna, "
                "suma_opadu, cisnienie)", IMGW_DEFAULT_FIELD)

    try:
        resp = requests.get(IMGW_SYNOP_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        stations = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"[ERROR] Failed to download data from IMGW: {e}")
        return

    wanted = normalize(location)
    match = next((s for s in stations if normalize(s.get("stacja", "")) == wanted), None)
    if match is None:
        match = next((s for s in stations if wanted in normalize(s.get("stacja", ""))), None)
    if match is None:
        names = ", ".join(sorted(s["stacja"] for s in stations))
        print(f"[ERROR] Station '{location}' not found.\nAvailable: {names}")
        return

    raw_value = match.get(field)
    if raw_value is None:
        print(f"[ERROR] Station {match['stacja']} has no field '{field}'. "
              f"Available: {', '.join(match.keys())}")
        return

    value = float(raw_value)
    # IMGW: data_pomiaru = YYYY-MM-DD, godzina_pomiaru = hour (Polish local time)
    try:
        from zoneinfo import ZoneInfo
        local = datetime.strptime(
            f"{match['data_pomiaru']} {int(match['godzina_pomiaru']):02d}:00", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=ZoneInfo("Europe/Warsaw"))
        dt = local.astimezone(timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)

    print(f"Station: {match['stacja']}, {field} = {value}, measured at {dt.isoformat()}")
    send_measurement(api_key, value, dt, dry_run)



def main() -> None:
    parser = argparse.ArgumentParser(description="Example data generator")
    parser.add_argument("--dry-run", action="store_true", help="don't send, only print")
    parser.add_argument("--url", help="override SERVER_URL")
    args = parser.parse_args()

    global SERVER_MEASUREMENTS_URL
    if args.url:
        SERVER_MEASUREMENTS_URL = args.url

    print("=== Example data generator ===")
    print("1) Example data (3 API keys, 15 measurements per key)")
    print("2) Custom data")
    print("3) Real data (IMGW)")
    choice = ask("Select mode", "1")

    modes = {"1": mode_example, "2": mode_custom, "3": mode_real}
    if choice not in modes:
        sys.exit("Unknown mode.")
    # try:
    modes[choice](args.dry_run)
    # except ValueError as e:
    #     sys.exit(f"[ERROR] {e}")


if __name__ == "__main__":
    main()