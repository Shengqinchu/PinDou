"""CAD shop orders paid with the host. Never call the payment gateway or wallet."""
from __future__ import annotations

import json
import time
import uuid
from typing import Annotated, Literal

from fastapi import Depends, Header, Request
from pydantic import Field, model_validator

import commerce

database = None
STATES = {'manual_pending', 'manual_confirmed', 'manual_completed', 'manual_cancelled'}


class Item(commerce.Strict):
    product_id: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,39}$')
    quantity: int = Field(ge=1, le=20, strict=True)
    variant_id: str = Field(default='', pattern=r'^(?:[a-z0-9][a-z0-9_-]{0,39})?$')
    choice_id: str = Field(default='', pattern=r'^(?:[a-z0-9][a-z0-9_-]{0,39})?$')


class Cart(commerce.Strict):
    items: list[Item] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def unique(self):
        if len({(x.product_id, x.variant_id, x.choice_id) for x in self.items}) != len(self.items):
            raise ValueError('Duplicate selections')
        return self


class Contact(commerce.Strict):
    name: str = Field(default='', max_length=80)
    contact: str = Field(default='', max_length=180)
    notes: str = Field(default='', max_length=1500)


class Checkout(Cart, Contact):
    quote_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    access_key: str = Field(pattern=r'^[a-f0-9]{64}$')
    locale: Literal['zh', 'en'] = 'zh'
    delivery_method: Literal['pickup', 'courier']
    address: str = Field(default='', max_length=500)
    website: str = Field(default='', max_length=0)

    @model_validator(mode='after')
    def required_delivery_details(self):
        if not self.name.strip() or not self.contact.strip() or not self.notes.strip():
            raise ValueError('Name, contact and order notes are required')
        if self.delivery_method == 'courier' and not self.address.strip():
            raise ValueError('Courier address is required')
        self.name = self.name.strip()
        self.contact = self.contact.strip()
        self.notes = self.notes.strip()
        self.address = self.address.strip() if self.delivery_method == 'courier' else ''
        return self


class ContactUpdate(Contact):
    version: int = Field(ge=1, strict=True)


class Update(commerce.Strict):
    status: Literal['manual_pending', 'manual_confirmed', 'manual_completed', 'manual_cancelled']
    staff_note: str = Field(default='', max_length=1500)
    version: int = Field(ge=1, strict=True)


def initialize(db_func):
    global database
    database = db_func
    with database() as db:
        db.execute('CREATE TABLE IF NOT EXISTS shop_order_settings(id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL DEFAULT 0)')
        db.execute('INSERT OR IGNORE INTO shop_order_settings VALUES(1,0)')


def ordering_enabled(db):
    # Catalog initialization can run before this module's migration.
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='shop_order_settings'").fetchone():
        return False
    row = db.execute('SELECT enabled FROM shop_order_settings WHERE id=1').fetchone()
    return bool(row and row[0])


def option_label(options, selected):
    if not options and not selected:
        return None
    option = next((x for x in options if x['id'] == selected), None)
    if not option:
        commerce.fail('shop_choose_variant', 422)
    return option


