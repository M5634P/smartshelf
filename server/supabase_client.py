"""Supabase Client – Produktdaten, Bestellstatus und Scan-Log."""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_url = os.getenv("SUPABASE_URL")
_key = os.getenv("SUPABASE_KEY")

if not _url or not _key:
    raise RuntimeError("SUPABASE_URL und SUPABASE_KEY müssen in .env gesetzt sein")

supabase: Client = create_client(_url, _key)


def get_product(prod_id: str) -> dict | None:
    """Holt Produktdaten aus der products-Tabelle."""
    resp = supabase.table("products").select("*").eq("prod_id", prod_id).execute()
    if resp.data:
        return resp.data[0]
    return None


def has_pending_order(prod_id: str) -> bool:
    """Prüft ob eine offene Bestellung (PENDING) für dieses Produkt existiert."""
    resp = (
        supabase.table("orders")
        .select("prod_id")
        .eq("prod_id", prod_id)
        .eq("status", "PENDING")
        .execute()
    )
    return len(resp.data) > 0


def create_order(prod_id: str, quantity: int) -> dict:
    """Erstellt eine neue Bestellung mit Status PENDING.

    Verwendet upsert, da orders.prod_id PRIMARY KEY ist (1 Zeile pro Produkt).
    Eine alte DELIVERED-Bestellung wird dabei durch die neue PENDING ersetzt.
    Doppelbestellungen werden durch has_pending_order() in server.py verhindert.
    """
    resp = (
        supabase.table("orders")
        .upsert({
            "prod_id": prod_id,
            "status": "PENDING",
            "quantity": quantity,
        })
        .execute()
    )
    return resp.data[0] if resp.data else {}


def log_scan(shelf_id: str, prod_id: str, count: int) -> None:
    """Schreibt einen Scan-Eintrag in die scan_log-Tabelle."""
    supabase.table("scan_log").insert({
        "shelf_id": shelf_id,
        "prod_id": prod_id,
        "count": count,
    }).execute()


def get_all_products() -> list[dict]:
    """Holt alle Produkte."""
    resp = supabase.table("products").select("*").execute()
    return resp.data


def get_all_orders() -> list[dict]:
    """Holt alle Bestellungen."""
    resp = supabase.table("orders").select("*").order("ordered_at", desc=True).execute()
    return resp.data


def get_recent_scans(limit: int = 50) -> list[dict]:
    """Holt die letzten Scans."""
    resp = supabase.table("scan_log").select("*").order("scanned_at", desc=True).limit(limit).execute()
    return resp.data


_ALLOWED_PRODUCT_FIELDS = {"prod_name", "supplier_email", "supplier_name", "min_qty", "reorder_qty", "sap_stock", "sap_ordered_from_vendors", "sap_ordered_by_customers", "active", "unit"}


def update_product(prod_id: str, updates: dict) -> dict | None:
    """Aktualisiert ein Produkt in der products-Tabelle."""
    safe_updates = {k: v for k, v in updates.items() if k in _ALLOWED_PRODUCT_FIELDS}
    if not safe_updates:
        return None
    resp = supabase.table("products").update(safe_updates).eq("prod_id", prod_id).execute()
    if resp.data:
        return resp.data[0]
    return None


def complete_order(prod_id: str, received_qty: int) -> dict | None:
    """Schliesst die offene Bestellung für ein Produkt ab mit der tatsächlich erhaltenen Menge."""
    resp = (
        supabase.table("orders")
        .update({"status": "DELIVERED", "quantity": received_qty})
        .eq("prod_id", prod_id)
        .eq("status", "PENDING")
        .execute()
    )
    if resp.data:
        return resp.data[0]
    return None
