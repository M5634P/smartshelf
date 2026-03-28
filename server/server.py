"""SmartShelf Flask Server – Empfängt Scan-Daten, prüft Schwellwerte, löst Bestellungen aus."""

import base64
import io
import logging
import os
import secrets
import time
from pathlib import Path

from flask import Flask, request, jsonify, Response, send_file
from flask_socketio import SocketIO
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

from server.supabase_client import get_product, get_all_products, update_product, has_pending_order, create_order, log_scan, get_all_orders, get_recent_scans, complete_order
from server.sap_client import sync_sap_to_supabase
from server.sendgrid_notifier import send_order_mail

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("smartshelf-server")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB Upload-Limit

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS, async_mode="threading")

# Letztes Kamerabild vom Pi (in-memory)
_camera_frame = {"image": None, "detections": 0, "timestamp": None}

# Ordner für gespeicherte Kamerabilder
CAPTURES_DIR = Path(__file__).resolve().parent / "captures"
CAPTURES_DIR.mkdir(exist_ok=True)

# Flag: Bildspeicherung aktiv/inaktiv
_storage_enabled = True


@app.route("/scan", methods=["POST"])
def scan():
    """
    Empfängt Scan-Daten vom Pi.

    Erwartet JSON: {shelf_id, prod_id, count}
    Antwortet mit: {status: OK|NOK, action: none|order_triggered}
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "NOK", "error": "Kein JSON erhalten"}), 400

    shelf_id = data.get("shelf_id")
    prod_id = data.get("prod_id")
    count = data.get("count")

    if not all([shelf_id, prod_id, count is not None]):
        return jsonify({"status": "NOK", "error": "Fehlende Felder"}), 400

    log.info("Scan empfangen: shelf=%s, prod=%s, count=%d", shelf_id, prod_id, count)

    # Scan loggen
    try:
        log_scan(shelf_id, prod_id, count)
    except Exception as e:
        log.error("Scan-Log Fehler: %s", e)

    # WebSocket: Dashboard-Daten an alle Clients pushen
    try:
        socketio.emit("scan_update", {
            "shelf_id": shelf_id, "prod_id": prod_id, "count": count,
        })
        _push_dashboard()
    except Exception as e:
        log.error("WebSocket Push Fehler: %s", e)

    # Produkt aus Supabase holen
    product = get_product(prod_id)
    if not product:
        log.warning("Produkt %s nicht in Supabase gefunden", prod_id)
        return jsonify({"status": "NOK", "error": "Produkt nicht gefunden"}), 404

    min_qty = product["min_qty"]
    reorder_qty = product["reorder_qty"]

    # Schwellwert prüfen
    if count > min_qty:
        log.info("Bestand OK: %d > %d (min_qty)", count, min_qty)
        return jsonify({"status": "OK", "action": "none"})

    log.warning("Bestand kritisch: %d <= %d (min_qty) für %s", count, min_qty, prod_id)

    # Offene Bestellung prüfen
    if has_pending_order(prod_id):
        log.info("Offene Bestellung existiert bereits für %s", prod_id)
        return jsonify({"status": "OK", "action": "none", "info": "Bestellung bereits offen"})

    # Bestellung auslösen
    create_order(prod_id, reorder_qty)
    log.info("Bestellung erstellt: %s x %d", prod_id, reorder_qty)

    # E-Mail senden
    mail_sent = send_order_mail(product, reorder_qty)
    if mail_sent:
        log.info("Bestell-Mail gesendet für %s", prod_id)
    else:
        log.error("Bestell-Mail fehlgeschlagen für %s", prod_id)

    return jsonify({
        "status": "NOK",
        "action": "order_triggered",
        "mail_sent": mail_sent,
    })


@app.route("/health", methods=["GET"])
def health():
    """Health-Check Endpoint."""
    return jsonify({"status": "OK", "service": "smartshelf-server"})


@app.route("/", methods=["GET"])
def dashboard():
    """Redirect zur Vue.js Frontend-App."""
    return jsonify({"info": "SmartShelf API – Frontend läuft auf Port 3000", "frontend": "http://localhost:3000"})


@app.route("/api/dashboard", methods=["GET"])
def api_dashboard():
    """JSON-API für Dashboard-Daten."""
    products = get_all_products()
    orders = get_all_orders()
    scans = get_recent_scans(limit=50)
    return jsonify({
        "products": products,
        "orders": orders,
        "scans": scans,
    })


@app.route("/api/camera", methods=["POST"])
def api_camera_upload():
    """Empfängt annotiertes Kamerabild vom Pi (Base64 JPEG)."""
    data = request.get_json()
    if not data or "image" not in data:
        return jsonify({"status": "NOK", "error": "Kein Bild"}), 400
    _camera_frame["image"] = data["image"]
    _camera_frame["detections"] = data.get("detections", 0)
    _camera_frame["timestamp"] = time.time()

    # Bild auf Disk speichern (latest + Zeitstempel)
    if _storage_enabled:
        try:
            img_bytes = base64.b64decode(data["image"])
            # Immer latest.jpg überschreiben
            (CAPTURES_DIR / "latest.jpg").write_bytes(img_bytes)
            # Zusätzlich mit Zeitstempel speichern
            ts_str = time.strftime("%Y%m%d_%H%M%S")
            (CAPTURES_DIR / f"{ts_str}.jpg").write_bytes(img_bytes)
            # Alte Bilder aufräumen (max 100 behalten)
            saved = sorted(CAPTURES_DIR.glob("2*.jpg"), reverse=True)
            for old in saved[100:]:
                old.unlink()
        except Exception as e:
            log.error("Bild-Speicher Fehler: %s", e)

    log.info("Kamerabild empfangen & gespeichert (%d KB, %d Objekte)", len(data["image"]) // 1024, _camera_frame["detections"])

    # WebSocket: Kamerabild an alle Clients pushen
    try:
        socketio.emit("camera_update", {
            "image": _camera_frame["image"],
            "detections": _camera_frame["detections"],
            "timestamp": _camera_frame["timestamp"],
        })
    except Exception as e:
        log.error("WebSocket Kamera-Push Fehler: %s", e)

    return jsonify({"status": "OK"})


@app.route("/api/camera", methods=["GET"])
def api_camera_get():
    """Liefert das letzte Kamerabild als JSON (Base64)."""
    if _camera_frame["image"] is None:
        return jsonify({"status": "NOK", "error": "Kein Bild vorhanden"}), 404
    return jsonify({
        "image": _camera_frame["image"],
        "detections": _camera_frame["detections"],
        "timestamp": _camera_frame["timestamp"],
    })


@app.route("/api/camera/latest.jpg", methods=["GET"])
def api_camera_latest_image():
    """Liefert das letzte Kamerabild direkt als JPEG."""
    latest = CAPTURES_DIR / "latest.jpg"
    if not latest.exists():
        return jsonify({"status": "NOK", "error": "Kein Bild vorhanden"}), 404
    return send_file(str(latest), mimetype="image/jpeg")


@app.route("/api/camera/storage", methods=["GET"])
def api_camera_storage_status():
    """Gibt den aktuellen Speicher-Status zurück."""
    return jsonify({"enabled": _storage_enabled})


@app.route("/api/camera/storage", methods=["POST"])
def api_camera_storage_toggle():
    """Aktiviert/deaktiviert die Bildspeicherung."""
    global _storage_enabled
    data = request.get_json()
    if data and "enabled" in data:
        _storage_enabled = bool(data["enabled"])
    else:
        _storage_enabled = not _storage_enabled
    log.info("Bildspeicherung %s", "aktiviert" if _storage_enabled else "deaktiviert")
    return jsonify({"enabled": _storage_enabled})


@app.route("/api/camera/history", methods=["GET"])
def api_camera_history():
    """Liste der gespeicherten Kamerabilder."""
    saved = sorted(CAPTURES_DIR.glob("2*.jpg"), reverse=True)
    images = [{"filename": f.name, "timestamp": f.stem, "size": f.stat().st_size} for f in saved[:50]]
    return jsonify({"images": images, "count": len(images)})


@app.route("/api/camera/history/<filename>", methods=["GET"])
def api_camera_history_file(filename):
    """Liefert ein gespeichertes Kamerabild als JPEG."""
    # Path Traversal Schutz: Keine Pfad-Separatoren erlauben
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"status": "NOK", "error": "Ungültiger Dateiname"}), 400
    filepath = (CAPTURES_DIR / filename).resolve()
    if not filepath.is_relative_to(CAPTURES_DIR.resolve()):
        return jsonify({"status": "NOK", "error": "Zugriff verweigert"}), 403
    if not filepath.exists() or not filepath.suffix == ".jpg":
        return jsonify({"status": "NOK", "error": "Bild nicht gefunden"}), 404
    return send_file(str(filepath), mimetype="image/jpeg")


@app.route("/api/detect", methods=["POST"])
def api_detect():
    """
    Empfängt ein Raw-Bild vom Pi, führt die Detection-Pipeline aus.

    Akzeptiert:
      - multipart/form-data mit Feld 'image' (JPEG file)
      - JSON mit {'image': '<base64>'} (Base64-kodiertes JPEG)

    Ablauf:
      1. Bild speichern (raw)
      2. detect.py Pipeline ausführen
      3. Annotiertes Bild speichern + via WebSocket pushen
      4. Für jede Zone: Scan loggen, Schwellwert prüfen, ggf. Bestellung
    """
    from server.detect import detect_image

    # 1. Bild empfangen
    if request.content_type and 'multipart' in request.content_type:
        file = request.files.get('image')
        if not file:
            return jsonify({"status": "NOK", "error": "Kein Bild im Upload"}), 400
        img_bytes = file.read()
    else:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"status": "NOK", "error": "Kein Bild (JSON: {image: base64})"}), 400
        img_bytes = base64.b64decode(data['image'])

    # 2. Raw-Bild speichern
    ts_str = time.strftime("%Y%m%d_%H%M%S")
    raw_path = CAPTURES_DIR / f"{ts_str}_raw.jpg"
    raw_path.write_bytes(img_bytes)

    # 3. Detection-Pipeline
    try:
        pil_image = Image.open(io.BytesIO(img_bytes))
        annotated_path = str(CAPTURES_DIR / f"{ts_str}_detected.jpg")

        log.info("Detection gestartet...")
        results, _ = detect_image(output_path=annotated_path, image_pil=pil_image)
        log.info("Detection abgeschlossen: %d Zonen", len(results))
    except Exception as e:
        log.error("Detection Fehler: %s", e)
        return jsonify({"status": "NOK", "error": "Detection fehlgeschlagen"}), 500

    # 4. Annotiertes Bild als latest.jpg + Base64 für WebSocket
    detected_path = Path(annotated_path)
    if detected_path.exists():
        detected_bytes = detected_path.read_bytes()
        (CAPTURES_DIR / "latest.jpg").write_bytes(detected_bytes)
        b64_image = base64.b64encode(detected_bytes).decode("utf-8")
    else:
        b64_image = base64.b64encode(img_bytes).decode("utf-8")

    # 5. Ergebnisse verarbeiten: Scans loggen + Schwellwerte prüfen
    detection_results = []
    total_detections = 0
    for name, prod_id, count, zone, dets, color, method in results:
        if not prod_id:
            continue

        total_detections += count
        detection_results.append({
            "zone": name,
            "prod_id": prod_id,
            "count": count,
            "method": method,
        })

        # Scan loggen + sap_stock mit erkanntem Count aktualisieren
        try:
            log_scan("SHELF-1", prod_id, count)
            update_product(prod_id, {"sap_stock": count})
        except Exception as e:
            log.error("Scan-Log Fehler für %s: %s", prod_id, e)

        # Schwellwert prüfen
        product = get_product(prod_id)
        if not product:
            log.warning("Produkt %s nicht in DB, überspringe Schwellwert", prod_id)
            continue

        if product.get("active") is False:
            continue

        min_qty = product["min_qty"]
        if count <= min_qty:
            log.warning("Bestand niedrig: %s %d < %d", prod_id, count, min_qty)
            if not has_pending_order(prod_id):
                reorder_qty = product["reorder_qty"]
                create_order(prod_id, reorder_qty)
                log.info("Bestellung erstellt: %s x %d", prod_id, reorder_qty)
                send_order_mail(product, reorder_qty)

    # 6. Kamera-Frame updaten + WebSocket push
    _camera_frame["image"] = b64_image
    _camera_frame["detections"] = total_detections
    _camera_frame["timestamp"] = time.time()

    try:
        socketio.emit("camera_update", {
            "image": b64_image,
            "detections": total_detections,
            "timestamp": _camera_frame["timestamp"],
        })
        _push_dashboard()
    except Exception as e:
        log.error("WebSocket Push Fehler: %s", e)

    # Alte Bilder aufräumen (max 100)
    saved = sorted(CAPTURES_DIR.glob("2*_detected.jpg"), reverse=True)
    for old in saved[100:]:
        old.unlink()
    raw_files = sorted(CAPTURES_DIR.glob("2*_raw.jpg"), reverse=True)
    for old in raw_files[100:]:
        old.unlink()

    log.info("Detection komplett: %d Objekte in %d Zonen", total_detections, len(detection_results))
    return jsonify({
        "status": "OK",
        "detections": total_detections,
        "zones": detection_results,
        "timestamp": ts_str,
    })


@app.route("/api/product/<prod_id>", methods=["PUT"])
def api_update_product(prod_id):
    """Aktualisiert lokale Produktfelder (supplier_email, min_qty, reorder_qty)."""
    data = request.get_json()
    if not data:
        return jsonify({"status": "NOK", "error": "Kein JSON"}), 400

    # Nur erlaubte Felder durchlassen
    allowed = {"prod_name", "supplier_email", "supplier_name", "min_qty", "reorder_qty", "sap_stock", "sap_ordered_from_vendors", "sap_ordered_by_customers", "active"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"status": "NOK", "error": "Keine gültigen Felder"}), 400

    result = update_product(prod_id, updates)
    if result:
        log.info("Produkt %s aktualisiert: %s", prod_id, updates)
        _push_dashboard()
        return jsonify({"status": "OK", "product": result})
    return jsonify({"status": "NOK", "error": "Produkt nicht gefunden"}), 404


@app.route("/api/products/sync", methods=["POST"])
def api_sync_products():
    """SAP Webhook → Supabase Sync auslösen."""
    try:
        count = sync_sap_to_supabase()
        _push_dashboard()
        log.info("SAP Sync erfolgreich: %d Produkte", count)
        return jsonify({"status": "OK", "count": count})
    except Exception as e:
        log.error("SAP Sync Fehler: %s", e)
        return jsonify({"status": "NOK", "error": str(e)}), 500


@app.route("/api/order/complete", methods=["POST"])
def api_complete_order():
    """Schliesst eine offene Bestellung ab."""
    data = request.get_json()
    if not data:
        return jsonify({"status": "NOK", "error": "Kein JSON"}), 400

    prod_id = data.get("prod_id")
    received_qty = data.get("received_qty")

    if not prod_id or received_qty is None:
        return jsonify({"status": "NOK", "error": "prod_id und received_qty erforderlich"}), 400

    result = complete_order(prod_id, int(received_qty))
    if result:
        log.info("Bestellung abgeschlossen: %s, erhalten: %d", prod_id, int(received_qty))
        # Wareneingang loggen + sap_stock aufstocken
        try:
            qty = int(received_qty)
            product = get_product(prod_id)
            current_stock = product["sap_stock"] if product else 0
            new_stock = current_stock + qty
            update_product(prod_id, {"sap_stock": new_stock})
            log_scan("WARENEINGANG", prod_id, new_stock)
            log.info("Wareneingang: %s +%d → Bestand jetzt %d", prod_id, qty, new_stock)
        except Exception as e:
            log.error("Wareneingang-Fehler: %s", e)
        # WebSocket: Dashboard-Daten an alle Clients pushen
        try:
            _push_dashboard()
        except Exception as e:
            log.error("WebSocket Push Fehler: %s", e)
        return jsonify({"status": "OK", "order": result})
    return jsonify({"status": "NOK", "error": "Keine offene Bestellung gefunden"}), 404


def _push_dashboard():
    """Pusht aktuelle Dashboard-Daten an alle verbundenen WebSocket-Clients."""
    products = get_all_products()
    orders = get_all_orders()
    scans = get_recent_scans(limit=50)
    socketio.emit("dashboard_update", {
        "products": products,
        "orders": orders,
        "scans": scans,
    })
    log.info("WebSocket: Dashboard-Update gepusht")


@socketio.on("connect")
def handle_connect():
    log.info("WebSocket Client verbunden")
    # Sofort aktuelle Daten senden
    try:
        products = get_all_products()
        orders = get_all_orders()
        scans = get_recent_scans(limit=50)
        socketio.emit("dashboard_update", {
            "products": products,
            "orders": orders,
            "scans": scans,
        })
        if _camera_frame["image"]:
            socketio.emit("camera_update", _camera_frame)
    except Exception as e:
        log.error("WebSocket Connect Push Fehler: %s", e)


if __name__ == "__main__":
    log.info("SmartShelf Server gestartet auf Port 5001 (WebSocket aktiviert)")
    socketio.run(app, host="0.0.0.0", port=5001, debug=False, allow_unsafe_werkzeug=True)