def quote_cart(db, cart):
    if not ordering_enabled(db):
        commerce.fail('shop_manual_closed')
    import shop_catalog
    catalog = {p['id']: p for p in shop_catalog.catalog_for(db)['products']}
    lines, groups = [], {}
    for item in cart.items:
        p = catalog.get(item.product_id)
        if not p or p['kind'] != 'physical' or p['price_cents'] is None or p['shop_collection'] == 'services':
            commerce.fail('shop_unpriced_or_hidden')
        variant = option_label(p.get('variants', []), item.variant_id)
        choice = option_label(p.get('choices', []), item.choice_id)
        override = variant.get('price_cents') if variant else None
        unit_cents = p['price_cents'] if override is None else override
        group = groups.setdefault(p['id'], {'product': p, 'quantity': 0, 'offer_quantity': 0, 'indexes': []})
        group['quantity'] += item.quantity
        # Independently priced sets do not count towards regular-item offers.
        if override is None:
            group['offer_quantity'] += item.quantity
            group['indexes'].append(len(lines))
        if group['quantity'] > p['available_stock']:
            commerce.fail('stock_unavailable')
        lines.append({**item.model_dump(), 'kind': 'physical', 'zh': p['zh'], 'en': p['en'],
                      'image': p['image'], 'unit_cents': unit_cents, 'total_cents': unit_cents * item.quantity,
                      'product_version': p['version'], 'variant_zh': variant['zh'] if variant else '',
                      'variant_en': variant['en'] if variant else '', 'choice_zh': choice['zh'] if choice else '',
                      'choice_en': choice['en'] if choice else '', 'discount_cents': 0})
    for group in groups.values():
        p, quantity = group['product'], group['offer_quantity']
        offer = p.get('quantity_offer')
        if not offer:
            continue
        # Mix different numbered variants of the same product. Integer cents;
        # distributing the exact group total prevents rounding or split-line loss.
        bundles, singles = divmod(quantity, offer['quantity'])
        amount = bundles * offer['price_cents'] + singles * p['price_cents']
        allocated, done = 0, 0
        for index in group['indexes']:
            line = lines[index]
            done += line['quantity']
            bundled = min(done, bundles * offer['quantity'])
            full, part = divmod(bundled, offer['quantity'])
            cumulative = full * offer['price_cents'] + part * offer['price_cents'] // offer['quantity'] + (done - bundled) * p['price_cents']
            line['total_cents'] = cumulative - allocated
            allocated = cumulative
            line['discount_cents'] = line['unit_cents'] * line['quantity'] - line['total_cents']
        assert allocated == amount
    subtotal = sum(x['unit_cents'] * x['quantity'] for x in lines)
    total = sum(x['total_cents'] for x in lines)
    if not 1 <= total <= 1000000:
        commerce.fail('order_amount_limit', 422)
    result = {'mode': 'manual', 'currency': 'CAD', 'lines': lines, 'subtotal_cents': subtotal,
              'discount_cents': subtotal - total, 'total_cents': total,
              'tax_cents': 0, 'tax_mode': 'host_arranged', 'tax_bps': 0,
              'cny_fen': 0, 'fx_cny_per_cad': ''}
    result['quote_id'] = commerce.digest(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return result


def register(app, admin_actor):
    @app.post('/studio-api/shop/cart/quote')
    def quote(payload: Cart):
        with database() as db:
            return quote_cart(db, payload)

    @app.post('/studio-api/shop/orders', status_code=201)
    def place(payload: Checkout, request: Request, idempotency_key: Annotated[str, Header()]):
        try:
            uuid.UUID(idempotency_key)
        except ValueError:
            commerce.fail('invalid_request_id', 422)
        hashed = commerce.digest(payload.model_dump_json())
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT * FROM commerce_orders WHERE idempotency_key=?', (idempotency_key,)).fetchone()
            if existing:
                commerce.authorize(existing, payload.access_key)
                if existing['payload_hash'] != hashed:
                    commerce.fail('request_changed')
                return commerce.order_view(existing)
            quoted = quote_cart(db, payload)
            if quoted['quote_id'] != payload.quote_id:
                commerce.fail('price_changed')
            client = commerce.digest('manual:' + (request.client.host if request.client else 'unknown'))
            bucket = int(time.time()) // 3600
            row = db.execute('SELECT count FROM commerce_limits WHERE client=? AND bucket=?', (client, bucket)).fetchone()
            if row and row[0] >= 20:
                commerce.fail('too_many_orders', 429)
            db.execute('DELETE FROM commerce_limits WHERE bucket<?', (bucket - 1,))
            db.execute('INSERT INTO commerce_limits VALUES(?,?,1) ON CONFLICT(client,bucket) DO UPDATE SET count=count+1', (client, bucket))
            ident = 'PS' + uuid.uuid4().hex[:24].upper()
            now = time.time()
            customer = {'name': payload.name, 'contact': payload.contact, 'contact_method': 'other',
                        'notes': payload.notes, 'locale': payload.locale,
                        'delivery_method': payload.delivery_method, 'address': payload.address}
            db.execute("""INSERT INTO commerce_orders(id,created_at,updated_at,status,access_hash,idempotency_key,payload_hash,customer,quote,expires_at,hold_until,fulfillment)
                       VALUES(?,?,?,'manual_pending',?,?,?,?,?,0,0,'awaiting_contact')""",
                       (ident, now, now, commerce.digest(payload.access_key), idempotency_key, hashed,
                        json.dumps(customer, ensure_ascii=False), json.dumps(quoted, ensure_ascii=False)))
            for item in payload.items:
                db.execute('INSERT INTO commerce_stock VALUES(?,?,?)', (ident, item.product_id, item.quantity))
            commerce.audit(db, ident, 'manual_order_submitted')
            return commerce.order_view(db.execute('SELECT * FROM commerce_orders WHERE id=?', (ident,)).fetchone())

    @app.patch('/studio-api/shop/orders/{ident}/contact')
    def contact(ident: str, payload: ContactUpdate, x_order_key: Annotated[str | None, Header()] = None):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM commerce_orders WHERE id=?', (ident,)).fetchone()
            commerce.authorize(row, x_order_key)
            if row['status'] not in STATES:
                commerce.fail('order_not_found', 404)
            if row['version'] != payload.version:
                commerce.fail('version_conflict')
            customer = json.loads(row['customer'])
            customer.update(payload.model_dump(exclude={'version'}))
            db.execute('UPDATE commerce_orders SET customer=?,updated_at=?,version=version+1 WHERE id=?',
                       (json.dumps(customer, ensure_ascii=False), time.time(), ident))
            commerce.audit(db, ident, 'manual_contact_updated', 'customer')
            return commerce.order_view(db.execute('SELECT * FROM commerce_orders WHERE id=?', (ident,)).fetchone())

    @app.get('/studio-api/manage/shop/orders')
    def listing(_actor=Depends(admin_actor), status: str = 'all', search: str = '', page: int = 1):
        if status not in STATES | {'all'} or not 1 <= page <= 10000 or len(search) > 120:
            commerce.fail('invalid_page', 422)
        clauses = ["status IN ('manual_pending','manual_confirmed','manual_completed','manual_cancelled')"]
        params = []
        if status != 'all':
            clauses.append('status=?'); params.append(status)
        if search:
            clauses.append("(instr(lower(id),lower(?))>0 OR instr(lower(customer),lower(?))>0)")
            params.extend([search, search])
        where = ' WHERE ' + ' AND '.join(clauses)
        with database() as db:
            total = db.execute('SELECT count(*) FROM commerce_orders' + where, params).fetchone()[0]
            rows = db.execute('SELECT * FROM commerce_orders' + where + " ORDER BY CASE status WHEN 'manual_pending' THEN 0 WHEN 'manual_confirmed' THEN 1 WHEN 'manual_completed' THEN 2 ELSE 3 END,created_at DESC,id DESC LIMIT 30 OFFSET ?", (*params, (page - 1) * 30)).fetchall()
            return {'items': [commerce.order_view(r, True) for r in rows], 'total': total}

    @app.patch('/studio-api/manage/shop/orders/{ident}')
    def update(ident: str, payload: Update, actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM commerce_orders WHERE id=?', (ident,)).fetchone()
            if not row or row['status'] not in STATES:
                commerce.fail('order_not_found', 404)
            if row['version'] != payload.version:
                commerce.fail('version_conflict')
            if row['status'] in {'manual_completed', 'manual_cancelled'} and payload.status != row['status']:
                commerce.fail('shop_order_finished')
            if payload.status == 'manual_completed' and row['status'] != 'manual_completed':
                stocks = db.execute('SELECT product_id,sum(quantity) AS quantity FROM commerce_stock WHERE order_id=? GROUP BY product_id', (ident,)).fetchall()
                for stock in stocks:
                    product = db.execute('SELECT payload FROM commerce_products WHERE id=?', (stock['product_id'],)).fetchone()
                    if not product:
                        commerce.fail('stock_unavailable')
                    p = json.loads(product[0])
                    if p['stock'] - commerce.stock_held(db, p['id'], ident) < stock['quantity']:
                        commerce.fail('stock_unavailable')
                    p.update(stock=p['stock']-stock['quantity'], version=p['version']+1)
                    db.execute('UPDATE commerce_products SET payload=? WHERE id=?', (json.dumps(p, ensure_ascii=False), p['id']))
            fulfillment = {'manual_pending':'awaiting_contact', 'manual_confirmed':'confirmed', 'manual_completed':'completed', 'manual_cancelled':'cancelled'}[payload.status]
            db.execute('UPDATE commerce_orders SET status=?,fulfillment=?,staff_note=?,updated_at=?,version=version+1 WHERE id=?',
                       (payload.status, fulfillment, payload.staff_note, time.time(), ident))
            commerce.audit(db, ident, 'manual_order_updated', actor, json.dumps({'before':row['status'], 'after':payload.status}, ensure_ascii=False))
            return commerce.order_view(db.execute('SELECT * FROM commerce_orders WHERE id=?', (ident,)).fetchone(), True)
