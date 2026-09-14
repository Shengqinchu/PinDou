"""Add the two owner-approved scenery products once, without editing old goods."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

MIGRATION = 'scenery-products-20260913'
IDS = {'scenery-sunset-apocalypse', 'scenery-blue-coast'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def catalog_hash(db):
    return digest([tuple(r) for r in db.execute('SELECT id,payload FROM commerce_products ORDER BY id')])


def protected_hashes(db):
    names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    # Only product inserts, their audit events, and the one-time marker may change.
    return {name: digest([tuple(r) for r in db.execute('SELECT * FROM "'+name.replace('"','""')+'" ORDER BY rowid')])
            for name in names if name not in {'commerce_products','commerce_events','shop_catalog_migrations'}}


def plan(db, seeds):
    import commerce, shop_catalog
    if db.execute('SELECT 1 FROM shop_catalog_migrations WHERE id=?', (MIGRATION,)).fetchone():
        return {'already_applied': True, 'catalog_sha256': catalog_hash(db)}, []
    if len(seeds) != 2 or {p['id'] for p in seeds} != IDS:
        raise ValueError('Expected the two scenery products')
    current = {r[0] for r in db.execute('SELECT id FROM commerce_products')}
    products = []
    for seed in seeds:
        p = commerce.Product.model_validate(seed)
        if p.id in current:
            raise ValueError('Product ID already exists: '+p.id)
        assert p.shop_collection == 'finished' and p.shop_visible and p.price_cents is not None
        assert [v.id for v in p.variants] == ['1','2','3','4','full-set']
        assert p.variants[-1].price_cents is not None and p.quantity_offer is None
        shop_catalog.validate_product_category(db, p)
        products.append(p.model_dump())
    return {'already_applied':False, 'catalog_sha256':catalog_hash(db), 'seed_sha256':digest(seeds),
            'create':[{'id':p['id'],'name':p['zh'],'single_cents':p['price_cents'],
                       'full_set_cents':p['variants'][-1]['price_cents'],'variants':len(p['variants']),
                       'images':len(p['images'])} for p in products], 'existing_products_changed':0}, products


def apply(db, seeds, expected):
    import commerce
    db.execute('BEGIN IMMEDIATE')
    try:
        report, products = plan(db, seeds)
        if report['already_applied']:
            db.rollback()
            return report
        if report['catalog_sha256'] != expected:
            raise ValueError('Catalog changed after preview')
        before = protected_hashes(db)
        old = dict(db.execute('SELECT id,payload FROM commerce_products'))
        for p in products:
            payload = json.dumps(p, ensure_ascii=False)
            db.execute('INSERT INTO commerce_products VALUES(?,?)', (p['id'],payload))
            commerce.audit(db,p['id'],'scenery_product_added','owner-request-20260913',payload)
        db.execute('INSERT INTO shop_catalog_migrations VALUES(?)', (MIGRATION,))
        assert protected_hashes(db) == before, 'Protected business data changed'
        after = dict(db.execute('SELECT id,payload FROM commerce_products'))
        assert all(after[k] == value for k,value in old.items()), 'Existing goods changed'
        assert set(after) - set(old) == IDS
        db.commit()
        return report | {'applied':True,'protected_tables_unchanged':len(before),'existing_products_unchanged':len(old),'after_sha256':catalog_hash(db)}
    except BaseException:
        db.rollback()
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db',required=True)
    parser.add_argument('--products',required=True)
    parser.add_argument('--service-root',required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--expect')
    parser.add_argument('--backup')
    args = parser.parse_args()
    sys.path.insert(0,args.service_root)
    seeds = json.loads(Path(args.products).read_text(encoding='utf8'))
    with sqlite3.connect('file:'+args.db+('?mode=rw' if args.apply else '?mode=ro'),uri=True,timeout=15) as db:
        db.row_factory = sqlite3.Row
        if args.apply:
            if not args.expect or not args.backup:
                raise ValueError('Apply needs the preview hash and a new backup path')
            dest = Path(args.backup)
            if dest.exists():
                raise ValueError('Backup already exists')
            dest.parent.mkdir(parents=True,exist_ok=True)
            with sqlite3.connect(dest) as backup:
                db.backup(backup)
            result = apply(db,seeds,args.expect) | {'backup':str(dest)}
        else:
            result = plan(db,seeds)[0]
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()
