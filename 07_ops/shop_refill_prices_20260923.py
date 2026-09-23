"""Set the owner's 2026-09-23 refill prices after the new checkout is live.

Plan is read-only. Apply requires the plan fingerprint, makes a SQLite backup,
and updates only the 230 identified refill products in one transaction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PRICES_CAD = {'A': 40, 'B': 50, 'C': 45, 'D': 40, 'E': 36, 'F': 38, 'G': 32, 'H': 35, 'M': 23}
COUNTS = {'A': 27, 'B': 33, 'C': 30, 'D': 27, 'E': 25, 'F': 26, 'G': 22, 'H': 24, 'M': 16}


def selection(db):
    chosen = []
    for product_id, raw in db.execute('SELECT id,payload FROM commerce_products ORDER BY id'):
        product = json.loads(raw)
        category = product.get('shop_category_id', '')
        if category not in {f'refill-{s.lower()}' for s in PRICES_CAD}:
            continue
        series = category[-1].upper()
        code = product.get('code', '')
        full = code == f'{series} SET' and product.get('zh') == f'{series}系列全色10g'
        if not full and not (code.startswith(series) and code[1:].isdigit() and product.get('zh') == code):
            raise RuntimeError(f'Unexpected refill identity: {product_id}')
        if product.get('stock') != 999 or product.get('kind') != 'physical' or product.get('shop_collection') != 'home' or not product.get('shop_visible'):
            raise RuntimeError(f'Unexpected refill state: {product_id}')
        price = PRICES_CAD[series] * 100 if full else 200
        if product.get('price_cents') not in (None, price):
            raise RuntimeError(f'Existing price differs: {product_id}')
        chosen.append((product_id, raw, product, price, full))
    if Counter(p['shop_category_id'][-1].upper() for _, _, p, _, _ in chosen) != COUNTS:
        raise RuntimeError('Series counts changed; review the live catalog')
    if Counter(p['shop_category_id'][-1].upper() for _, _, p, _, full in chosen if full) != Counter({s: 1 for s in PRICES_CAD}):
        raise RuntimeError('Expected one full-color set per series')
    for series in PRICES_CAD:
        numbers = sorted(int(p['code'][1:]) for _, _, p, _, full in chosen if p['shop_category_id'] == f'refill-{series.lower()}' and not full)
        if numbers != list(range(1, COUNTS[series])):
            raise RuntimeError(f'Missing or duplicated numbered refill: {series}')
    return chosen


def fingerprint(chosen):
    data = [(product_id, raw) for product_id, raw, _, _, _ in chosen]
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--expect', help='selection_sha256 from a reviewed plan')
    parser.add_argument('--backup-dir', type=Path)
    args = parser.parse_args()
    if args.apply and (not args.expect or not args.backup_dir):
        parser.error('--apply requires --expect and --backup-dir')
    db = sqlite3.connect(f'file:{args.db}?mode={"rw" if args.apply else "ro"}', uri=True, timeout=30)
    try:
        chosen = selection(db)
        digest = fingerprint(chosen)
        summary = {'selection_sha256': digest, 'products': len(chosen), 'series': COUNTS,
                   'full_set_cad': PRICES_CAD, 'single_cad': 2,
                   'unpriced': sum(p['price_cents'] is None for _, _, p, _, _ in chosen),
                   'already_priced': sum(p['price_cents'] == price for _, _, p, price, _ in chosen)}
        if not args.apply:
            print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
            return
        if digest != args.expect:
            raise RuntimeError('Plan fingerprint changed; apply cancelled')
        args.backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = args.backup_dir / f'refill-before-{datetime.now(timezone.utc):%Y%m%d%H%M%S}.sqlite3'
        if backup.exists():
            raise RuntimeError('Backup filename already exists')
        with sqlite3.connect(backup) as target:
            db.backup(target)
        os.chmod(backup, 0o600)
        with sqlite3.connect(f'file:{backup}?mode=ro', uri=True) as check:
            if check.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or fingerprint(selection(check)) != digest:
                raise RuntimeError('Backup verification failed')
        db.execute('BEGIN IMMEDIATE')
        if fingerprint(selection(db)) != digest:
            db.rollback()
            raise RuntimeError('Live catalog changed since backup; apply cancelled')
        updated = 0
        for product_id, _, product, price, _ in chosen:
            if product['price_cents'] == price:
                continue
            before = product['price_cents']
            product['price_cents'] = price
            product['version'] += 1
            db.execute('UPDATE commerce_products SET payload=? WHERE id=?', (json.dumps(product, ensure_ascii=False), product_id))
            db.execute('INSERT INTO commerce_events(order_id,created_at,event,actor,detail) VALUES(?,?,?,?,?)',
                       (product_id, time.time(), 'shop_refill_price_updated', 'owner-request-20260923',
                        json.dumps({'before_cents': before, 'after_cents': price}, ensure_ascii=False)))
            updated += 1
        db.commit()
        summary.update(updated=updated, backup=str(backup), after_sha256=fingerprint(selection(db)))
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    finally:
        db.close()


if __name__ == '__main__':
    main()
