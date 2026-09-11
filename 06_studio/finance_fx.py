"""Dated CNY-to-CAD reference quotes; each cash record freezes its own quote."""
from __future__ import annotations

import json
import threading
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from fastapi import HTTPException

SOURCE = 'Bank of Canada'
_lock = threading.Lock()


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS studio_finance_fx (
      requested_on TEXT PRIMARY KEY, rate TEXT NOT NULL, rate_date TEXT NOT NULL,
      source TEXT NOT NULL, fetched_at REAL NOT NULL)''')


def cad_cents(amount, rate):
    if amount is None:
        return None
    return int((Decimal(amount) * Decimal(rate)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def fetch_quote(day):
    lower = day - timedelta(days=14)
    url = ('https://www.bankofcanada.ca/valet/observations/FXCNYCAD/json'
           f'?start_date={lower.isoformat()}&end_date={day.isoformat()}')
    request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'PinDouStudio/1.0'})
    with urlopen(request, timeout=6) as response:
        raw = response.read(262145)
    if len(raw) > 262144:
        raise ValueError('Oversized FX response')
    data = json.loads(raw)
    valid = []
    for observation in data.get('observations', []):
        try:
            observed = date.fromisoformat(observation['d'])
            rate = Decimal(observation['FXCNYCAD']['v'])
            if lower <= observed <= day and rate.is_finite() and Decimal('0') < rate < Decimal('100'):
                valid.append((observed, rate))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
    if not valid:
        raise ValueError('No dated FX observation')
    observed, rate = max(valid, key=lambda item: item[0])
    return {'rate': format(rate, 'f'), 'rate_date': observed.isoformat(), 'source': SOURCE}


def quote(database, day):
    if day > datetime.now(ZoneInfo('America/Toronto')).date():
        raise HTTPException(422, 'finance_fx_future_date')
    requested = day.isoformat()
    with _lock:
        with database() as db:
            row = db.execute('SELECT * FROM studio_finance_fx WHERE requested_on=?', (requested,)).fetchone()
        cached = dict(row) if row else None
        # Exact-day quotes are stable. A previous-business-day fallback is
        # refreshed hourly so today's later publication can be used by new entries.
        if cached and (cached['rate_date'] == requested or time.time() - cached['fetched_at'] < 3600):
            return {k: cached[k] for k in ('rate', 'rate_date', 'source')}
        try:
            value = fetch_quote(day)
        except Exception:
            if cached:
                return {k: cached[k] for k in ('rate', 'rate_date', 'source')}
            raise HTTPException(503, 'finance_rate_unavailable') from None
        with database() as db:
            db.execute('INSERT OR REPLACE INTO studio_finance_fx VALUES(?,?,?,?,?)',
                       (requested, value['rate'], value['rate_date'], value['source'], time.time()))
        return value
