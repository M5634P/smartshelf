"""SAP Business One Webhook Client – Holt Produktdaten via Celonis Make Webhook und synct nach Supabase."""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("smartshelf-sap")

# Webhook URLs aus Umgebungsvariablen
SAP_ALL_PRODUCTS_URL = os.getenv("SAP_ALL_PRODUCTS_URL", "")
SAP_SINGLE_PRODUCT_URL = os.getenv("SAP_SINGLE_PRODUCT_URL", "")


def _map_sap_to_product(sap_item: dict) -> dict:
    """Mappt SAP Business One Felder auf unser Produkt-Schema."""
    return {
        "prod_id": sap_item.get("ItemCode", ""),
        "prod_name": sap_item.get("ItemName", ""),
        "supplier_name": sap_item.get("Mainsupplier") or "",
        "supplier_email": "",
        "min_qty": int(float(sap_item.get("MinInventory", 0))),
        "reorder_qty": int(float(sap_item.get("DesiredInventory", 0))),
        "unit": "Stk",
        "sap_stock": int(float(sap_item.get("QuantityOnStock", 0))),
        "sap_ordered_from_vendors": int(float(sap_item.get("QuantityOrderedFromVendors", 0))),
        "sap_ordered_by_customers": int(float(sap_item.get("QuantityOrderedByCustomers", 0))),
    }


def sync_sap_to_supabase() -> int:
    """Holt alle Produkte vom SAP Webhook und schreibt sie in Supabase (UPSERT).

    Lokale Felder (supplier_email, min_qty, reorder_qty) werden NUR bei neuen
    Produkten gesetzt. Bei bestehenden Produkten werden nur SAP-Felder aktualisiert,
    damit lokale Änderungen erhalten bleiben.
    """
    from server.supabase_client import supabase

    try:
        log.info("SAP Sync: Hole alle Produkte vom Webhook...")
        resp = requests.get(SAP_ALL_PRODUCTS_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("value", [])
        log.info("SAP Sync: %d Produkte vom Webhook erhalten", len(items))

        # Bestehende Produkte aus Supabase holen (für lokale Felder)
        existing_resp = supabase.table("products").select("prod_id").execute()
        existing_ids = {row["prod_id"] for row in existing_resp.data}

        count = 0
        for sap_item in items:
            mapped = _map_sap_to_product(sap_item)
            prod_id = mapped["prod_id"]
            if not prod_id:
                continue

            if prod_id in existing_ids:
                # Nur SAP-Felder updaten, lokale Felder (email, min, reorder) behalten
                supabase.table("products").update({
                    "prod_name": mapped["prod_name"],
                    "supplier_name": mapped["supplier_name"],
                    "sap_stock": mapped["sap_stock"],
                    "sap_ordered_from_vendors": mapped["sap_ordered_from_vendors"],
                    "sap_ordered_by_customers": mapped["sap_ordered_by_customers"],
                }).eq("prod_id", prod_id).execute()
            else:
                # Neues Produkt: alle Felder setzen
                supabase.table("products").insert(mapped).execute()

            count += 1

        log.info("SAP Sync: %d Produkte in Supabase geschrieben", count)
        return count

    except Exception as e:
        log.error("SAP Sync Fehler: %s", e)
        raise
