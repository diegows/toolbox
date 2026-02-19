#!/usr/bin/env python3
"""Download temperature records (max and min) from the AEMET OpenData API.

Fetches daily maximum and minimum temperature data from AEMET OpenData for a
given weather station and date range. Can also compute frequency tables
to count how many days fall within specified temperature ranges.

Requires the AEMET_API_KEY environment variable to be set (get one at
https://opendata.aemet.es/centrodedescargas/altaUsuario).

Usage examples:

  # List all available stations (find your IDEMA code)
  aemet-temps.py --list-stations
  aemet-temps.py --list-stations | grep -i madrid

  # Fetch temps for a station and date range (table output)
  aemet-temps.py -s 3129 --start 2024-01-01 --end 2024-01-31

  # Same, but CSV output (pipe-friendly, errors go to stderr)
  aemet-temps.py -s 3129 --start 2024-01-01 --end 2024-03-31 --csv > temps.csv

  # Frequency table from a previously saved CSV
  aemet-temps.py -i temps.csv --freq "30-35,35-40,40-50"

  # Frequency table filtered to a specific date range
  aemet-temps.py -i temps.csv --freq "28-32,33-35,36-40" \\
      --freq-start 2024-06-01 --freq-end 2024-09-30

  # Frequency table as CSV
  aemet-temps.py -i temps.csv --freq "30-35,35-40,40-50" --csv

CLI reference:

  --station, -s STATION   IDEMA station code (e.g. 3129, B228)
  --start YYYY-MM-DD      Start date for data retrieval
  --end YYYY-MM-DD        End date for data retrieval
  --list-stations         List all AEMET stations and exit
  --csv                   Output CSV instead of a formatted table
  --input, -i FILE        Read from a CSV file (date,max,min) instead of AEMET
  --freq RANGES           Compute frequency table for temperature ranges
                          given as comma-separated lo-hi pairs, e.g.
                          '30-35,35-40,40-50'. Ranges are [lo, hi).
  --freq-field FIELD      Which field to use for frequency table: max or min
                          (default: max)
  --freq-start YYYY-MM-DD Filter data from this date before computing freq
  --freq-end YYYY-MM-DD   Filter data up to this date before computing freq

Notes:
  - AEMET limits queries to ~31 days. Longer ranges are automatically split
    into 30-day chunks with delays to respect the 50 req/min rate limit.
  - Temperatures use comma as decimal separator in the API; converted here.
  - Errors and progress messages go to stderr; data goes to stdout.
"""

import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

BASE_URL = "https://opendata.aemet.es/opendata"


def warn(msg):
    print(msg, file=sys.stderr)


def _urlopen_with_retry(req, max_attempts=5):
    """urlopen with retry on rate limits and transient errors (timeouts, connection resets)."""
    for attempt in range(max_attempts):
        try:
            return urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_attempts - 1:
                wait = 30 * (attempt + 1)
                warn(f"Rate limited, waiting {wait}s (attempt {attempt + 1}/{max_attempts})...")
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < max_attempts - 1:
                wait = 10 * (attempt + 1)
                warn(f"Connection error: {e} — retrying in {wait}s (attempt {attempt + 1}/{max_attempts})...")
                time.sleep(wait)
                continue
            raise


def aemet_request(path):
    """Two-step AEMET request: first call gets a datos URL, second fetches data."""
    api_key = os.environ.get("AEMET_API_KEY")
    if not api_key:
        warn("Error: AEMET_API_KEY environment variable not set")
        sys.exit(1)

    sep = "&" if "?" in path else "?"
    url = f"{BASE_URL}{path}{sep}api_key={api_key}"

    req = urllib.request.Request(url)
    try:
        with _urlopen_with_retry(req) as resp:
            meta = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        warn(f"Error: HTTP {e.code} on {url}")
        body = e.read().decode("utf-8", errors="replace")
        warn(body)
        sys.exit(1)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        warn(f"Error: {e} on {url}")
        sys.exit(1)

    datos_url = meta.get("datos")
    if not datos_url:
        desc = meta.get("descripcion", meta.get("estado", "unknown error"))
        warn(f"Error: no data URL in response — {desc}")
        return None

    req2 = urllib.request.Request(datos_url)
    try:
        with _urlopen_with_retry(req2) as resp:
            raw = resp.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
        warn(f"Error fetching data from {datos_url}: {e}")
        return None

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    return json.loads(text)


