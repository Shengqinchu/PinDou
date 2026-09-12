"""Import the reviewed catalog once. Existing owner edits are never overwritten.

Default is validation only. Run with --apply after the Studio release is installed.
No supplier requests, order creation, messages or payment configuration changes.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def import_products(database, rows, image_dir: Path, media_dir: Path, apply=False):
    import commerce, shop_catalog
    from PIL import Image
    ids=set(); sources=set(); checked=[]; images={}
    with database() as db:
        for row in rows:
            p=commerce.Product.model_validate(row['product'])
            if p.id in ids or row['source_key'] in sources:
                raise ValueError('Duplicate import identity')
            ids.add(p.id);sources.add(row['source_key'])
            if p.kind!='physical' or p.shop_collection!='home' or p.active or p.price_cents is not None or p.stock:
                raise ValueError('Imports must be unpriced catalog-only products')
            shop_catalog.validate_product_category(db,p)
            for src in p.images:
                if not re.fullmatch(r'/studio-api/media/[a-f0-9]{64}\.(jpg|png|webp)',src):
                    raise ValueError('Invalid imported media path')
                name=src.rsplit('/',1)[1];path=image_dir/name
                if hashlib.sha256(path.read_bytes()).hexdigest()!=name.split('.')[0]:
                    raise ValueError('Imported media hash mismatch')
                with Image.open(path) as im:im.verify()
                images[name]=path
            checked.append((p,row['source_key'],row['source']))
        existing={r[0] for r in db.execute('SELECT id FROM commerce_products')}
    new=[x for x in checked if x[0].id not in existing]
    if apply:
        media_dir.mkdir(parents=True,exist_ok=True)
        for name,path in images.items():
            target=media_dir/name
            if target.exists():
                if hashlib.sha256(target.read_bytes()).hexdigest()!=name.split('.')[0]:
                    raise ValueError('Stored image hash mismatch')
            else:target.write_bytes(path.read_bytes())
        inserted=0
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            for product,source_key,source in checked:
                if db.execute('SELECT 1 FROM commerce_products WHERE id=?',(product.id,)).fetchone():continue
                if db.execute('SELECT 1 FROM shop_import_sources WHERE source_key=?',(source_key,)).fetchone():continue
                shop_catalog.validate_product_category(db,product)
                db.execute('INSERT INTO commerce_products VALUES(?,?)',(product.id,product.model_dump_json()))
                db.execute('INSERT INTO shop_import_sources VALUES(?,?,?)',(source_key,product.id,json.dumps(source,ensure_ascii=False)))
                commerce.audit(db,product.id,'shop_product_imported','owner-request',json.dumps({'source_key':source_key}))
                inserted+=1
    else:inserted=0
    return {'products':len(checked),'new':len(new),'inserted':inserted,'preserved':len(checked)-len(new),'images':len(images),'applied':apply}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--service',type=Path,required=True)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--images',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    sys.path.insert(0,str(args.service.resolve()))
    import app
    app.DB_PATH=args.database.resolve()
    result=import_products(app.database,json.loads(args.source.read_text(encoding='utf8')),args.images,args.database.resolve().parent/'media',args.apply)
    print(json.dumps(result))
