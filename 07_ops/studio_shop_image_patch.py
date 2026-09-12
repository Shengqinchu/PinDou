"""Apply a reviewed, versioned image-only catalog patch through Studio's batch handler.

Default: validate and execute against a disposable database copy. --apply stores
original media, creates a SQLite backup, and calls the same all-or-nothing handler.
The input snapshot and image manifest contain public product data, never cookies.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_products(path):
    with sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True) as db:
        return dict(db.execute('SELECT id,payload FROM commerce_products'))


def patch(args):
    sys.path.insert(0, str(args.service.resolve()))
    from fastapi import FastAPI
    from PIL import Image
    import commerce
    import content
    import shop_catalog

    snapshot = json.loads(args.snapshot.read_text(encoding='utf-8'))
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    expected = set(snapshot['single_codes'])
    assert manifest['expected'] == manifest['downloaded'] == len(expected)
    assert not manifest['errors'] and not manifest['duplicate_images']
    assert len(expected) == snapshot['single_count']
    assert {r['code'] for r in manifest['images']} == expected
    assert len(manifest['images']) == len(expected)
    assert re.fullmatch(r'\d+', manifest['item_id'])
    before = read_products(args.database)
    selected = {}
    for row in snapshot['products']:
        p = row['product']
        assert digest(before[p['id']].encode()) == row['sha256'], 'Catalog changed; obtain a new snapshot'
        if p.get('code') in expected:
            assert p['code'] not in selected
            assert re.fullmatch(r'[A-HM][1-9]\d?', p['code'])
            assert p['kind'] == 'physical' and p['shop_collection'] == 'home'
            selected[p['code']] = p
    assert len(selected) == len(expected)
    protected = {r['id'] for r in snapshot['protected_bundles']}
    assert not protected.intersection(p['id'] for p in selected.values())

    changes = []
    media = []
    for row in manifest['images']:
        p = selected[row['code']]
        assert re.fullmatch(re.escape(row['code']) + r'\.(jpg|png|webp)', row['file'])
        file = args.images / row['file']
        raw = file.read_bytes()
        assert len(raw) == row['bytes'] and digest(raw) == row['sha256']
        with Image.open(file) as image:
            image.verify()
        with Image.open(file) as image:
            assert image.size == (row['width'], row['height'])
            assert image.format == row['format']
            assert min(image.size) >= 300
        suffix = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}[row['format']]
        src = '/studio-api/media/' + row['sha256'] + '.' + suffix
        # Explicit replacement applies only to the owner's selected individual colors.
        changes.append({'id':p['id'], 'version':p['version'], 'images':[src], 'image_mode':'replace'})
        media.append((file, src))
    payload = shop_catalog.ProductBatch.model_validate({'items':changes})
    args.evidence.mkdir(parents=True, exist_ok=True)

    def execute(database_path):
        @contextmanager
        def database():
            db = sqlite3.connect(database_path, timeout=15)
            db.row_factory = sqlite3.Row
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        shop_catalog.database = database
        api = FastAPI()
        shop_catalog.register(api, lambda: None)
        handler = next(r.endpoint for r in api.routes if r.path == '/studio-api/manage/shop/products/batch')
        # This is an owner-authorized local operational call, not an exposed auth override.
        return handler(payload, actor='owner-request:taobao-sku-images:' + manifest['item_id'])

    def verify(after):
        assert before.keys() == after.keys()
        planned = {r['id']:r for r in changes}
        changed = 0
        for ident, raw in before.items():
            if ident not in planned:
                assert raw == after[ident], 'An unselected product changed'
                continue
            old, new = json.loads(raw), json.loads(after[ident])
            assert new['images'] == planned[ident]['images']
            assert new['image'] == planned[ident]['images'][0]
            assert {k:v for k,v in old.items() if k not in ('image','images','version')} == {
                k:v for k,v in new.items() if k not in ('image','images','version')}, 'Non-image product field changed'
            assert new['version'] == old['version'] + (0 if old == new else 1)
            changed += old != new
        return changed

    # Exercise the deployed handler on a disposable copy before any live mutation.
    with tempfile.TemporaryDirectory(prefix='shop-image-check-') as directory:
        test_db = Path(directory)/'catalog.sqlite3'
        with sqlite3.connect(args.database) as source, sqlite3.connect(test_db) as target:
            source.backup(target)
        tested = execute(test_db)
        assert verify(read_products(test_db)) == tested['updated']

    result = {'checked_at':datetime.now(timezone.utc).isoformat(), 'item_id':manifest['item_id'],
              'selected':len(changes), 'protected_bundles':len(protected), 'original_images':len(media),
              'preview_updated':tested['updated'], 'applied':False}
    (args.evidence/'plan.json').write_text(json.dumps({'result':result,'items':changes},indent=2),encoding='utf-8')
    if args.apply:
        assert read_products(args.database) == before, 'Catalog changed since validation'
        backup = args.evidence/'before.sqlite3'
        assert not backup.exists(), 'Use a new evidence directory for each application'
        with sqlite3.connect(args.database) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        (args.evidence/'before-products.json').write_text(json.dumps(before,ensure_ascii=False),encoding='utf-8')
        content.MEDIA_DIR = args.database.parent/'media'
        owner = args.database.stat()
        for file, src in media:
            stored = content.store_image(file.read_bytes(), original=True)
            assert stored['src'] == src
            destination = content.MEDIA_DIR/src.rsplit('/',1)[1]
            if hasattr(os,'chown'):
                os.chown(destination,owner.st_uid,owner.st_gid)
            destination.chmod(0o600)
        applied = execute(args.database)
        after = read_products(args.database)
        assert verify(after) == applied['updated']
        (args.evidence/'after-products.json').write_text(json.dumps(after,ensure_ascii=False),encoding='utf-8')
        result.update(applied=True,updated=applied['updated'],batch_id=applied['batch_id'],
                      backup=str(backup),unselected_unchanged=len(before)-len(changes),non_image_fields_unchanged=True)
    (args.evidence/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('service','database','snapshot','manifest','images','evidence'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    patch(parser.parse_args())
