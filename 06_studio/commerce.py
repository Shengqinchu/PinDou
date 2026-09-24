"""Server-priced checkout, durable seat/stock holds and verified payment fulfillment."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Annotated, Literal
from urllib.parse import parse_qsl
from zoneinfo import ZoneInfo

from fastapi import Depends, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from payments import gateway, PaymentUnavailable, PaymentRejected

TORONTO = ZoneInfo("America/Toronto")
database = None
PENDING = ("creating", "pending", "payment_uncertain")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Hours(Strict):
    day: int = Field(ge=0, le=6)
    enabled: bool = False
    start: str = "10:00"
    end: str = "22:00"

    @model_validator(mode="after")
    def interval(self):
        if minutes(self.end) <= minutes(self.start):
            raise ValueError("Closing must follow opening")
        return self


class DateHours(Strict):
    date: date
    enabled: bool = False
    start: str = "10:00"
    end: str = "22:00"

    @model_validator(mode="after")
    def interval(self):
        if minutes(self.end) <= minutes(self.start):
            raise ValueError("Closing must follow opening")
        return self


class Settings(Strict):
    enabled: bool = False
    capacity: int = Field(default=0, ge=0, le=100, strict=True)
    weekly: list[Hours] = Field(min_length=7, max_length=7)
    overrides: list[DateHours] = Field(default_factory=list, max_length=90)
    fx_cny_per_cad: str = Field(default="5.0000", pattern=r"^\d{1,2}(\.\d{1,4})?$")
    tax_mode: Literal["unconfirmed", "included", "additional"] = "unconfirmed"
    tax_bps: int = Field(default=0, ge=0, le=3000, strict=True)
    notice_minutes: int = Field(default=30, ge=0, le=1440, strict=True)
    version: int = Field(default=1, ge=1, strict=True)

    @model_validator(mode="after")
    def unique_days(self):
        if {row.day for row in self.weekly} != set(range(7)) or len({row.date for row in self.overrides}) != len(self.overrides):
            raise ValueError("Duplicate or missing schedule days")
        if Decimal(self.fx_cny_per_cad) <= 0:
            raise ValueError("Exchange rate must be positive")
        if self.enabled and self.tax_mode == "unconfirmed":
            raise ValueError("Confirm final pricing before opening checkout")
        return self


class ProductOption(Strict):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,39}$")
    zh: str = Field(min_length=1, max_length=80)
    en: str = Field(min_length=1, max_length=120)


class ProductVariant(ProductOption):
    # None inherits the product price. A set can carry its own full price.
    price_cents: int | None = Field(default=None, ge=1, le=1000000, strict=True)


class QuantityOffer(Strict):
    quantity: int = Field(ge=2, le=20, strict=True)
    price_cents: int = Field(ge=1, le=1000000, strict=True)


class Product(Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    kind: Literal["experience", "physical"]
    category: Literal["experience", "tools", "beads", "finished"]
    zh: str = Field(min_length=1, max_length=200)
    en: str = Field(min_length=1, max_length=200)
    detailZh: str = Field(default="", max_length=10000)
    detailEn: str = Field(default="", max_length=10000)
    image: str = Field(default="", max_length=350)
    images: list[str] = Field(default_factory=list, max_length=12)
    shop_collection: Literal["home", "finished", "services"] | None = None
    shop_category_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    shop_visible: bool = False
    code: str = Field(default="", max_length=50)
    sort: int = Field(default=0, ge=0, le=100000, strict=True)
    price_cents: int | None = Field(default=None, ge=1, le=1000000, strict=True)
    stock: int = Field(default=0, ge=0, le=100000, strict=True)
    variants: list[ProductVariant] = Field(default_factory=list, max_length=100)
    choices: list[ProductOption] = Field(default_factory=list, max_length=20)
    choiceZh: str = Field(default="制作方式", min_length=1, max_length=80)
    choiceEn: str = Field(default="Finish", min_length=1, max_length=120)
    quantity_offer: QuantityOffer | None = None
    active: bool = False
    version: int = Field(default=1, ge=1, strict=True)

    @model_validator(mode="after")
    def published_price(self):
        import content
        if any(len({v.id for v in values}) != len(values) for values in (self.variants, self.choices)):
            raise ValueError("Duplicate product options")
        if self.quantity_offer and self.price_cents is not None and self.quantity_offer.price_cents >= self.price_cents * self.quantity_offer.quantity:
            raise ValueError("Offer must cost less than buying the items individually")
        for src in [self.image, *self.images]:
            if src and not (re.fullmatch(r"studio-(0[1-9]|1[0-5])|journal-(02|04|05|07|10|11|13|20)", src) or content.image_path_ok(src)):
                raise ValueError("Use a studio image upload")
        if len(set(self.images)) != len(self.images) or any(not src for src in self.images):
            raise ValueError("Duplicate or empty images")
        if self.shop_collection and self.kind != "physical":
            raise ValueError("Shop items must be physical products")
        if self.shop_visible and not self.shop_collection:
            raise ValueError("Choose a shop collection")
        if self.active and self.price_cents is None:
            raise ValueError("Published products need a price")
        if self.kind == "experience" and self.id not in {"hourly", "day", "pair"}:
            raise ValueError("Unknown experience")
        if self.kind == "physical" and self.id in {"hourly", "day", "pair"}:
            raise ValueError("Reserved experience ID")
        return self


class Selection(Strict):
    date: date
    start: str
    end: str
    guests: int = Field(ge=1, le=100, strict=True)

    @model_validator(mode="after")
    def valid(self):
        if minutes(self.end) <= minutes(self.start):
            raise ValueError("Invalid visit interval")
        return self


class Line(Strict):
    product_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    quantity: int = Field(ge=1, le=20, strict=True)
    booking: Selection | None = None


class Cart(Strict):
    items: list[Line] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique(self):
        if len({(line.product_id, line.booking.model_dump_json() if line.booking else "") for line in self.items}) != len(self.items):
            raise ValueError("Duplicate line items")
        return self


class Checkout(Cart):
    name: str = Field(min_length=1, max_length=80)
    contact_method: Literal["wechat", "email", "phone"]
    contact: str = Field(min_length=3, max_length=180)
    notes: str = Field(default="", max_length=1500)
    locale: Literal["zh", "en"] = "zh"
    consent: Literal[True]
    website: str = Field(default="", max_length=0)
    quote_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    access_key: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def contact_valid(self):
        if self.contact_method == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.contact):
            raise ValueError("Invalid email")
        if self.contact_method == "phone" and (not re.fullmatch(r"[+\d ()-]{7,30}", self.contact) or len(re.sub(r"\D", "", self.contact)) < 7):
            raise ValueError("Invalid phone")
        return self


class Fulfillment(Strict):
    completed: bool
    staff_note: str = Field(default="", max_length=1500)
    version: int = Field(ge=1, strict=True)


def fail(code: str, status=409):
    raise HTTPException(status, code)


def minutes(value: str) -> int:
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):(?:00|30)", value):
        raise ValueError("Use half-hour intervals")
    hh, mm = value.split(":")
    return int(hh) * 60 + int(mm)


def clock(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def now_local():
    return datetime.now(TORONTO)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def audit(db, order_id, event, actor="system", detail=""):
    db.execute("INSERT INTO commerce_events(order_id,created_at,event,actor,detail) VALUES(?,?,?,?,?)", (order_id, time.time(), event, actor, detail))


def initialize(db_func):
    global database
    database = db_func
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS commerce_settings (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS commerce_products (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS commerce_orders (
          id TEXT PRIMARY KEY, created_at REAL NOT NULL, updated_at REAL NOT NULL,
          status TEXT NOT NULL, access_hash TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
          payload_hash TEXT NOT NULL, customer TEXT NOT NULL, quote TEXT NOT NULL,
          expires_at REAL NOT NULL, hold_until REAL NOT NULL, payment_url TEXT NOT NULL DEFAULT '',
          qr_url TEXT NOT NULL DEFAULT '', provider_id TEXT NOT NULL DEFAULT '',
          trade_id TEXT UNIQUE, paid_at REAL, last_check REAL NOT NULL DEFAULT 0,
          fulfillment TEXT NOT NULL DEFAULT 'awaiting_payment', staff_note TEXT NOT NULL DEFAULT '',
          version INTEGER NOT NULL DEFAULT 1, owner_id TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS commerce_seats (
          order_id TEXT NOT NULL, date TEXT NOT NULL, start INTEGER NOT NULL,
          end INTEGER NOT NULL, guests INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS commerce_seat_date ON commerce_seats(date,start,end);
        CREATE TABLE IF NOT EXISTS commerce_stock (order_id TEXT NOT NULL, product_id TEXT NOT NULL, quantity INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS commerce_stock_product ON commerce_stock(product_id);
        CREATE TABLE IF NOT EXISTS commerce_events (
          id INTEGER PRIMARY KEY, order_id TEXT NOT NULL, created_at REAL NOT NULL,
          event TEXT NOT NULL, actor TEXT NOT NULL, detail TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS commerce_limits (
          client TEXT NOT NULL, bucket INTEGER NOT NULL, count INTEGER NOT NULL,
          PRIMARY KEY(client,bucket)
        );
        """)
        if 'owner_id' not in {r[1] for r in db.execute('PRAGMA table_info(commerce_orders)')}:
            db.execute("ALTER TABLE commerce_orders ADD COLUMN owner_id TEXT NOT NULL DEFAULT ''")
        db.execute('CREATE INDEX IF NOT EXISTS commerce_orders_owner ON commerce_orders(owner_id,created_at DESC)')
        import admin_archives
        admin_archives.initialize(db)
        settings = Settings(weekly=[Hours(day=i) for i in range(7)])
        db.execute("INSERT OR IGNORE INTO commerce_settings VALUES(1,?)", (settings.model_dump_json(),))
        seeds = [
            dict(id="hourly", zh="按时体验", en="By the hour", price_cents=800),
            dict(id="day", zh="单人全天", en="A day for one", price_cents=4990),
            dict(id="pair", zh="双人全天", en="A day for two", price_cents=8880),
        ]
        for item in seeds:
            product = Product(**item, kind="experience", category="experience", image="studio-04", active=True)
            db.execute("INSERT OR IGNORE INTO commerce_products VALUES(?,?)", (product.id, product.model_dump_json()))
        for pid, cat, zh, en, img in [
            ("starter", "tools", "给第一幅作品的工具", "Your first little toolkit", "studio-07"),
            ("beads", "beads", "刚好缺的那一抹颜色", "A little more colour", "studio-06"),
            ("findings", "tools", "让拼豆变成随身小物", "The finishing touches", "studio-11"),
            ("custom", "finished", "一份专属的手作心意", "Something made for you", "journal-05"),
        ]:
            product = Product(id=pid, kind="physical", category=cat, zh=zh, en=en, image=img,
                              detailZh="款式与售价整理中，敬请期待。", detailEn="Styles and prices are being prepared.")
            db.execute("INSERT OR IGNORE INTO commerce_products VALUES(?,?)", (pid, product.model_dump_json()))


