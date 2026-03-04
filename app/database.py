"""
SQLite wrapper for TechNova orders / products / customers.

The .db file is bundled inside the container at data/technova.db.
On first access it is copied to /tmp so SQLite can create WAL temp files
on the writable layer without touching the read-only image filesystem.
"""
from __future__ import annotations

import os
import shutil
import sqlite3

_BUNDLE_DB = os.path.join(os.path.dirname(__file__), "..", "data", "technova.db")
_TMP_DB = "/tmp/technova.db"


def _get_conn() -> sqlite3.Connection:
    if not os.path.exists(_TMP_DB):
        os.makedirs("/tmp", exist_ok=True)
        shutil.copy2(_BUNDLE_DB, _TMP_DB)
    con = sqlite3.connect(_TMP_DB)
    con.row_factory = sqlite3.Row
    return con


def _rows(cursor: sqlite3.Cursor) -> list[dict]:
    return [dict(r) for r in cursor.fetchall()]


class Database:
    # ── order lookups ─────────────────────────────────────────────────────────

    def get_order(self, order_id: str) -> dict | None:
        with _get_conn() as con:
            rows = _rows(
                con.execute(
                    """
                    SELECT  o.id, o.status, o.total_amount, o.tracking_number,
                            o.created_at, o.shipped_at, o.delivered_at,
                            c.name AS customer_name, c.email
                    FROM    orders o
                    JOIN    customers c ON c.id = o.customer_id
                    WHERE   o.id = ?
                    LIMIT 1
                    """,
                    (order_id.upper(),),
                )
            )
        return rows[0] if rows else None

    def get_orders_by_email(self, email: str) -> list[dict]:
        with _get_conn() as con:
            return _rows(
                con.execute(
                    """
                    SELECT  o.id, o.status, o.total_amount, o.tracking_number,
                            o.created_at, o.shipped_at, o.delivered_at
                    FROM    orders o
                    JOIN    customers c ON c.id = o.customer_id
                    WHERE   LOWER(c.email) = LOWER(?)
                    ORDER BY o.created_at DESC
                    LIMIT 10
                    """,
                    (email,),
                )
            )

    def get_order_items(self, order_id: str) -> list[dict]:
        with _get_conn() as con:
            return _rows(
                con.execute(
                    """
                    SELECT  p.name, oi.quantity, oi.unit_price
                    FROM    order_items oi
                    JOIN    products p ON p.id = oi.product_id
                    WHERE   oi.order_id = ?
                    """,
                    (order_id.upper(),),
                )
            )

    # ── product lookups ───────────────────────────────────────────────────────

    def search_products(self, name: str) -> list[dict]:
        with _get_conn() as con:
            return _rows(
                con.execute(
                    """
                    SELECT  id, name, category, price, stock_quantity, description
                    FROM    products
                    WHERE   LOWER(name) LIKE LOWER(?)
                    LIMIT 5
                    """,
                    (f"%{name}%",),
                )
            )
