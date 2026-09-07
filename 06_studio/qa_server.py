"""Local browser QA only. Explicitly bound to loopback; never packaged/deployed.

Uses an isolated test DB and provider double, never merchant credentials.
"""
import json
import os
import tempfile
from pathlib import Path

import uvicorn
from fastapi.responses import Response

import app as studio
import commerce
from test_commerce import FakeGateway

studio.DB_PATH = Path(tempfile.mkdtemp(prefix="pindou-commerce-qa-")) / "qa.sqlite3"
commerce.gateway = FakeGateway()
studio.app.dependency_overrides[studio.admin_actor] = lambda: "local-qa"
studio.initialize()
with studio.database() as db:
    settings = commerce.settings_for(db)
    settings.update(enabled=True, capacity=4, tax_mode="included")
    for row in settings["weekly"]:
        row["enabled"] = True
    db.execute("UPDATE commerce_settings SET payload=? WHERE id=1", (json.dumps(settings),))
    product = next(p for p in commerce.products_for(db) if p["id"] == "starter")
    product.update(active=True, price_cents=1200, stock=10)
    db.execute("UPDATE commerce_products SET payload=? WHERE id='starter'", (json.dumps(product, ensure_ascii=False),))


def create(order_id, amount):
    result = FakeGateway.create(commerce.gateway, order_id, amount)
    # In the local fixture only, use a clearly-labelled visual in place of a live QR.
    result["qr_url"] = "/studio-api/qa/qr"
    return result


commerce.gateway.create = create


@studio.app.get('/studio-api/qa/qr')
def qr():
    return Response('<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220"><rect width="220" height="220" fill="#eee9de"/><text x="110" y="90" font-family="sans-serif" font-size="16" text-anchor="middle">LOCAL QA ONLY</text><text x="110" y="125" font-family="sans-serif" font-size="12" text-anchor="middle">No real payment</text></svg>', media_type='image/svg+xml')


@studio.app.post('/studio-api/qa/paid/{order_id}')
def paid(order_id: str):
    commerce.gateway.orders[order_id]['status'] = 'OD'
    commerce.reconcile(order_id, force=True)
    return {'ok': True}


if __name__ == '__main__':
    uvicorn.run(studio.app, host='127.0.0.1', port=8011, access_log=False)
