"""Tests für SmartShelf Flask API-Endpunkte."""

import json
import pytest
from tests.conftest import mock_supabase, mock_sendgrid, mock_sap


# ── Hilfsfunktion ────────────────────────────────────────────────────────────

SAMPLE_PRODUCT = {
    "prod_id": "013880",
    "prod_name": "Rolle",
    "min_qty": 3,
    "reorder_qty": 10,
    "sap_stock": 5,
    "supplier_email": "test@example.com",
    "supplier_name": "Test Lieferant",
    "active": True,
    "unit": "Stk",
}


# ── Health & Dashboard ───────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json["status"] == "OK"

    def test_root_returns_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "SmartShelf API" in resp.json["info"]


class TestDashboard:
    def test_dashboard_returns_products_orders_scans(self, client):
        mock_supabase.get_all_products.return_value = [SAMPLE_PRODUCT]
        mock_supabase.get_all_orders.return_value = []
        mock_supabase.get_recent_scans.return_value = []

        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json
        assert "products" in data
        assert "orders" in data
        assert "scans" in data
        assert len(data["products"]) == 1


# ── Scan Endpoint ────────────────────────────────────────────────────────────

class TestScan:
    def test_scan_missing_json(self, client):
        resp = client.post("/scan", content_type="application/json", data="")
        assert resp.status_code == 400

    def test_scan_missing_fields(self, client):
        resp = client.post("/scan", json={"shelf_id": "S1"})
        assert resp.status_code == 400
        assert "Fehlende Felder" in resp.json["error"]

    def test_scan_product_not_found(self, client):
        mock_supabase.get_product.return_value = None
        resp = client.post("/scan", json={
            "shelf_id": "SHELF-1", "prod_id": "UNKNOWN", "count": 5
        })
        assert resp.status_code == 404

    def test_scan_stock_ok_no_order(self, client):
        """Bestand über min_qty → keine Bestellung."""
        mock_supabase.get_product.return_value = {**SAMPLE_PRODUCT, "min_qty": 3}
        resp = client.post("/scan", json={
            "shelf_id": "SHELF-1", "prod_id": "013880", "count": 5
        })
        assert resp.status_code == 200
        assert resp.json["action"] == "none"
        mock_supabase.create_order.assert_not_called()

    def test_scan_stock_critical_triggers_order(self, client):
        """Bestand <= min_qty → Bestellung wird ausgelöst."""
        mock_supabase.get_product.return_value = {**SAMPLE_PRODUCT, "min_qty": 3}
        mock_supabase.has_pending_order.return_value = False

        resp = client.post("/scan", json={
            "shelf_id": "SHELF-1", "prod_id": "013880", "count": 3
        })
        assert resp.json["action"] == "order_triggered"
        mock_supabase.create_order.assert_called_once_with("013880", 10)
        mock_sendgrid.send_order_mail.assert_called_once()

    def test_scan_stock_zero_triggers_order(self, client):
        """Bestand 0 bei min_qty 0 → Bestellung (0 <= 0)."""
        mock_supabase.get_product.return_value = {**SAMPLE_PRODUCT, "min_qty": 0, "reorder_qty": 5}
        mock_supabase.has_pending_order.return_value = False

        resp = client.post("/scan", json={
            "shelf_id": "SHELF-1", "prod_id": "013880", "count": 0
        })
        assert resp.json["action"] == "order_triggered"
        mock_supabase.create_order.assert_called_once_with("013880", 5)

    def test_scan_no_duplicate_order(self, client):
        """Offene Bestellung existiert → keine zweite Bestellung."""
        mock_supabase.get_product.return_value = {**SAMPLE_PRODUCT, "min_qty": 3}
        mock_supabase.has_pending_order.return_value = True

        resp = client.post("/scan", json={
            "shelf_id": "SHELF-1", "prod_id": "013880", "count": 1
        })
        assert resp.status_code == 200
        assert resp.json["action"] == "none"
        assert "bereits offen" in resp.json["info"]
        mock_supabase.create_order.assert_not_called()

    def test_scan_logs_to_scan_log(self, client):
        """Jeder Scan wird in scan_log geschrieben."""
        mock_supabase.get_product.return_value = SAMPLE_PRODUCT
        client.post("/scan", json={
            "shelf_id": "SHELF-1", "prod_id": "013880", "count": 5
        })
        mock_supabase.log_scan.assert_called_once_with("SHELF-1", "013880", 5)


# ── Wareneingang (Order Complete) ────────────────────────────────────────────

