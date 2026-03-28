"""Shared fixtures for SmartShelf tests."""

import sys
import types
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

# ── Mock heavy dependencies before importing server ──────────────────────────
# supabase_client, sap_client, sendgrid_notifier use env vars at import time.
# We stub them so tests don't need a real .env or network.


def _patch_server_deps():
    """Creates mock modules for supabase_client, sap_client, sendgrid_notifier."""
    mock_supabase = types.ModuleType("server.supabase_client")
    mock_supabase.get_product = MagicMock(return_value=None)
    mock_supabase.get_all_products = MagicMock(return_value=[])
    mock_supabase.update_product = MagicMock(return_value=None)
    mock_supabase.has_pending_order = MagicMock(return_value=False)
    mock_supabase.create_order = MagicMock(return_value={})
    mock_supabase.log_scan = MagicMock()
    mock_supabase.get_all_orders = MagicMock(return_value=[])
    mock_supabase.get_recent_scans = MagicMock(return_value=[])
    mock_supabase.complete_order = MagicMock(return_value=None)

    mock_sap = types.ModuleType("server.sap_client")
    mock_sap.sync_sap_to_supabase = MagicMock(return_value=0)

    mock_sendgrid = types.ModuleType("server.sendgrid_notifier")
    mock_sendgrid.send_order_mail = MagicMock(return_value=True)

    sys.modules["server.supabase_client"] = mock_supabase
    sys.modules["server.sap_client"] = mock_sap
    sys.modules["server.sendgrid_notifier"] = mock_sendgrid

    return mock_supabase, mock_sap, mock_sendgrid


mock_supabase, mock_sap, mock_sendgrid = _patch_server_deps()

from server.server import app, socketio


@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks between tests."""
    mock_supabase.get_product.reset_mock()
    mock_supabase.get_product.return_value = None
    mock_supabase.get_all_products.reset_mock()
    mock_supabase.get_all_products.return_value = []
    mock_supabase.update_product.reset_mock()
    mock_supabase.update_product.return_value = None
    mock_supabase.has_pending_order.reset_mock()
    mock_supabase.has_pending_order.return_value = False
    mock_supabase.create_order.reset_mock()
    mock_supabase.create_order.return_value = {"prod_id": "TEST", "status": "PENDING"}
    mock_supabase.log_scan.reset_mock()
    mock_supabase.get_all_orders.reset_mock()
    mock_supabase.get_all_orders.return_value = []
    mock_supabase.get_recent_scans.reset_mock()
    mock_supabase.get_recent_scans.return_value = []
    mock_supabase.complete_order.reset_mock()
    mock_supabase.complete_order.return_value = None
    mock_sendgrid.send_order_mail.reset_mock()
    mock_sendgrid.send_order_mail.return_value = True
    mock_sap.sync_sap_to_supabase.reset_mock()
    mock_sap.sync_sap_to_supabase.return_value = 0
