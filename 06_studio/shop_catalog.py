"""Shop browsing and owner-editable categories; checkout retains its existing gate."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Literal
from fastapi import Depends
from pydantic import Field, ValidationError, model_validator
import commerce

database = None


class Category(commerce.Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    parent_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    zh: str = Field(min_length=1, max_length=60)
    en: str = Field(min_length=1, max_length=100)
    sort: int = Field(default=0, ge=0, le=100000, strict=True)
    visible: bool = True
    version: int = Field(default=1, ge=1, strict=True)


class ProductChange(commerce.Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    version: int = Field(ge=1, strict=True)
    price_cents: int | None = Field(default=None, ge=1, le=1000000, strict=True)
    images: list[str] | None = Field(default=None, max_length=12)
    image_mode: Literal['append', 'replace'] = 'append'

    @model_validator(mode='after')
    def changed_fields(self):
        if 'price_cents' not in self.model_fields_set and self.images is None:
            raise ValueError('Choose a price or image change')
        return self


class ProductBatch(commerce.Strict):
    items: list[ProductChange] = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def unique_products(self):
        if len({p.id for p in self.items}) != len(self.items):
            raise ValueError('Duplicate products')
        return self


def initialize(db_func):
    global database
    database = db_func
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS shop_categories(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS shop_import_sources(
          source_key TEXT PRIMARY KEY,product_id TEXT NOT NULL UNIQUE,payload TEXT NOT NULL);
        """)
        seed = json.loads(Path(__file__).with_name('shop-categories.json').read_text(encoding='utf8'))
        for data in seed:
            category = Category.model_validate(data)
            db.execute('INSERT OR IGNORE INTO shop_categories VALUES(?,?)', (category.id, category.model_dump_json()))
        for data in json.loads(Path(__file__).with_name('shop-services.json').read_text(encoding='utf8')):
            product = commerce.Product.model_validate(data)
            db.execute('INSERT OR IGNORE INTO commerce_products VALUES(?,?)', (product.id, product.model_dump_json()))


def categories_for(db):
    return sorted([json.loads(r[0]) for r in db.execute('SELECT payload FROM shop_categories')], key=lambda c: (c['sort'], c['id']))


def validate_product_category(db, product):
    if not product.shop_collection:
        return
    if product.shop_collection != 'home':
        if product.shop_category_id is not None:
            commerce.fail('shop_category_invalid', 422)
        return
    categories = categories_for(db)
    if not any(c['id'] == product.shop_category_id and c['parent_id'] for c in categories):
        commerce.fail('shop_category_invalid', 422)


def catalog_for(db, admin=False):
    categories = categories_for(db)
    products = [commerce.Product.model_validate(p).model_dump() for p in commerce.products_for(db) if p.get('shop_collection')]
    if not admin:
        roots = {c['id'] for c in categories if not c['parent_id'] and c['visible']}
        categories = [c for c in categories if c['visible'] and (not c['parent_id'] or c['parent_id'] in roots)]
        ids = {c['id'] for c in categories}
        products = [p for p in products if p['shop_visible'] and (p['shop_collection'] != 'home' or p['shop_category_id'] in ids)]
    products.sort(key=lambda p: (p['sort'], p['id']))
    return {'categories': categories, 'products': products, 'checkout_ready': commerce.commerce_ready(commerce.settings_for(db))}


def register(app, admin_actor):
    @app.patch('/studio-api/manage/shop/products/batch')
    def update_products(payload: ProductBatch, actor=Depends(admin_actor)):
        batch_id = uuid.uuid4().hex
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            changes = []
            # Validate the complete selection before any product or audit write.
            for patch in payload.items:
                row = db.execute('SELECT payload FROM commerce_products WHERE id=?', (patch.id,)).fetchone()
                if not row:
                    commerce.fail('product_unavailable', 404)
                old = json.loads(row[0])
                if not old.get('shop_collection'):
                    commerce.fail('invalid_product', 422)
                if old['version'] != patch.version:
                    commerce.fail('version_conflict')
                value = dict(old)
                if 'price_cents' in patch.model_fields_set:
                    value['price_cents'] = patch.price_cents
                if patch.images is not None:
                    images = (value.get('images', []) if patch.image_mode == 'append' else []) + patch.images
                    value['images'] = list(dict.fromkeys(images))
                    if len(value['images']) > 12:
                        commerce.fail('shop_too_many_images', 422)
                    value['image'] = value['images'][0] if value['images'] else ''
                # Preserve title, stock, visibility and payment flags.
                try:
                    product = commerce.Product.model_validate(value)
                except ValidationError:
                    commerce.fail('invalid_product', 422)
                validate_product_category(db, product)
                normalized = product.model_dump()
                if normalized == commerce.Product.model_validate(old).model_dump():
                    continue
                normalized['version'] += 1
                changes.append((patch.id, old, normalized))
            for product_id, old, value in changes:
                db.execute('UPDATE commerce_products SET payload=? WHERE id=?', (json.dumps(value, ensure_ascii=False), product_id))
                commerce.audit(db, product_id, 'shop_product_batch_updated', actor,
                               json.dumps({'batch_id':batch_id, 'before':old, 'after':value}, ensure_ascii=False))
        return {'batch_id':batch_id, 'updated':len(changes), 'products':[v for _,_,v in changes]}

    @app.get('/studio-api/shop/catalog')
    def public_catalog():
        with database() as db:
            return catalog_for(db)

    @app.get('/studio-api/manage/shop')
    def owner_catalog(_actor=Depends(admin_actor)):
        with database() as db:
            result = catalog_for(db, True)
            # Supplier prices never appear in customer-facing catalog responses.
            result['sources'] = {r['product_id']: json.loads(r['payload']) for r in db.execute('SELECT product_id,payload FROM shop_import_sources')}
            return result

    @app.put('/studio-api/manage/shop/categories/{category_id}')
    def save_category(category_id: str, payload: Category, actor=Depends(admin_actor)):
        if category_id != payload.id:
            commerce.fail('shop_category_invalid', 422)
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            categories = {c['id']: c for c in categories_for(db)}
            old = categories.get(category_id)
            if (old and old['version'] != payload.version) or (not old and payload.version != 1):
                commerce.fail('version_conflict')
            if payload.parent_id:
                parent = categories.get(payload.parent_id)
                if not parent or parent['parent_id'] or parent['id'] == category_id or any(c['parent_id'] == category_id for c in categories.values()):
                    commerce.fail('shop_category_invalid', 422)
            elif old and old['parent_id']:
                if any(p.get('shop_category_id') == category_id for p in commerce.products_for(db)):
                    commerce.fail('shop_category_in_use', 409)
            value = payload.model_dump()
            value['version'] += 1
            db.execute('INSERT INTO shop_categories VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (category_id, json.dumps(value, ensure_ascii=False)))
            commerce.audit(db, category_id, 'shop_category_updated', actor, json.dumps({'before':old,'after':value}, ensure_ascii=False))
        return value