def settings_for(db):
    return json.loads(db.execute("SELECT payload FROM commerce_settings WHERE id=1").fetchone()[0])


def products_for(db, include_archived=False):
    where = '' if include_archived else " WHERE NOT EXISTS (SELECT 1 FROM studio_archives a WHERE a.kind='product' AND a.entity_id=p.id)"
    return [json.loads(row[0]) for row in db.execute("SELECT payload FROM commerce_products p" + where + " ORDER BY p.rowid")]


def opening(settings, day):
    for override in settings["overrides"]:
        if override["date"] == day.isoformat():
            return override if override["enabled"] else None
    row = next(r for r in settings["weekly"] if r["day"] == day.weekday())
    return row if row["enabled"] else None


def seat_rows(db, day, exclude=""):
    return db.execute("""SELECT s.* FROM commerce_seats s JOIN commerce_orders o ON o.id=s.order_id
        WHERE s.date=? AND o.id<>? AND (o.status='paid' OR
        (o.status IN ('creating','pending','payment_uncertain') AND o.hold_until>?))""", (day, exclude, time.time())).fetchall()


def remaining_seats(db, settings, day, start, end, exclude="", extra=()):
    rows = list(seat_rows(db, day, exclude)) + list(extra)
    return min(settings["capacity"] - sum(r["guests"] for r in rows if r["date"] == day and r["start"] < slot + 30 and r["end"] > slot) for slot in range(start, end, 30))