def list_stations():
    """List all available AEMET stations."""
    data = aemet_request("/api/valores/climatologicos/inventarioestaciones/todasestaciones")
    if not data:
        warn("Error: could not retrieve station list")
        sys.exit(1)

    print(f"{'IDEMA':<10} {'Name':<40} {'Province':<20} {'Altitude':>8}")
    print(f"{'-----':<10} {'----':<40} {'--------':<20} {'--------':>8}")
    for s in sorted(data, key=lambda x: x.get("provincia", "")):
        idema = s.get("indicativo", "")
        name = s.get("nombre", "")
        prov = s.get("provincia", "")
        alt = s.get("altitud", "")
        print(f"{idema:<10} {name:<40} {prov:<20} {alt:>8}")


def parse_temp(val):
    """Parse AEMET temperature value (comma as decimal separator)."""
    if not val:
        return None
    try:
        return float(val.replace(",", "."))
    except ValueError:
        return None


def date_chunks(start, end, days=30):
    """Split a date range into chunks of at most `days` days."""
    chunks = []
    cur = start
    while cur <= end:
        chunk_end = min(cur + timedelta(days=days - 1), end)
        chunks.append((cur, chunk_end))
        cur = chunk_end + timedelta(days=1)
    return chunks


def fetch_temps(station, start, end):
    """Fetch daily Tmax and Tmin for a station over a date range, chunking if needed."""
    fmt = "%Y-%m-%dT00:00:00UTC"
    chunks = date_chunks(start, end)
    all_records = []

    for i, (c_start, c_end) in enumerate(chunks):
        if i > 0:
            time.sleep(5)
        s = c_start.strftime(fmt)
        e = c_end.strftime(fmt)
        path = f"/api/valores/climatologicos/diarios/datos/fechaini/{s}/fechafin/{e}/estacion/{station}"
        warn(f"Fetching {c_start.date()} to {c_end.date()} ...")
        data = aemet_request(path)
        if data:
            all_records.extend(data)
        else:
            warn(f"Warning: no data for chunk {c_start.date()} to {c_end.date()}")

    results = []
    for rec in all_records:
        fecha = rec.get("fecha", "")
        tmax = parse_temp(rec.get("tmax"))
        tmin = parse_temp(rec.get("tmin"))
        if tmax is not None or tmin is not None:
            results.append((fecha, tmax, tmin))

    results.sort(key=lambda x: x[0])
    return results


def parse_ranges(spec):
    """Parse a range spec like '30-35,35-40,40-50' into a list of (lo, hi) tuples."""
    ranges = []
    for part in spec.split(","):
        lo, hi = part.strip().split("-", 1)
        ranges.append((float(lo), float(hi)))
    return ranges


def read_csv_input(path):
    """Read a CSV file with date,max,min columns and return list of (date, max, min)."""
    results = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fecha = row.get("date", "")
            try:
                tmax = float(row["max"]) if row.get("max") else None
            except (ValueError, KeyError):
                tmax = None
            try:
                tmin = float(row["min"]) if row.get("min") else None
            except (ValueError, KeyError):
                tmin = None
            if tmax is not None or tmin is not None:
                results.append((fecha, tmax, tmin))
    return results


def frequency_table(values, ranges):
    """Count how many values fall in each range [lo, hi)."""
    counts = {(lo, hi): 0 for lo, hi in ranges}
    for v in values:
        for lo, hi in ranges:
            if lo <= v < hi:
                counts[(lo, hi)] += 1
                break
    return counts


