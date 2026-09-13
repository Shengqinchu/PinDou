"""One-time owner PDF import. Preview first; apply requires the exact catalog hash."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time

MIGRATION='finished-products-and-manual-orders-20260913'
PROTECTED=('shop_categories','studio_reservations','studio_booking_profiles','studio_members',
           'studio_wallet_ledger','studio_journal','studio_finance_entries','commerce_settings','studio_content','commerce_orders')


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def catalog_hash(db):
    return digest([tuple(r) for r in db.execute('SELECT id,payload FROM commerce_products ORDER BY id')])


def protected_hashes(db):
    return {t:digest([tuple(r) for r in db.execute('SELECT * FROM "'+t+'" ORDER BY rowid')]) for t in PROTECTED}


def plan(db,seeds):
    import commerce,shop_catalog
    current={p['id']:p for p in commerce.products_for(db)}
    if db.execute('SELECT 1 FROM shop_catalog_migrations WHERE id=?',(MIGRATION,)).fetchone():
        return {'already_applied':True,'catalog_sha256':catalog_hash(db)},[]
    if len(seeds)!=4 or len({p['id'] for p in seeds})!=4:
        raise ValueError('Expected exactly four distinct finished products')
    changes=[]
    for seed in seeds:
        p=commerce.Product.model_validate(seed)
        assert p.shop_collection=='finished' and p.shop_visible and p.price_cents is not None
        if p.id in current:raise ValueError('An owner product already uses '+p.id)
        shop_catalog.validate_product_category(db,p)
        changes.append((p.id,None,p.model_dump()))
    for p in current.values():
        if p.get('shop_collection') and p['stock']!=999:
            if commerce.stock_held(db,p['id'])>999:raise ValueError('Reserved stock exceeds 999')
            changes.append((p['id'],p,dict(p,stock=999,version=p['version']+1)))
    return {'already_applied':False,'catalog_sha256':catalog_hash(db),'create':[{'id':p['id'],'name':p['zh'],'cad':p['price_cents']/100,'variants':len(p['variants']),'images':len(p['images'])} for _,old,p in changes if old is None],
            'existing_stock_updates':sum(old is not None for _,old,_ in changes),'shop_products_after':sum(bool(p.get('shop_collection')) for p in current.values())+4,
            'payment_gateway_changed':False,'enable_manual_ordering':True},changes


def apply(db,seeds,expected):
    import commerce
    db.execute('BEGIN IMMEDIATE')
    report,changes=plan(db,seeds)
    if report['already_applied']:
        db.rollback();return report
    if report['catalog_sha256']!=expected:
        db.rollback();raise ValueError('Catalog changed after preview; run preview again')
    before=protected_hashes(db)
    for ident,old,value in changes:
        db.execute('INSERT INTO commerce_products VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(ident,json.dumps(value,ensure_ascii=False)))
        commerce.audit(db,ident,'finished_product_imported' if old is None else 'owner_stock_initialized','owner-pdf-20260913',json.dumps({'before':old,'after':value},ensure_ascii=False))
    db.execute('UPDATE shop_order_settings SET enabled=1 WHERE id=1')
    db.execute('INSERT INTO shop_catalog_migrations VALUES(?)',(MIGRATION,))
    assert protected_hashes(db)==before,'Protected business data changed'
    db.commit()
    return report|{'applied':True,'protected_tables_unchanged':list(before),'after_sha256':catalog_hash(db)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--db',required=True);parser.add_argument('--products',required=True)
    parser.add_argument('--service-root',default=str(Path(__file__).resolve().parents[1]/'06_studio'))
    parser.add_argument('--apply',action='store_true');parser.add_argument('--expect');parser.add_argument('--backup')
    args=parser.parse_args();sys.path.insert(0,args.service_root)
    seeds=json.loads(Path(args.products).read_text(encoding='utf8'))
    db=sqlite3.connect(('file:'+args.db+'?mode=rw') if args.apply else ('file:'+args.db+'?mode=ro'),uri=True,timeout=15);db.row_factory=sqlite3.Row
    if args.apply:
        if not args.expect or not args.backup:raise ValueError('Apply needs the reviewed hash and a new backup path')
        dest=Path(args.backup)
        if dest.exists():raise ValueError('Backup already exists')
        dest.parent.mkdir(parents=True,exist_ok=True)
        backup=sqlite3.connect(dest);db.backup(backup);backup.close()
        result=apply(db,seeds,args.expect)|{'backup':str(dest)}
    else:result=plan(db,seeds)[0]
    print(json.dumps(result,ensure_ascii=False))
    db.close()

if __name__=='__main__':main()
