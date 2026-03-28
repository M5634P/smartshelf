"""SmartShelf Pi Client – Kamera-Aufnahme → Server Detection Pipeline."""

import logging
import time
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("smartshelf-pi")

BASE_DIR = Path(__file__).resolve().parent.parent
CAPTURE_PATH = BASE_DIR / "captures" / "current.jpg"

# Server-Konfiguration
SERVER_URL = "http://100.76.0.111:5001"
SCAN_INTERVAL_SEC = 10


def capture_image(output_path: Path) -> bool:
    """Nimmt ein Foto mit der Pi Camera auf."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from picamera2 import Picamera2

        cam = Picamera2()
        cam.configure(cam.create_still_configuration(
            main={"size": (3280, 2464)}
        ))
        cam.start()
        time.sleep(1)
        cam.capture_file(str(output_path))
        cam.stop()
        cam.close()
        log.info("Foto aufgenommen: %s", output_path)
        return True
    except Exception as e:
        log.error("Kamera-Fehler: %s", e)
        return False


def send_to_server(image_path: Path) -> dict | None:
    """Sendet das Raw-Bild an den Server zur Detection."""
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{SERVER_URL}/api/detect",
                files={"image": ("frame.jpg", f, "image/jpeg")},
                timeout=120,  # Detection kann dauern
            )
        data = resp.json()

        if data.get("status") == "OK":
            log.info(
                "Detection OK: %d Objekte in %d Zonen",
                data.get("detections", 0),
                len(data.get("zones", [])),
            )
            for zone in data.get("zones", []):
                log.info(
                    "  %s (%s): %d [%s]",
                    zone["zone"], zone["prod_id"],
                    zone["count"], zone["method"],
                )
        else:
            log.error("Server-Fehler: %s", data.get("error", "Unbekannt"))

        return data
    except Exception as e:
        log.error("Verbindungsfehler: %s", e)
        return None


def main():
    """Hauptloop: Foto aufnehmen → an Server senden → warten → wiederholen."""
    log.info("SmartShelf Pi Client gestartet")
    log.info("Server: %s | Intervall: %ds", SERVER_URL, SCAN_INTERVAL_SEC)

    while True:
        try:
            if capture_image(CAPTURE_PATH):
                send_to_server(CAPTURE_PATH)
            else:
                log.warning("Kein Bild aufgenommen, überspringe Zyklus")
        except Exception as e:
            log.error("Fehler im Scan-Zyklus: %s", e)

        log.info("Nächster Scan in %d Sekunden...", SCAN_INTERVAL_SEC)
        time.sleep(SCAN_INTERVAL_SEC)


if __name__ == "__main__":
    main()