def main():
    parser = argparse.ArgumentParser(description="Download temperature records (max/min) from AEMET OpenData")
    parser.add_argument("--station", "-s", help="IDEMA station code (e.g. 3129, B228)")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--list-stations", action="store_true", help="List all stations and exit")
    parser.add_argument("--csv", action="store_true", help="Output CSV instead of table")
    parser.add_argument("--input", "-i", help="Read data from a CSV file instead of fetching from AEMET")
    parser.add_argument("--freq", help="Compute frequency table for given ranges (e.g. '30-35,35-40,40-50')")
    parser.add_argument("--freq-field", choices=["max", "min"], default="max",
                        help="Which field to use for frequency table (default: max)")
    parser.add_argument("--freq-start", help="Filter data from this date before computing frequency (YYYY-MM-DD)")
    parser.add_argument("--freq-end", help="Filter data up to this date before computing frequency (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.list_stations:
        list_stations()
        return

    if args.input:
        results = read_csv_input(args.input)
        if not results:
            warn(f"No data found in {args.input}")
            sys.exit(1)
    else:
        if not args.station or not args.start or not args.end:
            parser.error("--station, --start, and --end are required (unless using --list-stations or --input)")

        try:
            start = datetime.strptime(args.start, "%Y-%m-%d")
            end = datetime.strptime(args.end, "%Y-%m-%d")
        except ValueError:
            parser.error("Dates must be in YYYY-MM-DD format")

        if start > end:
            parser.error("--start must be before --end")

        results = fetch_temps(args.station, start, end)

        if not results:
            warn("No data found for the given station and date range.")
            sys.exit(1)

    if args.freq:
        filtered = results
        if args.freq_start or args.freq_end:
            fs = args.freq_start or "0000-00-00"
            fe = args.freq_end or "9999-99-99"
            filtered = [(d, tmax, tmin) for d, tmax, tmin in results if fs <= d <= fe]
            if not filtered:
                warn("No data in the specified --freq-start/--freq-end range.")
                sys.exit(1)

        ranges = parse_ranges(args.freq)
        if args.freq_field == "min":
            values = [tmin for _, _, tmin in filtered if tmin is not None]
        else:
            values = [tmax for _, tmax, _ in filtered if tmax is not None]
        counts = frequency_table(values, ranges)

        period_start = filtered[0][0]
        period_end = filtered[-1][0]

        if args.csv:
            print("range_start,range_end,days")
            for lo, hi in ranges:
                print(f"{lo:g},{hi:g},{counts[(lo, hi)]}")
        else:
            print(f"Period:  {period_start} to {period_end} ({len(filtered)} days)")
            print(f"Field:   {args.freq_field}")
            print()
            print(f"{'Range (C)':<16}{'Days':>6}")
            print(f"{'----------':<16}{'-----':>6}")
            for lo, hi in ranges:
                label = f"{lo:g}-{hi:g}"
                print(f"{label:<16}{counts[(lo, hi)]:>6}")
            print(f"{'Total':<16}{sum(counts.values()):>6}")
        return

    if args.csv:
        print("date,max,min")
        for fecha, tmax, tmin in results:
            tmax_s = f"{tmax}" if tmax is not None else ""
            tmin_s = f"{tmin}" if tmin is not None else ""
            print(f"{fecha},{tmax_s},{tmin_s}")
    else:
        print(f"Station: {args.station}")
        print(f"Period:  {args.start} to {args.end}")
        print()
        print(f"{'Date':<16}{'Max (C)':>8}{'Min (C)':>8}")
        print(f"{'----------':<16}{'-------':>8}{'-------':>8}")
        for fecha, tmax, tmin in results:
            tmax_s = f"{tmax:>8.1f}" if tmax is not None else f"{'—':>8}"
            tmin_s = f"{tmin:>8.1f}" if tmin is not None else f"{'—':>8}"
            print(f"{fecha:<16}{tmax_s}{tmin_s}")


if __name__ == "__main__":
    main()