class TestWareneingang:
    def test_complete_order_missing_fields(self, client):
        resp = client.post("/api/order/complete", json={"prod_id": "013880"})
        assert resp.status_code == 400

    def test_complete_order_not_found(self, client):
        mock_supabase.complete_order.return_value = None
        resp = client.post("/api/order/complete", json={
            "prod_id": "013880", "received_qty": 10
        })
        assert resp.status_code == 404

    def test_complete_order_updates_stock(self, client):
        """Wareneingang: sap_stock wird um received_qty erhöht."""
        mock_supabase.complete_order.return_value = {"prod_id": "013880", "status": "DELIVERED"}
        mock_supabase.get_product.return_value = {**SAMPLE_PRODUCT, "sap_stock": 2}

        resp = client.post("/api/order/complete", json={
            "prod_id": "013880", "received_qty": 10
        })
        assert resp.status_code == 200
        assert resp.json["status"] == "OK"
        # sap_stock sollte von 2 auf 12 gesetzt werden
        mock_supabase.update_product.assert_called_with("013880", {"sap_stock": 12})

    def test_complete_order_logs_wareneingang(self, client):
        """Wareneingang wird im scan_log protokolliert."""
        mock_supabase.complete_order.return_value = {"prod_id": "013880", "status": "DELIVERED"}
        mock_supabase.get_product.return_value = {**SAMPLE_PRODUCT, "sap_stock": 0}

        client.post("/api/order/complete", json={
            "prod_id": "013880", "received_qty": 5
        })
        mock_supabase.log_scan.assert_called_with("WARENEINGANG", "013880", 5)


# ── Product Update ───────────────────────────────────────────────────────────

class TestProductUpdate:
    def test_update_product_allowed_fields(self, client):
        mock_supabase.update_product.return_value = SAMPLE_PRODUCT
        resp = client.put("/api/product/013880", json={
            "min_qty": 5, "reorder_qty": 20
        })
        assert resp.status_code == 200
        mock_supabase.update_product.assert_called_once_with(
            "013880", {"min_qty": 5, "reorder_qty": 20}
        )

    def test_update_product_filters_disallowed_fields(self, client):
        """Nicht erlaubte Felder werden ignoriert."""
        mock_supabase.update_product.return_value = SAMPLE_PRODUCT
        resp = client.put("/api/product/013880", json={
            "min_qty": 5, "hack_field": "evil"
        })
        assert resp.status_code == 200
        mock_supabase.update_product.assert_called_once_with(
            "013880", {"min_qty": 5}
        )

    def test_update_product_no_valid_fields(self, client):
        resp = client.put("/api/product/013880", json={
            "hack_field": "evil"
        })
        assert resp.status_code == 400

    def test_update_product_not_found(self, client):
        mock_supabase.update_product.return_value = None
        resp = client.put("/api/product/013880", json={"min_qty": 5})
        assert resp.status_code == 404


# ── Path Traversal Schutz ────────────────────────────────────────────────────

class TestPathTraversal:
    def test_history_file_rejects_path_traversal(self, client):
        """Path Traversal mit '..' im Dateinamen wird abgelehnt."""
        resp = client.get("/api/camera/history/..secret.jpg")
        assert resp.status_code == 400

    def test_history_file_rejects_backslash(self, client):
        resp = client.get("/api/camera/history/..\\..\\etc\\passwd")
        assert resp.status_code == 400

    def test_history_file_rejects_dotdot(self, client):
        resp = client.get("/api/camera/history/..passwd")
        assert resp.status_code == 400

    def test_history_file_nonexistent(self, client):
        resp = client.get("/api/camera/history/20260101_120000.jpg")
        assert resp.status_code == 404


# ── Camera Endpoints ─────────────────────────────────────────────────────────

class TestCamera:
    def test_camera_upload_no_image(self, client):
        resp = client.post("/api/camera", json={})
        assert resp.status_code == 400

    def test_camera_get_no_image(self, client):
        # Reset camera frame
        from server.server import _camera_frame
        _camera_frame["image"] = None
        resp = client.get("/api/camera")
        assert resp.status_code == 404

    def test_storage_toggle(self, client):
        resp = client.post("/api/camera/storage", json={"enabled": False})
        assert resp.status_code == 200
        assert resp.json["enabled"] is False

        resp = client.post("/api/camera/storage", json={"enabled": True})
        assert resp.json["enabled"] is True

    def test_storage_status(self, client):
        resp = client.get("/api/camera/storage")
        assert resp.status_code == 200
        assert "enabled" in resp.json


# ── SAP Sync ─────────────────────────────────────────────────────────────────

class TestSAPSync:
    def test_sync_success(self, client):
        mock_sap.sync_sap_to_supabase.return_value = 5
        resp = client.post("/api/products/sync")
        assert resp.status_code == 200
        assert resp.json["count"] == 5

    def test_sync_error(self, client):
        mock_sap.sync_sap_to_supabase.side_effect = Exception("SAP unreachable")
        resp = client.post("/api/products/sync")
        assert resp.status_code == 500
        mock_sap.sync_sap_to_supabase.side_effect = None
