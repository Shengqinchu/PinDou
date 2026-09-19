"""Reversible owner-list removal. Identity, balances and history stay intact."""
import hashlib
import json
import uuid
from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator


def initialize(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS studio_archives (
      kind TEXT NOT NULL, entity_id TEXT NOT NULL, deleted_at TEXT NOT NULL,
      actor TEXT NOT NULL, PRIMARY KEY(kind,entity_id)
    );
    CREATE TABLE IF NOT EXISTS studio_archive_actions (
      idempotency_key TEXT PRIMARY KEY, request_hash TEXT NOT NULL,
      created_at TEXT NOT NULL, actor TEXT NOT NULL, result TEXT NOT NULL
    );
    """)


def archived(db, kind, entity_id):
    row = db.execute('SELECT deleted_at FROM studio_archives WHERE kind=? AND entity_id=?',
                     (kind, entity_id)).fetchone()
    return row[0] if row else None


class Entity(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=128)
    version: int = Field(ge=1, strict=True)


class MemberAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['delete', 'restore']
    version: int = Field(ge=1, strict=True)


class ProductAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['delete', 'restore']
    items: list[Entity] = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def unique(self):
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError('Duplicate products')
        return self


def change(db, kind, items, action, key, actor):
    import commerce
    import wallet
    try:
        uuid.UUID(key)
    except ValueError:
        raise HTTPException(422, 'invalid_request_id') from None
    encoded = json.dumps({'kind': kind, 'items': [i.model_dump() for i in items], 'action': action}, sort_keys=True)
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    db.execute('BEGIN IMMEDIATE')
    old_action = db.execute('SELECT request_hash,result FROM studio_archive_actions WHERE idempotency_key=?', (key,)).fetchone()
    if old_action:
        if old_action['request_hash'] != digest:
            raise HTTPException(409, 'wallet_request_changed')
        return json.loads(old_action['result'])
    records = []
    # Check every version before writing any item in a batch.
    for item in items:
        if kind == 'member':
            record = wallet.member(db, item.id)
        else:
            row = db.execute('SELECT payload FROM commerce_products WHERE id=?', (item.id,)).fetchone()
            if not row:
                commerce.fail('product_unavailable', 404)
            record = json.loads(row[0])
            if not record.get('shop_collection'):
                commerce.fail('invalid_product', 422)
        if record['version'] != item.version or bool(archived(db, kind, item.id)) != (action == 'restore'):
            raise HTTPException(409, 'version_conflict')
        records.append((item, record))
    stamp = wallet.now()
    for item, record in records:
        if action == 'delete':
            db.execute('INSERT INTO studio_archives VALUES(?,?,?,?)', (kind, item.id, stamp, actor))
        else:
            db.execute('DELETE FROM studio_archives WHERE kind=? AND entity_id=?', (kind, item.id))
        if kind == 'member':
            db.execute('UPDATE studio_members SET version=version+1,updated_at=? WHERE owner_id=?', (stamp, item.id))
            db.execute('INSERT INTO studio_audit(request_id,changed_at,actor,previous_status,new_status,staff_note) VALUES(?,?,?,?,?,?)',
                       (item.id, stamp, actor, 'member_deleted' if action == 'restore' else 'member_active',
                        'member_active' if action == 'restore' else 'member_deleted', 'History and balances retained'))
        else:
            record['version'] += 1
            db.execute('UPDATE commerce_products SET payload=? WHERE id=?', (json.dumps(record, ensure_ascii=False), item.id))
            commerce.audit(db, item.id, 'shop_product_' + action, actor, json.dumps({'request_id': key, 'version': record['version']}))
    result = {'changed': len(items), 'action': action}
    db.execute('INSERT INTO studio_archive_actions VALUES(?,?,?,?,?)', (key, digest, stamp, actor, json.dumps(result)))
    return result


def register(app, database, admin_actor):
    @app.post('/studio-api/manage/shop/products/archive')
    def products(payload: ProductAction, idempotency_key: Annotated[str, Header()], actor=Depends(admin_actor)):
        with database() as db:
            return change(db, 'product', payload.items, payload.action, idempotency_key, actor)

    @app.post('/studio-api/manage/members/{owner_id}/archive')
    def member(owner_id: str, payload: MemberAction, idempotency_key: Annotated[str, Header()], actor=Depends(admin_actor)):
        with database() as db:
            return change(db, 'member', [Entity(id=owner_id, version=payload.version)], payload.action, idempotency_key, actor)