def stock_held(db, product_id, exclude=""):
    return db.execute("""SELECT coalesce(sum(s.quantity),0) FROM commerce_stock s JOIN commerce_orders o ON o.id=s.order_id
        WHERE s.product_id=? AND o.id<>? AND (o.status IN ('manual_pending','manual_confirmed','manual_preparing','manual_ready') OR (o.status IN ('creating','pending','payment_uncertain') AND o.hold_until>?))""", (product_id, exclude, time.time())).fetchone()[0]


PUBLIC_SALES_ENABLED = os.getenv("STUDIO_ONLINE_SALES", "0") == "1"

def commerce_ready(settings):
    return PUBLIC_SALES_ENABLED and settings["enabled"] and settings["tax_mode"] != "unconfirmed" and gateway.configured


def quote_cart(db, cart: Cart):
    settings = settings_for(db)
    if not commerce_ready(settings):
        fail("checkout_not_open")
    catalog = {p["id"]: p for p in products_for(db)}
    lines, extra_seats, extra_stock = [], [], {}
    for item in cart.items:
        product = catalog.get(item.product_id)
        if not product or not product["active"] or product["price_cents"] is None:
            fail("product_unavailable")
        booking = item.booking
        price = product["price_cents"]
        if product["kind"] == "experience":
            if not booking or item.quantity != 1:
                fail("choose_visit_time", 422)
            now = now_local()
            hours = opening(settings, booking.date)
            if not now.date() <= booking.date <= now.date() + timedelta(days=90) or not hours:
                fail("slot_unavailable")
            start, end = minutes(booking.start), minutes(booking.end)
            instant = datetime.combine(booking.date, datetime.min.time(), tzinfo=TORONTO) + timedelta(minutes=start)
            if instant <= now + timedelta(minutes=settings["notice_minutes"]):
                fail("slot_unavailable")
            if start < minutes(hours["start"]) or end > minutes(hours["end"]):
                fail("slot_unavailable")
            if product["id"] == "hourly":
                if end - start < 60:
                    fail("minimum_one_hour", 422)
                amount = int((Decimal(price) * (end - start) * booking.guests / 60).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            else:
                if end != minutes(hours["end"]) or booking.guests != (2 if product["id"] == "pair" else 1):
                    fail("invalid_day_pass", 422)
                amount = price
            if remaining_seats(db, settings, str(booking.date), start, end, extra=extra_seats) < booking.guests:
                fail("slot_unavailable")
            extra_seats.append(dict(date=str(booking.date), start=start, end=end, guests=booking.guests))
        else:
            if booking:
                fail("invalid_product_booking", 422)
            requested = item.quantity + extra_stock.get(product["id"], 0)
            if requested > product["stock"] - stock_held(db, product["id"]):
                fail("stock_unavailable")
            extra_stock[product["id"]] = requested
            amount = price * item.quantity
        lines.append({**item.model_dump(mode="json"), "zh": product["zh"], "en": product["en"],
                      "image": product["image"], "kind": product["kind"], "unit_cents": price, "total_cents": amount})
    subtotal = sum(row["total_cents"] for row in lines)
    tax = int((Decimal(subtotal) * Decimal(settings["tax_bps"]) / 10000).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) if settings["tax_mode"] == "additional" else 0
    total = subtotal + tax
    cny = int((Decimal(total) * Decimal(settings["fx_cny_per_cad"])).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if cny < 1 or cny > 2000000:
        fail("order_amount_limit", 422)
    result = dict(lines=lines, subtotal_cents=subtotal, tax_cents=tax, total_cents=total, cny_fen=cny,
                  fx_cny_per_cad=settings["fx_cny_per_cad"], tax_mode=settings["tax_mode"], tax_bps=settings["tax_bps"],
                  currency="CAD", payment_currency="CNY", settings_version=settings["version"])
    result["quote_id"] = digest(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return result


def order_view(row, admin=False):
    result = {key: row[key] for key in ("id", "created_at", "status", "expires_at", "hold_until", "paid_at", "fulfillment", "version")}
    result["quote"] = json.loads(row["quote"])
    if result["quote"].get("mode") == "manual":
        result["customer"] = json.loads(row["customer"])
    if row["status"] in PENDING and row["expires_at"] > time.time():
        result.update(payment_url=row["payment_url"], qr_url=row["qr_url"])
    if admin:
        result.update(customer=json.loads(row["customer"]), staff_note=row["staff_note"], provider_id=row["provider_id"], trade_id=row["trade_id"])
    return result


def authorize(row, access_key):
    if not row or not access_key or len(access_key) != 64 or not hmac.compare_digest(row["access_hash"], digest(access_key)):
        fail("order_not_found", 404)


def amount_matches(value, expected):
    try:
        amount = Decimal(str(value)) * 100
        return amount.is_finite() and amount == Decimal(expected)
    except (ValueError, InvalidOperation):
        return False


def query_matches(row, data):
    quote = json.loads(row["quote"])
    for key in ("trade_order_id", "out_trade_order"):
        if data.get(key) and str(data[key]) != row["id"]:
            return False
    if data.get("appid") and str(data["appid"]) != gateway.app_id:
        return False
    amount = data.get("total_fee", data.get("total_amount"))
    if amount is not None and not amount_matches(amount, quote["cny_fen"]):
        return False
    if row["provider_id"] and data.get("open_order_id") and str(data["open_order_id"]) != row["provider_id"]:
        return False
    return True


def settle(order_id, trade_id, source):
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM commerce_orders WHERE id=?", (order_id,)).fetchone()
        if not row:
            fail("order_not_found", 404)
        if json.loads(row['quote']).get('mode') == 'manual':
            fail('manual_order_has_no_gateway_payment')
        if row["trade_id"] and row["trade_id"] != trade_id:
            fail("payment_identity_mismatch")
        duplicate = db.execute("SELECT id FROM commerce_orders WHERE trade_id=? AND id<>?", (trade_id, order_id)).fetchone()
        if duplicate:
            fail("payment_identity_mismatch")
        if row["status"] in ("paid", "paid_needs_review", "refunded"):
            return
        settings = settings_for(db)
        seats = db.execute("SELECT * FROM commerce_seats WHERE order_id=?", (order_id,)).fetchall()
        stocks = db.execute("SELECT * FROM commerce_stock WHERE order_id=?", (order_id,)).fetchall()
        # Previously placed orders still settle against their retained inventory.
        catalog = {p["id"]: p for p in products_for(db, include_archived=True)}
        extra, can_fulfill = [], True
        for seat in seats:
            if remaining_seats(db, settings, seat["date"], seat["start"], seat["end"], order_id, extra) < seat["guests"]:
                can_fulfill = False
            # An expired payment cannot create a reservation in the past.
            start = datetime.fromisoformat(seat["date"] + "T" + clock(seat["start"])).replace(tzinfo=TORONTO)
            if start <= now_local():
                can_fulfill = False
            extra.append(seat)
        for stock in stocks:
            p = catalog.get(stock["product_id"])
            if not p or p["stock"] - stock_held(db, p["id"], order_id) < stock["quantity"]:
                can_fulfill = False
        if can_fulfill:
            for stock in stocks:
                p = catalog[stock["product_id"]]
                p["stock"] -= stock["quantity"]
                p["version"] += 1
                db.execute("UPDATE commerce_products SET payload=? WHERE id=?", (json.dumps(p, ensure_ascii=False), p["id"]))
        state = "paid" if can_fulfill else "paid_needs_review"
        db.execute("UPDATE commerce_orders SET status=?,fulfillment=?,trade_id=?,paid_at=?,updated_at=?,version=version+1 WHERE id=?",
                   (state, "confirmed" if can_fulfill else "review_required", trade_id, time.time(), time.time(), order_id))
        audit(db, order_id, state, detail=source)


def reconcile(order_id, force=False):
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM commerce_orders WHERE id=?", (order_id,)).fetchone()
        if not row or row["status"] not in (*PENDING, "expired") or (not force and row["last_check"] > time.time() - 6):
            return
        db.execute("UPDATE commerce_orders SET last_check=? WHERE id=?", (time.time(), order_id))
    try:
        data = gateway.query(order_id)
        if query_matches(row, data) and data.get("status") == "OD":
            # Callback is the fallback when the provider query omits amount/trade ID.
            trade = str(data.get("open_order_id") or data.get("transaction_id") or "")
            if trade and data.get("total_fee", data.get("total_amount")) is not None:
                settle(order_id, trade, "gateway_query")
    except PaymentUnavailable:
        pass
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute("SELECT * FROM commerce_orders WHERE id=?", (order_id,)).fetchone()
        if current["status"] in PENDING and current["hold_until"] <= time.time():
            db.execute("UPDATE commerce_orders SET status='expired',updated_at=?,version=version+1 WHERE id=?", (time.time(), order_id))
            audit(db, order_id, "expired")


async def reconciliation_loop():
    while True:
        await asyncio.sleep(15)
        with database() as db:
            ids = [row[0] for row in db.execute("SELECT id FROM commerce_orders WHERE status IN ('creating','pending','payment_uncertain','expired') AND created_at>? AND last_check<? ORDER BY last_check LIMIT 20", (time.time() - 600, time.time() - 14))]
        for order_id in ids:
            try:
                await asyncio.to_thread(reconcile, order_id)
            except Exception:
                # A bad order must not stop the reconciler for everyone else.
                import logging
                logging.getLogger(__name__).exception("Studio reconciliation failed: %s", order_id)


def register(app, admin_actor):
    @app.get("/studio-api/catalog")
    def catalog():
        with database() as db:
            settings = settings_for(db)
            products = products_for(db)
            for p in products:
                p["available_stock"] = max(0, p["stock"] - stock_held(db, p["id"])) if p["kind"] == "physical" else None
        return {"products": products, "settings": settings, "checkout_ready": commerce_ready(settings), "payment_configured": gateway.configured}

    @app.get("/studio-api/availability")
    def availability(date: date, plan: Literal["hourly", "day", "pair"] = "hourly", guests: int = 1, duration: int = 120):
        if not 1 <= guests <= 100 or duration < 60 or duration > 1380 or duration % 30:
            fail("invalid_selection", 422)
        if plan != "hourly":
            guests = 2 if plan == "pair" else 1
        with database() as db:
            settings = settings_for(db)
            hours = opening(settings, date)
            now = now_local()
            product = next((p for p in products_for(db) if p["id"] == plan), None)
            if not product or not product["active"]:
                return {"date": str(date), "slots": [], "reason": "closed", "timezone": "America/Toronto"}
            if not commerce_ready(settings) or not settings["capacity"]:
                return {"date": str(date), "slots": [], "reason": "not_open", "timezone": "America/Toronto"}
            if not hours or not now.date() <= date <= now.date() + timedelta(days=90):
                return {"date": str(date), "slots": [], "reason": "closed", "timezone": "America/Toronto"}
            slots = []
            for start in range(minutes(hours["start"]), minutes(hours["end"]), 30):
                end = start + duration if plan == "hourly" else minutes(hours["end"])
                instant = datetime.combine(date, datetime.min.time(), tzinfo=TORONTO) + timedelta(minutes=start)
                if end > minutes(hours["end"]) or instant <= now + timedelta(minutes=settings["notice_minutes"]):
                    continue
                remaining = max(0, remaining_seats(db, settings, str(date), start, end))
                slots.append({"start": clock(start), "end": clock(end), "remaining": remaining, "available": remaining >= guests})
        return {"date": str(date), "slots": slots, "reason": "open", "timezone": "America/Toronto"}

    @app.post("/studio-api/cart/quote")
    def quote(payload: Cart):
        if not PUBLIC_SALES_ENABLED: fail("shop_paused", 409)
        with database() as db:
            return quote_cart(db, payload)

    @app.post("/studio-api/orders", status_code=201)
    def create_order(payload: Checkout, request: Request, idempotency_key: Annotated[str, Header()]):
        try:
            uuid.UUID(idempotency_key)
        except ValueError:
            fail("invalid_request_id", 422)
        hashed = digest(payload.model_dump_json())
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM commerce_orders WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing:
                authorize(existing, payload.access_key)
                if existing["payload_hash"] != hashed:
                    fail("request_changed")
                return order_view(existing)
            if not PUBLIC_SALES_ENABLED: fail("shop_paused", 409)
            quoted = quote_cart(db, payload)
            if quoted["quote_id"] != payload.quote_id:
                fail("price_changed")
            client = digest(request.client.host if request.client else "unknown")
            bucket = int(time.time()) // 3600
            counter = db.execute("SELECT count FROM commerce_limits WHERE client=? AND bucket=?", (client, bucket)).fetchone()
            if counter and counter[0] >= 12:
                fail("too_many_orders", 429)
            db.execute("DELETE FROM commerce_limits WHERE bucket<?", (bucket - 1,))
            db.execute("INSERT INTO commerce_limits VALUES(?,?,1) ON CONFLICT(client,bucket) DO UPDATE SET count=count+1", (client, bucket))
            order_id = "PS" + uuid.uuid4().hex[:24].upper()
            now = time.time()
            customer = payload.model_dump(exclude={"items", "access_key", "quote_id", "website"})
            db.execute("""INSERT INTO commerce_orders(id,created_at,updated_at,status,access_hash,idempotency_key,payload_hash,customer,quote,expires_at,hold_until)
                VALUES(?,?,?,'creating',?,?,?,?,?,?,?)""", (order_id, now, now, digest(payload.access_key), idempotency_key, hashed, json.dumps(customer, ensure_ascii=False), json.dumps(quoted, ensure_ascii=False), now + 300, now + 390))
            for line in payload.items:
                if line.booking:
                    b = line.booking
                    db.execute("INSERT INTO commerce_seats VALUES(?,?,?,?,?)", (order_id, str(b.date), minutes(b.start), minutes(b.end), b.guests))
                else:
                    db.execute("INSERT INTO commerce_stock VALUES(?,?,?)", (order_id, line.product_id, line.quantity))
            audit(db, order_id, "created_and_held")
        # Never hold a database write lock during a network request.
        try:
            payment = gateway.create(order_id, quoted["cny_fen"])
            with database() as db:
                db.execute("UPDATE commerce_orders SET payment_url=?,qr_url=?,provider_id=?,status=CASE WHEN status='creating' THEN 'pending' ELSE status END,updated_at=? WHERE id=?", (payment["payment_url"], payment["qr_url"], payment["provider_id"], time.time(), order_id))
                audit(db, order_id, "cashier_created")
        except PaymentUnavailable as exc:
            with database() as db:
                state = "failed" if isinstance(exc, PaymentRejected) else "payment_uncertain"
                db.execute("UPDATE commerce_orders SET status=?,updated_at=? WHERE id=? AND status='creating'", (state, time.time(), order_id))
                audit(db, order_id, state)
        with database() as db:
            return order_view(db.execute("SELECT * FROM commerce_orders WHERE id=?", (order_id,)).fetchone())

    @app.get("/studio-api/orders/{order_id}")
    def read_order(order_id: str, x_order_key: Annotated[str | None, Header()] = None):
        with database() as db:
            row = db.execute("SELECT * FROM commerce_orders WHERE id=?", (order_id,)).fetchone()
            if row and row['status'] == 'manual_deleted':
                fail('order_not_found', 404)
            authorize(row, x_order_key)
        if row["created_at"] > time.time() - 600:
            reconcile(order_id)
        with database() as db:
            return order_view(db.execute("SELECT * FROM commerce_orders WHERE id=?", (order_id,)).fetchone())

    @app.post("/studio-api/payments/hupijiao/notify", response_class=PlainTextResponse)
    async def notify(request: Request):
        raw = await request.body()
        if len(raw) > 16000:
            return PlainTextResponse("fail", status_code=413)
        try:
            pairs = parse_qsl(raw.decode("utf-8"), keep_blank_values=True, max_num_fields=60)
            params = dict(pairs)
            if len(params) != len(pairs) or not gateway.verify_callback(params):
                return PlainTextResponse("fail", status_code=400)
            order_id = params.get("trade_order_id", "")
            trade = params.get("transaction_id") or params.get("open_order_id")
            with database() as db:
                row = db.execute("SELECT * FROM commerce_orders WHERE id=?", (order_id,)).fetchone()
            if not row or not trade or not amount_matches(params.get("total_fee"), json.loads(row["quote"])["cny_fen"]):
                return PlainTextResponse("fail", status_code=400)
            data = await asyncio.to_thread(gateway.query, order_id)
            if not query_matches(row, data):
                return PlainTextResponse("fail", status_code=400)
            # Use the same stable provider identity for polling and callbacks.
            verified_trade = str(data.get("open_order_id") or data.get("transaction_id") or trade)
            if params.get("open_order_id") and data.get("open_order_id") and str(params["open_order_id"]) != str(data["open_order_id"]):
                return PlainTextResponse("fail", status_code=400)
            if params.get("transaction_id") and data.get("transaction_id") and str(params["transaction_id"]) != str(data["transaction_id"]):
                return PlainTextResponse("fail", status_code=400)
            if params.get("status") == "OD" and data.get("status") == "OD":
                await asyncio.to_thread(settle, order_id, verified_trade, "signed_callback_and_query")
            elif params.get("status") == "CD" and data.get("status") == "CD":
                with database() as db:
                    db.execute("BEGIN IMMEDIATE")
                    current = db.execute("SELECT status FROM commerce_orders WHERE id=?", (order_id,)).fetchone()
                    if current["status"] in ("paid", "paid_needs_review"):
                        db.execute("UPDATE commerce_orders SET status='refunded',fulfillment='refunded',updated_at=?,version=version+1 WHERE id=?", (time.time(), order_id))
                        audit(db, order_id, "provider_refund_confirmed")
            else:
                return PlainTextResponse("fail", status_code=409)
            return PlainTextResponse("success")
        except (ValueError, PaymentUnavailable, HTTPException):
            return PlainTextResponse("fail", status_code=503)

    @app.get("/studio-api/manage/commerce")
    def manage(_actor: str = Depends(admin_actor)):
        with database() as db:
            return {"settings": settings_for(db), "products": products_for(db), "payment_configured": gateway.configured}

    @app.put("/studio-api/manage/schedule")
    def save_settings(payload: Settings, actor: str = Depends(admin_actor)):
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            old = settings_for(db)
            if payload.version != old["version"]:
                fail("version_conflict")
            value = payload.model_dump(mode="json")
            # Lowering capacity cannot invalidate already sold or held seats.
            days = [r[0] for r in db.execute("SELECT DISTINCT date FROM commerce_seats WHERE date>=?", (str(now_local().date()),))]
            for day in days:
                rows = seat_rows(db, day)
                for row in rows:
                    if remaining_seats(db, value, day, row["start"], row["end"]) < 0:
                        fail("capacity_below_reservations")
            value["version"] += 1
            db.execute("UPDATE commerce_settings SET payload=? WHERE id=1", (json.dumps(value, ensure_ascii=False),))
            audit(db, "settings", "schedule_and_prices_updated", actor, json.dumps({"before": old, "after": value}, ensure_ascii=False))
        return value

    @app.put("/studio-api/manage/products/{product_id}")
    def save_product(product_id: str, payload: Product, actor: str = Depends(admin_actor)):
        if product_id != payload.id:
            fail("invalid_product", 422)
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM commerce_products WHERE id=?", (product_id,)).fetchone()
            import admin_archives
            if admin_archives.archived(db, 'product', product_id):
                fail('product_unavailable', 409)
            if row:
                old = json.loads(row[0])
                if old["version"] != payload.version:
                    fail("version_conflict")
                if old["kind"] != payload.kind:
                    fail("invalid_product", 422)
            elif payload.version != 1:
                fail("version_conflict")
            if payload.kind == "physical" and payload.stock < stock_held(db, product_id):
                fail("stock_below_holds")
            import shop_catalog
            shop_catalog.validate_product_category(db, payload)
            value = payload.model_dump()
            value["version"] = payload.version + 1
            db.execute("INSERT INTO commerce_products VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload", (product_id, json.dumps(value, ensure_ascii=False)))
            audit(db, product_id, "product_updated", actor, json.dumps({"before": json.loads(row[0]) if row else None, "after": value}, ensure_ascii=False))
        return value

    @app.get("/studio-api/manage/orders")
    def list_orders(_actor: str = Depends(admin_actor), page: int = 1, status: str = "all", search: str = "", day: date | None = None, kind: str = "all", day_kind: str = "visit", fulfillment: str = "all"):
        if not 1 <= page <= 10000 or len(search) > 120 or status not in {"all", *PENDING, "paid", "received", "paid_needs_review", "expired", "failed", "refunded"} or kind not in {"all", "visit", "pickup"} or day_kind not in {"visit", "created", "paid"} or fulfillment not in {"all", "confirmed", "completed"}:
            fail("invalid_page", 422)
        clauses, params = [], []
        if status == "received":
            clauses.append("o.status IN ('paid','paid_needs_review')")
        elif status != "all":
            clauses.append("o.status=?"); params.append(status)
        if search.strip():
            clauses.append("(o.id LIKE ? OR json_extract(o.customer,'$.name') LIKE ? OR json_extract(o.customer,'$.contact') LIKE ?)")
            params.extend(["%" + search.strip() + "%"] * 3)
        if day:
            if day_kind == "visit":
                clauses.append("EXISTS (SELECT 1 FROM commerce_seats s WHERE s.order_id=o.id AND s.date=?)"); params.append(str(day))
            else:
                start = datetime.combine(day, datetime.min.time(), tzinfo=TORONTO)
                finish = start + timedelta(days=1)
                column = {"created": "o.created_at", "paid": "o.paid_at"}[day_kind]
                clauses.append(f"{column}>=? AND {column}<?")
                params.extend([start.timestamp(), finish.timestamp()])
        if fulfillment != "all":
            clauses.append("o.fulfillment=?"); params.append(fulfillment)
        if kind == "visit":
            clauses.append("EXISTS (SELECT 1 FROM commerce_seats s WHERE s.order_id=o.id)")
        if kind == "pickup":
            clauses.append("EXISTS (SELECT 1 FROM commerce_stock s WHERE s.order_id=o.id)")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with database() as db:
            rows = db.execute("SELECT o.* FROM commerce_orders o" + where + " ORDER BY o.created_at DESC,o.id DESC LIMIT 30 OFFSET ?", (*params, (page - 1) * 30)).fetchall()
            total = db.execute("SELECT count(*) FROM commerce_orders o" + where, params).fetchone()[0]
        return {"items": [order_view(row, True) for row in rows], "total": total}

    @app.get("/studio-api/manage/overview")
    def overview(_actor: str = Depends(admin_actor), day: date | None = None):
        selected = day or now_local().date()
        start = datetime.combine(selected, datetime.min.time(), tzinfo=TORONTO)
        finish = start + timedelta(days=1)
        week_end = selected + timedelta(days=7)
        with database() as db:
            settings = settings_for(db)
            totals = db.execute("""SELECT
              count(CASE WHEN created_at>=? AND created_at<? THEN 1 END) AS orders_today,
              count(CASE WHEN status='paid_needs_review' THEN 1 END) AS needs_review,
              count(CASE WHEN status='paid' AND fulfillment='confirmed' THEN 1 END) AS awaiting_fulfillment,
              coalesce(sum(CASE WHEN paid_at>=? AND paid_at<? AND status IN ('paid','paid_needs_review')
                THEN CAST(json_extract(quote,'$.cny_fen') AS INTEGER) ELSE 0 END),0) AS received_cny_fen
              FROM commerce_orders""", (start.timestamp(), finish.timestamp(), start.timestamp(), finish.timestamp())).fetchone()
            bookings = db.execute("""SELECT s.*,o.status,o.fulfillment,json_extract(o.customer,'$.name') AS name
              FROM commerce_seats s JOIN commerce_orders o ON o.id=s.order_id
              WHERE s.date>=? AND s.date<? AND (o.status='paid' OR
                (o.status IN ('creating','pending','payment_uncertain') AND o.hold_until>?))
              ORDER BY s.date,s.start,o.created_at""", (str(selected), str(week_end), time.time())).fetchall()
            days = []
            for offset in range(7):
                value = selected + timedelta(days=offset)
                hours = opening(settings, value)
                entries = [{"order_id": r["order_id"], "name": r["name"], "start": clock(r["start"]), "end": clock(r["end"]), "guests": r["guests"], "status": r["status"], "fulfillment": r["fulfillment"]} for r in bookings if r["date"] == str(value)]
                days.append({"date": str(value), "hours": hours, "entries": entries})
            today_guests = sum(r["guests"] for r in bookings if r["date"] == str(selected) and r["status"] == "paid")
            recent = db.execute("SELECT * FROM commerce_orders ORDER BY created_at DESC,id DESC LIMIT 5").fetchall()
            products = products_for(db)
        return {"date": str(selected), "metrics": {**dict(totals), "guests_today": today_guests}, "days": days,
                "recent_orders": [order_view(row, True) for row in recent], "catalog": {"published": sum(p["active"] for p in products), "drafts": sum(not p["active"] for p in products), "low_stock": sum(p["active"] and p["kind"] == "physical" and p["stock"] <= 3 for p in products)},
                "checkout_ready": commerce_ready(settings), "payment_configured": gateway.configured, "timezone": "America/Toronto"}

    @app.get("/studio-api/manage/orders/{order_id}")
    def order_detail(order_id: str, _actor: str = Depends(admin_actor)):
        with database() as db:
            row = db.execute("SELECT * FROM commerce_orders WHERE id=?", (order_id,)).fetchone()
            if not row:
                fail("order_not_found", 404)
            events = db.execute("SELECT id,created_at,event,actor,detail FROM commerce_events WHERE order_id=? ORDER BY created_at DESC,id DESC LIMIT 100", (order_id,)).fetchall()
        return {**order_view(row, True), "events": [dict(r) for r in events]}

    @app.get("/studio-api/manage/activity")
    def activity(_actor: str = Depends(admin_actor), page: int = 1):
        if not 1 <= page <= 10000:
            fail("invalid_page", 422)
        with database() as db:
            total = db.execute("SELECT count(*) FROM commerce_events").fetchone()[0]
            rows = db.execute("SELECT * FROM commerce_events ORDER BY created_at DESC,id DESC LIMIT 30 OFFSET ?", ((page - 1) * 30,)).fetchall()
        return {"items": [dict(r) for r in rows], "total": total}

    @app.patch("/studio-api/manage/orders/{order_id}")
    def fulfill(order_id: str, payload: Fulfillment, actor: str = Depends(admin_actor)):
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM commerce_orders WHERE id=?", (order_id,)).fetchone()
            if not row:
                fail("order_not_found", 404)
            if row["version"] != payload.version:
                fail("version_conflict")
            if payload.completed and row["status"] != "paid":
                fail("order_not_paid")
            fulfillment = ("completed" if payload.completed else "confirmed") if row["status"] == "paid" else row["fulfillment"]
            db.execute("UPDATE commerce_orders SET fulfillment=?,staff_note=?,version=version+1,updated_at=? WHERE id=?", (fulfillment, payload.staff_note, time.time(), order_id))
            audit(db, order_id, "fulfillment_updated", actor, payload.staff_note)
            return order_view(db.execute("SELECT * FROM commerce_orders WHERE id=?", (order_id,)).fetchone(), True)
