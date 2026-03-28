# SmartShelf – Projektdokumentation

**KI-gestützte Lagerüberwachung mit automatischer Nachbestellung**

Hackathon Baden 2026 | Data Unit AG

> **Kurzpräsentation:** Eine visuelle Übersicht des gesamten Prozesses in vier einfachen Schritten findet sich in der Datei [`4STEPS_Präsentation.pdf`](4STEPS_Präsentation.pdf).

---

## Aufgabenstellung der Challenge

In einem KMU gibt es Lagerbestände, die nicht systemtechnisch lagergeführt sind, sondern «nur» mit einer Sichtkontrolle überwacht werden. In der Challenge soll ein Lagergestell mittels Kamerabild und AI überwacht werden. Immer wenn die Kamera erkennt, dass ein Produkt kurz vor dem «Ausgehen» ist, soll in der Unternehmenssoftware (ERP) eine Bestellung beim Lieferanten des Produkts angelegt werden. Für den Hackathon-Use-Case reicht eine E-Mail-Bestellung mit CSV-Anhang.

### Gestellte Herausforderungen und unsere Lösungen

**1. Wie erkennt die Kamera, welche Produktnummer «hinter» der Bilderkennung liegt?**

Wir verwenden eine **zonenbasierte Erkennung**: Die Kamera hat eine feste Position und fotografiert immer dasselbe Regal. Für jede Regalzone sind feste Pixel-Koordinaten hinterlegt, die definieren, welches Produkt wo gelagert wird. Das Bild wird in diese Zonen gecroppt und jede Zone ist mit einer Produktnummer (Item Number) verknüpft. So weiss das System immer, welches Produkt es gerade analysiert – ganz ohne Barcodes oder QR-Codes.
→ *Siehe Kapitel 1 (Kernprinzip: Zonenbasierte Erkennung) und Kapitel 4.2 (detect.py – AI Detection Pipeline)*

**2. Wie wird erkannt, ob ein zur Neige gehendes Produkt nicht schon eine laufende Bestellung hat?**

Sobald eine Bestellung ausgelöst wird, erhält sie den Status **PENDING** in der Datenbank. Solange eine Bestellung auf PENDING steht, wird für dieses Produkt **keine weitere Bestellung** ausgelöst – auch wenn der Bestand weiterhin unter der Mindestmenge liegt. Erst wenn ein Mitarbeiter im Dashboard die Bestellung als eingegangen markiert (Status → DELIVERED), wird die Überwachung für dieses Produkt wieder aktiv.
→ *Siehe Kapitel 4.2 (Bestellzyklus: Blockierung & Freigabe)*

**3. Die Produktstammdaten (z.B. Produktnummer und Name des Lieferanten) – woher kommen sie?**

Die Produktstammdaten wurden einmalig über einen **Webhook** aus dem ERP synchronisiert und in unserer Supabase-Datenbank gespeichert. Die Werte (Item Numbers, Mindestmengen, Bestellmengen) wurden so angepasst, dass sie den tatsächlichen Produkten im Hackathon-Regal entsprechen. Jedes Produkt ist mit einer Lieferantennummer verknüpft, sodass der Server bei einer Bestellung automatisch den richtigen Lieferanten kontaktiert.
→ *Siehe Kapitel 4.2 (Webhook & Produktdaten) und Kapitel 4.4 (Datenbank – Tabelle products)*

---

## 1. Projektübersicht

SmartShelf ist ein IoT-System zur automatischen Inventurüberwachung. Eine Kamera auf einem Raspberry Pi 4 fotografiert alle 30 Sekunden ein Regal. Das Bild wird an den Server gesendet, wo KI-Modelle die Produkte in vordefinierten Zonen erkennen und zählen. Bei niedrigem Bestand wird automatisch eine Nachbestellung per E-Mail an den Lieferanten ausgelöst – ohne menschliche Interaktion. Ein Vue.js-Dashboard zeigt den Live-Status in Echtzeit.

### Kernprinzip: Zonenbasierte Erkennung

Die Kamera hat eine **feste Position** und fotografiert immer dasselbe Regal. Für jede Regalzone ist im System hinterlegt, **welches Produkt wo gelagert wird** (feste Pixel-Koordinaten). Das Gesamtbild wird in diese Zonen **gecroppt** (ausgeschnitten) und jeder Ausschnitt wird einzeln vom KI-Modell analysiert. So erkennt das System z.B.: *"Links oben: Produkt 013880 (Rolle), Bestand: 2 Stück"*. Dadurch werden **keine Barcodes oder QR-Codes** zur Produktidentifikation benötigt.

### Vier Erkennungsarten für verschiedene Lagerungsformen

Das Konzept von SmartShelf deckt vier verschiedene Lagerungsarten ab. **Die ersten zwei sind vollständig implementiert und funktionsfähig**, die letzten zwei sind konzeptionell ausgearbeitet und würden so integriert werden – sie sind aktuell noch nicht aktiv eingebaut, da die entsprechenden Sensoren im Hackathon nicht zur Verfügung standen.

#### Aktiv implementiert:

1. **Nebeneinander** – Produkte stehen nebeneinander in der Zone. Die KI erkennt und zählt jedes einzelne Objekt via Object Detection. Je nach Produkt kommt das Modell zum Einsatz, das beim Testen die besten Ergebnisse geliefert hat (z.B. Grounding DINO für Badetücher, Custom YOLO26n für Jasskarten).
2. **Übereinander (gestapelt)** – Produkte sind aufeinandergestapelt. Hier kommen je nach Produkt verschiedene Ansätze zum Einsatz: SAM2 + DINO für Segmentierung (z.B. Schokolade), oder Florence-2 + DINO als Hybrid (Caption-Zählung kombiniert mit Bounding Boxes).

#### Konzeptionell vorgesehen (noch nicht eingebaut):

3. **Hintereinander** – Produkte stehen hintereinander und verdecken sich gegenseitig. Hier ist das Konzept, dass ein **Mindestmengen-Schild** an einer definierten Stelle im Regal fixiert wird. Die Produkte werden davor gelagert. Sobald genug Produkte entnommen wurden und das Schild sichtbar wird, erkennt die KI das Schild und löst eine Bestellung aus. Es können sich noch Produkte hinter dem Schild befinden – das Schild markiert lediglich den Punkt der Mindestbestellmenge. Diese Erkennung ist noch nicht aktiv, da im Hackathon keine entsprechenden Schilder und Produkte zur Verfügung standen. Die Integration wäre technisch einfach umsetzbar, da die KI bereits auf Objekterkennung trainiert ist.
4. **In geschlossenen Kartons (nicht sichtbar)** – Für Produkte in Kartons, deren Inhalt nicht visuell erkennbar ist, ist das Konzept, **Loadcells (Wägezellen)** unter den Kartons zu platzieren. Diese wiegen grammgenau das Gesamtgewicht. In der Datenbank wird das Einzelgewicht des Produkts sowie das Kartongewicht hinterlegt. Daraus wird die aktuelle Stückzahl berechnet und bei Unterschreitung des Schwellwerts eine Bestellung ausgelöst. Diese Erkennung ist noch nicht eingebaut, da die Loadcell-Sensoren im Hackathon nicht vorhanden waren. Die Integration würde über eine zusätzliche API erfolgen, die die Gewichtsdaten an den Server sendet.

Durch diese vier Erkennungsarten ist das Konzept so ausgelegt, dass **jede denkbare Lagerungsform** abgedeckt wird und somit wirklich **keine menschliche Interaktion** mehr nötig ist – das System erkennt vollautomatisch den Bestand und löst bei Bedarf Bestellungen aus.

---

## 2. Systemarchitektur

Das System besteht aus **sechs Komponenten**, die über HTTP, WebSocket und E-Mail kommunizieren:

```
┌───────────────────────────┐                                  ┌──────────────────────────┐
│   SAP BUSINESS ONE (ERP)  │                                  │   SENDGRID (E-Mail)      │
│───────────────────────────│                                  │──────────────────────────│
│ Produktstammdaten         │                                  │ Bestell-Mail mit CSV     │
│ (Item Numbers, Lieferant) │                                  │ an Lieferanten senden    │
└─────────┬─────────────────┘                                  └──────────▲───────────────┘
          │ Webhook                                                       │ SMTP API
          ▼                                                               │
┌───────────────────────────┐                                              │
│   CELONIS MAKE (iPaaS)    │                                              │
│───────────────────────────│                                              │
│ Webhook empfangen &       │                                              │
│ JSON transformieren       │                                              │
└─────────┬─────────────────┘                                              │
          │ HTTP POST                                                      │
          ▼                                                                │
┌─────────────────────────────┐  HTTP   ┌──────────────────────────────────┤
│   RASPBERRY PI 4 (Edge)     │ ──────► │   PC / LAPTOP (Flask Server)     │
│─────────────────────────────│         │──────────────────────────────────│
│ 1. Foto aufnehmen (PiCam)  │         │ 1. Bild empfangen                │
│ 2. POST /api/detect (JPEG) │ ◄────── │ 2. Zonen croppen & KI-Analyse    │
│    via Tailscale VPN        │  JSON   │ 3. Schwellwerte prüfen           │
└─────────────────────────────┘         │ 4. Bestellung auslösen           │
                                        │ 5. SAP-Sync empfangen            │
                                        └──┬──────────────┬────────────────┘
                                           │              │
                              WebSocket    │              │ HTTPS
                             (Socket.IO)   │              ▼
                                           │   ┌──────────────────────────────┐
                                           │   │   SUPABASE (PostgreSQL)      │
                                           │   │──────────────────────────────│
                                           │   │ products  – Produktstamm     │
                                           │   │ orders    – Bestellungen     │
                                           │   │ scan_log  – Scan-Historie    │
                                           │   └──────────────────────────────┘
                                           ▼
                              ┌──────────────────────────────────┐
                              │   VUE.JS FRONTEND (Dashboard)    │
                              │──────────────────────────────────│
                              │ - Live-Kamerabild                │
                              │ - Bestandsübersicht              │
                              │ - Bestellstatus & Wareneingang   │
                              │ - Scan-Historie                  │
                              └──────────────────────────────────┘
```

### Kommunikationsfluss

1. **Pi → Server:** Alle 30 Sekunden ein Foto als JPEG via `POST /api/detect` (multipart/form-data)
2. **Server:** Bild in Zonen croppen → jede Zone einzeln durch KI-Modell analysieren → Counts ermitteln
3. **Server → Supabase:** Scan loggen, Produkt abfragen (`prod_id` → Item Number → Lieferantennummer, Mindestmenge, Bestellmenge), Schwellwert prüfen, `sap_stock` mit erkanntem Count aktualisieren
4. **Server → SendGrid:** Bei Unterschreitung des Mindestbestands: Lieferantennummer nachschlagen → automatische Bestell-Mail mit CSV-Anhang an den hinterlegten Lieferanten senden
5. **Server → Frontend:** Echtzeit-Updates via WebSocket (Socket.IO) für Dashboard, Scans, Kamerabild

### Detaillierter Prozessablauf

**A) SAP-Sync (einmalig / bei Bedarf):**
```
SAP B1              Celonis Make           Server                  Supabase
|                   |                      |                       |
|-- Webhook ------->|                      |                       |
|   (Produktdaten)  |-- HTTP POST -------->|                       |
|                   |   (JSON Array)       |-- sync_sap_to_supabase()
|                   |                      |-- UPSERT products --->|
|                   |                      |   (prod_id, name,     |
|                   |                      |    supplier, etc.)     |
```

**B) Scan-Zyklus (alle 30 Sekunden):**
```
Pi                  Server                  Supabase        SendGrid        Frontend
|                   |                       |               |               |
|-- POST /api/detect|                       |               |               |
|   (Raw JPEG)      |                       |               |               |
|                   |-- detect_image()      |               |               |
|                   |   (SAM2/DINO/Florence)|               |               |
|                   |                       |               |               |
|                   |-- Für jede Zone: ---->|               |               |
|                   |   log_scan()          |-- INSERT      |               |
|                   |   update_product()    |-- UPDATE      |               |
|                   |                       |   (sap_stock) |               |
|                   |                       |               |               |
|                   |-- count <= min_qty?-->|               |               |
|                   |   has_pending_order()?|-- SELECT      |               |
|                   |   create_order()      |-- INSERT      |               |
|                   |   send_order_mail() --|-------------->|               |
|                   |                       |               |-- E-Mail ---> Lieferant
|                   |                       |               |   (CSV-Anhang)|
|                   |-- WebSocket Push ---->|---------------|-------------->|
|                   |   camera_update       |               |               | Bild
|                   |   dashboard_update    |               |               | Daten
|<-- JSON Response -|                       |               |               |
```

**C) Wareneingang (manuell im Dashboard):**
```
Frontend            Server                  Supabase
|                   |                       |
|-- POST /api/order/complete -------------->|
|   {prod_id, received_qty}                 |
|                   |-- complete_order() -->|-- UPDATE orders (PENDING → DELIVERED)
|                   |-- get_product() ----->|-- SELECT products
|                   |-- update_product() -->|-- UPDATE products
|                   |   (sap_stock += qty)  |   (sap_stock = current + received)
|                   |-- log_scan() -------->|-- INSERT scan_log (WARENEINGANG)
|                   |-- WebSocket Push ---->|
|<-- dashboard_update -|                    |
```

---

## 3. Projektstruktur

```
smartshelf/
├── server/                        # Flask Backend (PC/Laptop)
│   ├── server.py                  # Flask + Socket.IO Server, REST-API Endpoints
│   ├── detect.py                  # AI Detection Pipeline (DINO + Florence-2 + SAM2)
│   ├── supabase_client.py         # Supabase Datenbankzugriff (CRUD)
│   ├── sap_client.py              # SAP Webhook Integration & Supabase-Sync
│   ├── sendgrid_notifier.py       # E-Mail-Versand mit CSV-Anhang
│   ├── captures/                  # Gespeicherte Kamerabilder (raw + annotiert)
│   └── __init__.py
│
├── pi/                            # Raspberry Pi Client (Edge)
│   ├── pi_client.py               # Hauptloop: Foto aufnehmen → an Server senden
│   ├── yolo_detector.py           # YOLO26n Objekterkennung (Edge-Inferenz)
│   ├── qr_reader.py               # QR-Code Erkennung (qrdet + pyzbar)
│   └── __init__.py
│
├── frontend/                      # Vue.js 3 Dashboard
│   ├── src/
│   │   ├── App.vue                # Root-Komponente, Socket.IO Init
│   │   ├── main.js                # App-Einstiegspunkt (Pinia, Router)
│   │   ├── router.js              # Vue Router (5 Seiten)
│   │   ├── stores/
│   │   │   └── dashboard.js       # Pinia Store (State, WebSocket, API-Calls)
│   │   ├── views/
│   │   │   ├── Dashboard.vue      # Hauptübersicht mit Stat-Cards + Live-Kamera
│   │   │   ├── Camera.vue         # Live-Kamerabild + Bildhistorie
│   │   │   ├── Products.vue       # Produktverwaltung (Inline-Bearbeitung)
│   │   │   ├── Orders.vue         # Bestellübersicht + Wareneingang
│   │   │   └── Scans.vue          # Scan-Verlauf mit Bestellstatus
│   │   ├── components/
│   │   │   ├── Navbar.vue         # Navigation + Verbindungsstatus
│   │   │   ├── StatCard.vue       # Statistik-Karte
│   │   │   └── ToastContainer.vue # Toast-Benachrichtigungen
│   │   └── assets/
│   │       └── style.css          # TailwindCSS 4 Styles + Custom Theme
│   ├── package.json
│   └── vite.config.js             # Vite Config mit Proxy auf Port 5001
│
├── .github/workflows/
│   └── deploy.yml                 # GitHub Actions: Auto-Deploy auf Pi via Tailscale
│
├── dataset_roboflow_kaggle/        # Roboflow Trainingsdaten & trainierte Modelle
│   └── My First Project-2/
│       ├── train/                 # Trainingsbilder + Labels
│       ├── valid/                 # Validierungsbilder + Labels
│       ├── test/                  # Testbilder + Labels
│       ├── data.yaml              # Roboflow Dataset-Konfiguration
│       ├── best (2).pt            # Custom-trainiertes YOLO26n Modell (bestes)
│       ├── last.pt                # Letzter Trainings-Checkpoint
│       ├── ergebnis.jpg           # Trainingsergebnis-Visualisierung
│       ├── ergebnis_last.jpg      # Trainingsergebnis (letzter Checkpoint)
│       └── README.roboflow.txt    # Roboflow Export-Info
│
├── doc_pictures/                  # Bilder für Dokumentation & Präsentation
│   ├── Grounding_Dino.jpeg        # Screenshot: Grounding DINO Erkennung
│   ├── Modeltraining.jpeg         # Screenshot: Custom Model Training Prozess
│   ├── segmentation_SAM2_chocolat.jpeg  # Screenshot: SAM2 Segmentierung (Schokolade)
│   ├── yolov26n_trained.jpeg      # Screenshot: YOLO26n Trainingsergebnis
│   └── yolov26n_trained_2.jpeg    # Screenshot: YOLO26n Trainingsergebnis (2)
│
├── supabase_setup.sql             # Datenbank-Setup-Script (SQL)
├── smartshelf.service             # systemd Service für Pi-Autostart
├── shelves.json                   # Regal-Konfiguration (Shelf-IDs ↔ Prod-IDs)
├── kaggle_training.ipynb          # Jupyter Notebook: YOLO26n Training auf Kaggle GPU
├── check_training.sh              # Bash-Script: Training-Fortschritt monitoren
├── tests/                         # pytest Test-Suite
│   ├── conftest.py                # Shared Fixtures, Mock-Setup
│   ├── test_api.py                # API-Endpunkt Tests (31 Tests)
│   └── test_sendgrid.py           # CSV-Generierung Tests
│
├── requirements_server.txt        # Python-Deps Server (Flask, Supabase, SendGrid)
├── requirements_pi.txt            # Python-Deps Pi (picamera2, requests)
├── .env.example                   # Umgebungsvariablen-Template
├── yolo26n.pt                     # YOLO26n Basis-Modell
├── SmartShelf_Architektur.docx    # Architektur-Diagramm (Word)
├── ZUSAMMENFASSUNG.md             # KI-Modell Zusammenfassung
└── README.md                      # Kurzanleitung
```

---

## 4. Komponenten im Detail

### 4.1 Raspberry Pi Client (`pi/`)

Der Raspberry Pi hat eine **einzige Aufgabe**: alle 30 Sekunden ein Foto mit der Kamera aufnehmen und an den Server senden. Die gesamte Intelligenz – Zonen-Cropping, KI-Analyse, Bestandsprüfung und Bestellauslösung – liegt auf dem Server.

#### `pi_client.py` – Hauptloop
- Läuft als Endlosschleife im konfigurierbaren Intervall (alle **30 Sekunden**)
- **Ablauf pro Zyklus:**
  1. Foto aufnehmen via `picamera2` (3280×2464 px)
  2. Bild als JPEG an Server senden (`POST /api/detect`, multipart/form-data)
  3. Timeout: 120 Sekunden (KI-Erkennung dauert je nach Hardware)
- Das ist alles – der Pi macht **ausschliesslich das Bild**. Der Server übernimmt den Rest.

#### `yolo_detector.py` – Edge-Inferenz (optional)
- YOLO26n Objekterkennung direkt auf dem Pi (CPU, 320px, Confidence 0.4)
- Kann für schnelle Vor-Erkennung auf dem Edge-Device eingesetzt werden
- Im aktuellen Setup wird die vollständige Erkennung serverseitig durchgeführt

#### `qr_reader.py` – QR-Code Erkennung (optional)
- QR-Code Detection via qrdet + pyzbar
- Kann zur Produktidentifikation alternativ zur zonenbasierten Erkennung eingesetzt werden

**Abhängigkeiten (`requirements_pi.txt`):**
```
picamera2>=0.3.12
requests>=2.31.0
```

**Systemd-Service (`smartshelf.service`):**
```ini
[Unit]
Description=SmartShelf Pi Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/smartshelf
ExecStart=/home/admin/smartshelf/venv/bin/python -m pi.pi_client
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=/home/admin/smartshelf

[Install]
WantedBy=multi-user.target
```

---

### 4.2 Flask Server (`server/`)

#### `server.py` – REST-API + WebSocket Server
Läuft auf Port **5001** mit Flask + Flask-SocketIO.

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/api/detect` | POST | Bild empfangen, KI-Detection, Scans loggen, Schwellwerte prüfen, Bestellungen auslösen |
| `/scan` | POST | Scan-Daten empfangen (JSON: shelf_id, prod_id, count) |
| `/health` | GET | Health-Check |
| `/api/dashboard` | GET | Dashboard-Daten (Produkte, Bestellungen, Scans) |
| `/api/camera` | POST | Kamerabild empfangen (Base64 JPEG) |
| `/api/camera` | GET | Letztes Kamerabild abrufen |
| `/api/camera/latest.jpg` | GET | Letztes Bild direkt als JPEG |
| `/api/camera/storage` | GET/POST | Bildspeicherung Status / Toggle |
| `/api/camera/history` | GET | Liste gespeicherter Bilder (max 50) |
| `/api/camera/history/<filename>` | GET | Einzelnes historisches Bild herunterladen |
| `/api/product/<prod_id>` | PUT | Produkt aktualisieren (alle Felder editierbar) |
| `/api/products/sync` | POST | SAP Webhook → Supabase Sync auslösen |
| `/api/order/complete` | POST | Bestellung abschliessen + Wareneingang buchen |

**WebSocket-Events (Socket.IO):**

| Event | Richtung | Daten | Beschreibung |
|-------|----------|-------|--------------|
| `dashboard_update` | Server → Client | `{products, orders, scans}` | Aktualisierte Dashboard-Daten |
| `camera_update` | Server → Client | `{image, detections, timestamp}` | Neues Kamerabild (Base64) |
| `scan_update` | Server → Client | `{shelf_id, prod_id, count}` | Toast-Benachrichtigung bei neuem Scan |

**Hauptprozess `/api/detect`:**
1. Bild empfangen (multipart oder Base64-JSON)
2. Raw-Bild speichern (`captures/{timestamp}_raw.jpg`)
3. KI-Detection-Pipeline ausführen (`detect.py`)
4. Annotiertes Bild speichern (`captures/{timestamp}_detected.jpg`)
5. Für jede erkannte Zone:
   - Scan in `scan_log` loggen
   - `sap_stock` mit erkanntem Count aktualisieren
   - Schwellwert prüfen: `count <= min_qty`?
   - Wenn ja UND keine offene Bestellung → Bestellung erstellen + E-Mail senden
6. Annotiertes Bild + Dashboard-Update via WebSocket an alle Clients pushen

**Bestelllogik:**
Über die `prod_id` (Item Number) werden alle verknüpften Daten aus Supabase abgerufen – Produktname, Mindestmenge (`min_qty`), Nachbestellmenge (`reorder_qty`), Lieferantennummer (`supplier_email`, `supplier_name`). Bei Unterschreitung des Mindestbestands schaut der Server die Lieferantennummer nach und sendet automatisch eine Bestell-Mail mit der hinterlegten Bestellmenge.

**Bestellzyklus (Blockierung & Freigabe):**
Sobald eine Bestellung ausgelöst wurde, wird sie mit dem Status **PENDING** in der Datenbank gespeichert. Ab diesem Zeitpunkt ist die Bestellung für dieses Produkt **blockiert** – es werden keine weiteren Bestellungen für dasselbe Produkt ausgelöst, auch wenn der Bestand weiterhin unter der Mindestmenge liegt. Dies verhindert doppelte Bestellungen.

Wenn die Lieferung eintrifft, kann ein Mitarbeiter im Dashboard auf **«Abschliessen»** klicken und die erhaltene Menge eingeben. Der Status wechselt auf **DELIVERED**, der Lagerbestand (`sap_stock`) wird um die erhaltene Menge aufgestockt. Ab diesem Moment wird der Bestand wieder regulär überwacht – falls er weiterhin unter der Mindestmenge liegt, wird erneut eine Bestellung ausgelöst.

**Webhook & Produktdaten:**
Die Produktstammdaten (Item Numbers, Produktnamen, SAP-Bestände) werden über einen Webhook aus SAP Business One (via Celonis Make) synchronisiert und in Supabase gespeichert. Beim Sync werden nur SAP-spezifische Felder aktualisiert – lokale Felder wie `min_qty`, `reorder_qty`, `supplier_email` und `active` bleiben erhalten. Die Werte wurden so angepasst, dass sie den tatsächlichen Produkten im Hackathon-Regal entsprechen. Jede Regalzone ist über die `prod_id` mit genau einem Produkt verknüpft.

**Lieferantenliste:** Für den Hackathon wurde eine eigene kleine Lieferantenliste erstellt. Als Lieferanten-E-Mails wurden die eigenen E-Mail-Adressen hinterlegt, um den vollständigen Bestellprozess end-to-end testen zu können.

**Optionale manuelle Freigabe:** Im aktuellen Setup läuft der Bestellprozess vollautomatisch. Für Produktionsumgebungen kann eine Kontrollfunktion eingebaut werden, bei der ein Mitarbeiter die Bestellung im Dashboard zuerst freigeben muss, bevor sie versendet wird.

**Bildspeicherung:**
- Bilder werden in `server/captures/` gespeichert (latest.jpg + Zeitstempel)
- Automatische Aufräumung: Max 100 Bilder behalten
- Speicherung kann vom Frontend aktiviert/deaktiviert werden

#### `detect.py` – AI Detection Pipeline (Serverseitig)

**Ablauf auf dem Server:**
1. Das Bild vom Pi wird empfangen
2. Anhand der **vordefinierten Zonen-Koordinaten** wird das Bild in einzelne Ausschnitte gecroppt – jede Zone entspricht einem Regalbereich, in dem ein bestimmtes Produkt gelagert wird
3. Jeder Ausschnitt wird **einzeln** durch das KI-Modell analysiert, das für dieses spezifische Produkt am besten funktioniert
4. Das Ergebnis (Anzahl erkannter Objekte) wird pro Zone zurückgegeben
5. Ein annotiertes Bild wird erzeugt mit farbigen Zonen-Rechtecken und Bounding Boxes

**Warum verschiedene Modelle pro Produkt?** Beim Testen haben wir festgestellt, dass nicht jedes KI-Modell jedes Produkt gleich gut erkennt. Deshalb wurde für jedes Produkt dasjenige Modell ausgewählt, das in unseren Tests die zuverlässigsten Ergebnisse geliefert hat:

| Produkt | Modell | Begründung |
|---------|--------|------------|
| **Badetuch (Rolle)** | Grounding DINO | Vortrainiertes Modell erkennt Handtücher zuverlässig via Text-Prompt |
| **Dymo Paper** | Grounding DINO | Karton-ähnliche Objekte werden gut erkannt |
| **Bostich Refill** | Grounding DINO | Einfache Kartonboxen, gut per Zero-Shot erkennbar |
| **Kopfhörer** | Grounding DINO | Elektronik-Produkte werden zuverlässig erkannt |
| **Schokolade** | SAM2 + DINO | Gestapelte Tafeln werden durch SAM2-Segmentierung einzeln getrennt |
| **Jasskarten** | yolov26n trained | Caption-Zählung kombiniert mit Bounding Boxes für beste Genauigkeit |
| **USB Plug, Audi/BMW Ersatzteil** | Grounding DINO | Manuell geführt – kein visuelles Erkennungsmodell zugewiesen |

**Eingesetzte Modelle:**
- **Grounding DINO** (`IDEA-Research/grounding-dino-tiny`): Zero-Shot Object Detection mit Text-Prompts – erkennt Objekte ohne eigenes Training, nur anhand einer Textbeschreibung. Schwellwert: 0.30, mit NMS-Filterung und Seitenverhältnis-Checks.
- **Florence-2** (`microsoft/Florence-2-base`): Caption-basiertes Zählen – beschreibt das Bild textlich und extrahiert daraus die Anzahl
- **SAM2** (`sam2_hiera_tiny.pt`): Segmentierung – trennt einzelne Objekte visuell voneinander, ideal für gestapelte Produkte. 1 Maske = 1 Objekt, mit Deduplizierung via IoU-Overlap.
- **Custom YOLO26n**: Eigens trainiertes Modell für Produkte, die von vortrainierten Modellen nicht erkannt werden

#### `supabase_client.py` – Datenbankzugriff
CRUD-Operationen auf drei Tabellen via Supabase Python SDK:
- `get_product()`, `get_all_products()`, `update_product()`
- `has_pending_order()`, `create_order()`, `complete_order()`
- `log_scan()`, `get_recent_scans()`

#### `sap_client.py` – SAP Webhook Integration
Synchronisiert Produktstammdaten aus SAP Business One (via Celonis Make Webhook) in Supabase:
- Mapping: ItemCode → prod_id, ItemName → prod_name, QuantityOnStock → sap_stock
- Numerische SAP-Werte werden mit `int(float(...))` konvertiert (SAP liefert "37.0" als String)
- Bestehende Produkte: Nur SAP-Felder aktualisieren, lokale Felder bleiben erhalten
- Neue Produkte: Mit Standardwerten anlegen

#### `sendgrid_notifier.py` – E-Mail-Versand
- Sendet HTML-Mail an den Lieferanten mit automatisch generiertem CSV-Anhang
- CSV enthält: Produkt-ID (Item Number), Produktname, Bestellmenge, Einheit, Zeitstempel
- Absender konfigurierbar via `FROM_EMAIL`
- **Ablauf:** Jedes Produkt in der Datenbank hat eine Lieferantennummer (E-Mail). Bei einer Bestellung schaut der Server diese nach und sendet die Mail mit den korrekten Bestellinformationen direkt an den jeweiligen Lieferanten.
- Im Hackathon-Setup wurden als Lieferanten-E-Mails die eigenen Adressen hinterlegt, um den Prozess zu testen

---

### 4.3 Frontend / Dashboard (`frontend/`)

Es wurde ein vollständiges **Dashboard** erstellt, das eine Übersicht über den gesamten Bestand, die Bestellungen und den Kamera-Feed bietet. Das Dashboard aktualisiert sich in Echtzeit über WebSocket.

Vue.js 3 SPA mit folgenden Technologien:
- **Build-Tool:** Vite 8 (Dev-Server auf Port 3000, Proxy auf 5001)
- **UI-Framework:** Vue 3 (Composition API + `<script setup>`)
- **Styling:** TailwindCSS 4
- **Icons:** Lucide Vue Next
- **State Management:** Pinia 3
- **Routing:** Vue Router 4 (5 Seiten)
- **Echtzeit:** Socket.IO Client

**Seiten:**

| Seite | Route | Beschreibung |
|-------|-------|-------------|
| Dashboard | `/` | Übersicht mit Stat-Cards (Produkte, Bestand OK/kritisch, offene Bestellungen), Live-Kamerabild, System-Status, kritische Produkte, letzte Scans mit Bestellstatus |
| Produkte | `/products` | Produkttabelle mit Inline-Bearbeitung aller Felder (Name, Lager, Min, Max/Soll, Lieferant, E-Mail), Aktiv/Inaktiv-Toggle, SAP-Sync Button. Aktive Produkte werden zuerst angezeigt. |
| Bestellungen | `/orders` | Offene (PENDING) und abgeschlossene (DELIVERED) Bestellungen, Wareneingang buchen mit Mengenangabe |
| Scans | `/scans` | Scan-Verlauf (letzte 50 Einträge) mit Zeitpunkt, Regal, Produkt, Anzahl, Min, Status (OK/Kritisch), Bestellstatus (Bestellt/Geliefert/–) |
| Kamera | `/camera` | Live-Kamerabild, Bildhistorie mit Download-Links, Speicher-Toggle |

**Pinia Store (`dashboard.js`):**
- Zentraler State für Produkte, Bestellungen, Scans, Kamerabild
- WebSocket-Verbindung mit automatischer Reconnection
- Computed Properties: `productMap` (prod_id → Produkt), `latestScanMap`, `stats` (ok/low/pending Zähler), `pendingOrders`, `deliveredOrders`
- API-Methoden: `fetchDashboard()`, `fetchCamera()`, `saveProduct()`, `syncSAP()`, `completeOrder()`, `toggleStorage()`
- Toast-Benachrichtigungen bei Scan-Updates und Aktionen

**Schwellwert-Logik:** Überall gilt: `count <= min_qty` = **Kritisch** (rot), `count > min_qty` = **OK** (grün). Dies betrifft alle Stat-Cards, Tabellen und Status-Badges konsistent über alle Seiten.

**Vite Konfiguration (`vite.config.js`):**
Alle API-Aufrufe (`/api/*`, `/scan`, `/health`) und WebSocket-Verbindungen (`/socket.io`) werden vom Vite Dev Server an den Flask-Server (Port 5001) weitergeleitet.

---

### 4.4 Datenbank (Supabase / PostgreSQL)

Drei Tabellen:

**`products`** – Produktstammdaten
| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `prod_id` | TEXT PK | SAP ItemCode (z.B. 0319.3771) |
| `prod_name` | TEXT | Produktname |
| `supplier_email` | TEXT | Lieferanten-E-Mail |
| `supplier_name` | TEXT | Lieferantenname |
| `min_qty` | INTEGER | Mindestbestand (Schwellwert für Bestellung) |
| `reorder_qty` | INTEGER | Nachbestellmenge (Max/Soll) |
| `unit` | TEXT | Einheit (Default: Stk) |
| `sap_stock` | INTEGER | Aktueller Lagerbestand (von KI-Erkennung aktualisiert) |
| `sap_ordered_from_vendors` | INTEGER | Offene Einkaufsbestellungen (SAP) |
| `sap_ordered_by_customers` | INTEGER | Offene Kundenbestellungen (SAP) |
| `active` | BOOLEAN | Produkt aktiv/inaktiv (deaktivierte lösen keine Bestellungen aus) |

**`orders`** – Bestellstatus
| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `prod_id` | TEXT PK | Produkt-ID |
| `status` | TEXT | PENDING oder DELIVERED |
| `ordered_at` | TIMESTAMPTZ | Bestellzeitpunkt |
| `quantity` | INTEGER | Bestellmenge |

**`scan_log`** – Scan-Verlauf
| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `id` | SERIAL PK | Auto-ID |
| `shelf_id` | TEXT | Regal-ID (SHELF-1) oder WARENEINGANG |
| `prod_id` | TEXT | Produkt-ID |
| `count` | INTEGER | Gezählte/erhaltene Menge |
| `scanned_at` | TIMESTAMPTZ | Scan-Zeitpunkt |

RLS ist aktiviert mit einer permissiven Policy für den `service_role` Key.

---

## 5. AI-Modelle

### 5.1 Custom Model Training

Für die präzise Erkennung der spezifischen Produkte im Regal wurden eigene KI-Modelle trainiert:

**Trainings-Workflow:**
1. **Datenerhebung:** Pro Produkt 50–100 Fotos aus verschiedenen Winkeln und Beleuchtungen aufgenommen
2. **Labeling auf Roboflow:** Bilder hochgeladen und manuell annotiert – jedes Produkt wird mit einer Bounding Box umrahmt und einer Klasse zugeordnet (z.B. "Jasskarte", "Schokolade")
3. **Training:** Über **200 Epochen** trainiert, bis das Modell eine **Präzision (mAP) von über 90%** erreicht hat
4. **Deployment:** Das fertig trainierte Modell wird lokal auf dem Server eingesetzt

**Warum Custom Training:** Da das Modell auf einem selbst erstellten Datensatz mit den echten Produkten im echten Regal trainiert wurde, erkennt es diese Produkte mit hoher Zuverlässigkeit. Neue Produkte können jederzeit einfach hinzugefügt werden, indem man Fotos macht, diese auf Roboflow labelt und das Modell neu trainiert.

### 5.2 Edge (Raspberry Pi): YOLO26n
- **Modell:** YOLO26n (Custom oder COCO-Fallback)
- **Inferenz:** CPU, 320px Bildgrösse, Confidence 0.4
- **Zweck:** Optionale schnelle Vor-Erkennung auf dem Edge-Device
- **Training:** Kaggle GPU, Jupyter Notebook (`kaggle_training.ipynb`)

### 5.3 Server: Hybrid Multi-Modell-Pipeline
Getestete Modelle und deren Status:

| Modell | Ergebnis | Status |
|--------|----------|--------|
| **Grounding DINO** (tiny) | Zero-Shot Object Detection mit Text-Prompts | ✅ Eingesetzt |
| **Florence-2** (base) | Caption-basiertes Zählen | ✅ Eingesetzt |
| **SAM 2** (hiera_tiny) | Mask-Segmentierung und Refinement | ✅ Eingesetzt |
| **YOLO26n** | Custom-trainiertes Modell | ✅ Eingesetzt |
| **SAM 3** | Braucht CUDA GPU, Checkpoint gesperrt | ❌ Nicht nutzbar |
| **OWLv2** | Schlechtere Ergebnisse als Hybrid | ❌ Verworfen |
| **Roboflow API** | Server-Fehler (500) | ❌ Nicht nutzbar |

### 5.4 Zonen-Konfiguration (9 Zonen, 3 Ebenen)

**Ebene 1 (oben):**
| Zone | Prod-ID | Methode | Prompt |
|------|---------|---------|--------|
| Rolle (Badetuch) | 013880 | DINO | "towel. rolled towel. fabric roll." |
| USB Plug | 013999 | none | – |
| Dymo Paper | 0319.3776 | DINO | "label printer box. DYMO box." |

**Ebene 2 (mitte):**
| Zone | Prod-ID | Methode |
|------|---------|---------|
| Audi Ersatzteil | 0319.3775 | none |
| BMW Ersatzteil | 0319.3774 | none |

**Ebene 3 (unten):**
| Zone | Prod-ID | Methode | Prompt |
|------|---------|---------|--------|
| Kopfhörer | 0319.3770 | DINO | "headphones. earphones. headset." |
| Bostich Refill | 0319.3772 | DINO | "cardboard box." |
| Schokolade | 0319.3771 | SAM2+DINO | "chocolate bar. flat package. candy bar." |
| Jasskarten | 0319.377098 | Florence+DINO | "small box. white box. package." |

### 5.5 Detection-Ergebnisse

| Zone | Erwartet | Erkannt | Status |
|------|----------|---------|--------|
| Rolle (Badetuch) | 2 | 2 | ✅ |
| USB Plug | 0 | 0 | ✅ |
| Dymo Paper | 1 | 1 | ✅ |
| Audi Ersatzteil | 0 | 0 | ✅ |
| BMW Ersatzteil | 0 | 0 | ✅ |
| Kopfhörer | 0 | 0 | ✅ |
| Bostich Refill | 1 | 1 | ✅ |
| Schokolade | 2 | 2 | ✅ |
| Jasskarten | 2 | 2 | ✅ |

**Alle 9/9 Counts korrekt.**

---

## 6. Geschäftslogik

### Schwellwert-Prüfung

```
Wenn erkannte_menge <= min_qty:
  → Status = "Kritisch" (rot)
  → Bestellung wird ausgelöst (falls keine offene existiert)
  → E-Mail an Lieferant mit CSV-Anhang

Wenn erkannte_menge > min_qty:
  → Status = "OK" (grün)
  → Keine Aktion
```

### Bestellmenge
Die Bestellmenge entspricht dem Feld `reorder_qty` (Max/Soll) des Produkts.

### Doppelbestellungs-Schutz
Pro Produkt kann nur **eine** offene Bestellung (Status `PENDING`) existieren. Solange eine Bestellung offen ist, wird keine zweite erstellt.

### Wareneingang
Beim Abschliessen einer Bestellung wird die erhaltene Menge zum aktuellen `sap_stock` **addiert**. Der nächste KI-Scan überschreibt `sap_stock` dann wieder mit dem tatsächlich erkannten Bestand.

### Aktiv/Inaktiv
Deaktivierte Produkte (`active = false`):
- Werden in der Produkttabelle ausgegraut angezeigt (am Ende der Liste)
- Lösen **keine** Bestellungen aus (auch wenn count <= min_qty)
- Werden weiterhin gescannt und im Scan-Log protokolliert

---

## 7. Aktueller Status & geplante Erweiterungen

### Was funktioniert

Das gesamte System ist **end-to-end funktionsfähig**: Der Pi macht ein Bild, der Server analysiert es zonenbasiert mit KI-Modellen, erkennt die Produkte, prüft die Schwellwerte, löst bei Bedarf automatisch eine Bestellung aus und sendet eine E-Mail an den Lieferanten. Das Frontend zeigt alles in Echtzeit an. Alle visuell erkennbaren Produkte (nebeneinander und übereinander gelagert) werden korrekt gezählt (9/9 Zonen korrekt).

### Was konzeptionell vorgesehen, aber noch nicht eingebaut ist

Die folgenden Erweiterungen sind **konzeptionell ausgearbeitet** und würden so integriert werden. Sie sind aktuell nicht aktiv, da die entsprechenden Sensoren und Hilfsmittel im Hackathon nicht zur Verfügung standen:

- **Hintereinander-Erkennung (Mindestmengen-Schild):** Physisches Schild im Regal markiert den Punkt der Mindestbestellmenge. Sobald es sichtbar wird, erkennt die KI es und löst eine Bestellung aus. (Siehe Abschnitt 1: Erkennungsart 3)
- **Loadcell-Erkennung (Kartons):** Wägezellen unter Kartons messen das Gewicht und berechnen die Stückzahl. (Siehe Abschnitt 1: Erkennungsart 4)
- **Menschenerkennung:** Da die eingesetzten KI-Modelle bereits auf Menschen trainiert sind, soll eine Personenerkennung integriert werden. Wenn jemand vor dem Regal steht, wird dieses Bild verworfen und erst das nächste Bild (ohne Person) für die Bestandsanalyse verwendet. So wird vermieden, dass die KI ein teilweise verdecktes Regal fälschlicherweise als „leer" interpretiert.
- **Drei-Bilder-Validierung:** Um die Zuverlässigkeit zu erhöhen, sollen zukünftig drei aufeinanderfolgende Bilder analysiert werden. Nur wenn alle drei dieselben Bestandswerte liefern, wird das Ergebnis akzeptiert. Dies verhindert fehlerhafte Bestellungen durch einmalige Fehlerkennungen (z.B. Lichtreflexionen oder vorübergehende Verdeckung).

### Skalierbarkeit

Das System ist so ausgelegt, dass es **einfach auf neue Produkte und verschiedene Branchen** erweitert werden kann:
1. Fotos vom neuen Produkt machen (50–100 Bilder)
2. Auf Roboflow labeln (Bounding Boxes zeichnen, Klasse zuordnen)
3. Modell neu trainieren (über 200 Epochen, bis >90% Präzision)
4. Zone im System definieren (Pixel-Koordinaten, Methode, Prompt)

Da die Modelle einfach selbst trainiert werden können, kann das System für verschiedenste Produktarten eingesetzt werden – überall dort, wo Lagerbestand automatisiert überwacht werden soll.

---

## 8. Sicherheit

### 8.1 Durchgeführte Sicherheitsanalyse

Es wurde ein umfassender Security-Audit auf dem gesamten Codebase durchgeführt. Dabei wurden Schwachstellen in den Kategorien **CRITICAL**, **HIGH**, **MEDIUM** und **LOW** identifiziert und behoben.

### 8.2 Behobene Schwachstellen

| Schwachstelle | Severity | Beschreibung | Massnahme |
|---------------|----------|--------------|-----------|
| **Hardcoded SECRET_KEY** | HIGH | Flask SECRET_KEY war als Klartext im Code (`"smartshelf-secret"`), ermöglicht Session-Fälschung | Dynamisch generiert via `secrets.token_hex(32)`, optional via Umgebungsvariable `FLASK_SECRET_KEY` konfigurierbar |
| **Wildcard CORS** | HIGH | `cors_allowed_origins="*"` erlaubte WebSocket-Verbindungen von jeder beliebigen Domain (Cross-Site WebSocket Hijacking) | Eingeschränkt auf explizit konfigurierte Origins via Umgebungsvariable `CORS_ORIGINS` (Default: `http://localhost:3000`) |
| **Path Traversal** | HIGH | Endpoint `/api/camera/history/<filename>` war anfällig für Directory Traversal (`../../etc/passwd`) – beliebige Dateien konnten gelesen werden | Dreifacher Schutz: (1) Pfad-Separatoren `/`, `\` und `..` im Dateinamen blockiert, (2) `Path.resolve()` + `is_relative_to()` Prüfung, (3) nur `.jpg` Dateien erlaubt |
| **Secrets im Quellcode** | HIGH | SAP Webhook-URLs mit eingebetteten Tokens waren direkt im Python-Code hartcodiert und damit im Git-Repository sichtbar | In Umgebungsvariablen verschoben (`SAP_ALL_PRODUCTS_URL`, `SAP_SINGLE_PRODUCT_URL` in `.env`) |
| **Hardcoded Dateipfade** | HIGH | SAM2-Modellpfad enthielt den vollen Benutzernamen (`/Users/michaelpeter/...`) | Durch Umgebungsvariable `SAM2_CHECKPOINT` mit relativem Fallback-Pfad ersetzt |
| **Error Information Disclosure** | HIGH | Python-Exceptions wurden direkt an den Client zurückgegeben und enthüllten interne Dateipfade und Bibliotheksversionen | Generische Fehlermeldungen an den Client, Details nur noch im Server-Log |
| **Kein Upload-Limit** | MEDIUM | Keine Begrenzung der Upload-Grösse – ein Angreifer konnte den Server-Speicher mit grossen Uploads erschöpfen (DoS) | `MAX_CONTENT_LENGTH = 50 MB` konfiguriert |
| **XSS in E-Mails** | MEDIUM | Produktnamen und Lieferantendaten wurden ohne Escaping in HTML-E-Mails eingebettet (Stored XSS) | Alle dynamischen Werte werden mit `html.escape()` behandelt bevor sie in den HTML-Body eingebettet werden |

### 8.3 Secrets Management

Alle sensiblen Daten sind in der `.env`-Datei gespeichert, die über `.gitignore` vom Repository ausgeschlossen ist:

- **Supabase Service-Role-Key** – Vollzugriff auf die Datenbank (umgeht Row Level Security)
- **SendGrid API-Key** – E-Mail-Versand
- **SAP Webhook-URLs** – Enthalten eingebettete Authentifizierungs-Tokens
- **Flask SECRET_KEY** – Session-Signierung (wird automatisch generiert wenn nicht gesetzt)

### 8.4 Aktuelle Netzwerksicherheit (Tailscale VPN)

Im aktuellen Setup kommunizieren Pi und Server über **Tailscale VPN**. Tailscale basiert auf **WireGuard** und verschlüsselt alle Daten end-to-end mit ChaCha20-Poly1305. Das bedeutet:

- Alle Bilder vom Pi zum Server sind **verschlüsselt** (via WireGuard-Tunnel)
- Alle API-Antworten zurück sind **verschlüsselt**
- Niemand im öffentlichen Internet kann die Daten mitlesen
- Die Endpoints sind nur innerhalb des Tailscale-Netzwerks erreichbar

Dadurch ist das System für den Hackathon-Scope **ausreichend abgesichert**, auch ohne zusätzliche HTTPS- oder API-Key-Schicht.

### 8.5 Supabase-Sicherheit

**Aktuelle Implementierung (Hackathon):**
- Zugriff erfolgt ausschliesslich serverseitig über den `service_role`-Key
- RLS (Row Level Security) ist aktiviert, Policies erlauben jedoch vollen Zugriff (`USING (true)`)
- Input-Validierung: Whitelist-Filter in `supabase_client.py` und `server.py` (doppelte Absicherung)
- Keine direkte Supabase-Verbindung vom Frontend — alle Abfragen laufen über die Flask-API

**Durchgeführte Fixes:**
- `update_product()` filtert jetzt auch in `supabase_client.py` auf erlaubte Felder (Whitelist)
- `create_order()` verwendet `upsert` mit Dokumentation warum (PK-Constraint auf `prod_id`)
- SQL-Setup mit Sicherheitshinweisen und Produktionsempfehlungen ergänzt

**Bewertung:** Für den Hackathon akzeptabel, da nur der Server auf Supabase zugreift und das System im VPN läuft. Für Produktion müssen restriktive RLS-Policies und Key-Trennung umgesetzt werden (siehe 8.6).

### 8.6 Bekannte Einschränkungen und Best-Practice-Empfehlungen für Produktion

Die folgenden Punkte wurden bewusst **nicht** implementiert, da sie den Rahmen des Hackathons übersteigen. Für einen Produktiveinsatz müssten diese adressiert werden:

| Punkt | Beschreibung | Empfehlung für Produktion |
|-------|--------------|---------------------------|
| **Supabase: service_role Key** | Der `service_role`-Key umgeht alle RLS-Policies und hat vollen DB-Zugriff. Akzeptabel, da nur der Server ihn verwendet. | `anon`-Key fürs Frontend (read-only), `service_role` nur serverseitig. Keys strikt trennen. |
| **Supabase: RLS Policies** | Policies erlauben vollen Zugriff für alle Rollen (`USING (true)`). | Restriktive Policies pro Rolle: `anon` = nur SELECT auf products, `service_role` = ALL |
| **Secrets in Git-History** | `.env` mit echten Keys war zeitweise in der Git-Historie. | Keys rotieren (Supabase, SendGrid), History bereinigen (BFG Repo-Cleaner) |
| **Keine API-Authentifizierung** | Alle Endpoints sind ohne Login/Token zugänglich. Innerhalb des Tailscale-VPNs ist dies unkritisch, da nur autorisierte Geräte Zugang haben. | API-Key-Validierung für Pi-zu-Server-Kommunikation, JWT-basierte Authentifizierung für das Frontend, Session-basierte Zugriffskontrolle |
| **Keine WebSocket-Authentifizierung** | WebSocket-Verbindungen werden ohne Token-Prüfung akzeptiert | Token-Validierung im `connect`-Handler, unautorisierte Verbindungen abweisen |
| **Kein Rate Limiting** | Endpoints können beliebig oft aufgerufen werden (DoS-Risiko, Massen-E-Mails) | Flask-Limiter einsetzen (z.B. 60 Req/min für Standard-Endpoints, 5/min für Sync und Detect) |
| **HTTP statt HTTPS** | Daten werden unverschlüsselt via HTTP übertragen – jedoch durch den Tailscale/WireGuard-Tunnel auf Netzwerkebene vollständig verschlüsselt | Zusätzliche TLS-Terminierung via Reverse Proxy (nginx + Let's Encrypt) für Defense-in-Depth |
| **Development Server** | Werkzeug Dev-Server ist nicht für Produktion ausgelegt | Gunicorn oder uWSGI hinter nginx einsetzen |
| **Keine Security Headers** | CSP, X-Frame-Options, HSTS etc. fehlen | Flask-Talisman oder manuelle Header via `@app.after_request` |
| **Server auf 0.0.0.0** | Server lauscht auf allen Netzwerk-Interfaces | Auf `127.0.0.1` binden und nur über Reverse Proxy exponieren |

#### Empfohlene Absicherung für Produktion (Best Practice)

Für einen produktiven Einsatz empfehlen wir die Umsetzung in folgender Prioritätsreihenfolge:

**1. API-Key für Pi-zu-Server-Kommunikation (Machine-to-Machine)**
Ein Shared Secret wird auf beiden Seiten in der `.env`-Datei hinterlegt. Der Pi sendet bei jedem Request einen `Authorization: Bearer <API-KEY>` Header mit. Der Server prüft diesen Header und lehnt Requests ohne gültigen Key mit HTTP 401 ab. Dies ist die einfachste und schnellste Massnahme, um die Kommunikation zwischen internen Diensten abzusichern.

**2. HTTPS via Reverse Proxy (TLS-Verschlüsselung)**
Ein nginx Reverse Proxy wird vor den Flask-Server geschaltet und terminiert TLS mit einem Let's Encrypt Zertifikat. Flask bindet dann nur noch auf `127.0.0.1:5001` und ist nicht mehr direkt erreichbar. Alle Verbindungen von aussen laufen über HTTPS (Port 443). Dies bietet eine zweite Verschlüsselungsschicht zusätzlich zum VPN (Defense-in-Depth).

**3. JWT-Authentifizierung für das Frontend (User-facing)**
Benutzer loggen sich über ein Login-Formular ein und erhalten ein signiertes JWT-Token. Dieses Token wird bei jedem API-Request im Header mitgesendet und vom Server validiert. Unautorisierte Requests werden mit HTTP 401 abgelehnt. Für WebSocket-Verbindungen wird das Token als Query-Parameter beim Connect mitgegeben und im `connect`-Handler geprüft. Frameworks wie Flask-JWT-Extended vereinfachen die Implementierung.

**4. Rate Limiting (DoS-Schutz)**
Flask-Limiter begrenzt die Anzahl Requests pro Zeiteinheit und IP-Adresse. Empfohlene Limits: 60 Requests/Minute für Standard-Endpoints, 5/Minute für rechenintensive Endpoints wie `/api/detect` und `/api/products/sync`. Dies verhindert Missbrauch, Massen-E-Mail-Versand und Ressourcenerschöpfung.

---

## 9. Deployment & CI/CD


### GitHub Actions Pipeline (`.github/workflows/deploy.yml`)
Bei jedem Push auf `main`:
1. **Tailscale VPN** aufbauen (AuthKey aus GitHub Secrets)
2. **SSH auf Pi** via Tailscale-IP
3. `git pull`, Dependencies installieren, systemd-Service neustarten

### Pi-Autostart (`smartshelf.service`)
- systemd-Service: Startet `pi.pi_client` automatisch nach Netzwerkverbindung
- User: `admin`, WorkingDirectory: `/home/admin/smartshelf`
- Restart bei Fehler nach 10 Sekunden

### Netzwerk
- **Tailscale** für VPN-Verbindung zwischen GitHub Actions und Pi
- Pi erreichbar über Tailscale-IP (z.B. 100.65.165.53)

---

## 10. Konfiguration & Secrets

### Umgebungsvariablen (`.env`)
| Variable | Beschreibung |
|----------|-------------|
| `SUPABASE_URL` | Supabase Projekt-URL |
| `SUPABASE_KEY` | Supabase Service-Role-Key |
| `SENDGRID_API_KEY` | SendGrid API-Key für E-Mail-Versand |
| `FROM_EMAIL` | Absender-E-Mail |
| `SAP_ALL_PRODUCTS_URL` | Celonis Make Webhook URL für alle SAP-Produkte |
| `SAP_SINGLE_PRODUCT_URL` | Celonis Make Webhook URL für einzelnes SAP-Produkt |
| `FLASK_SECRET_KEY` | Flask Session-Signierung (wird automatisch generiert wenn leer) |
| `CORS_ORIGINS` | Erlaubte WebSocket-Origins, kommagetrennt (Default: `http://localhost:3000`) |
| `SAM2_CHECKPOINT` | Pfad zum SAM2-Modell (Default: `./models/sam2_hiera_tiny.pt`) |
| `SERVER_URL` | Server-Adresse (nur für Pi relevant) |

### GitHub Secrets
| Secret | Verwendet von |
|--------|---------------|
| `TAILSCALE_AUTHKEY` | GitHub Actions VPN |
| `TAILSCALE_PI_IP` | GitHub Actions SSH |
| `PI_SSH_KEY` | GitHub Actions SSH |

---

## 11. Tech Stack

| Bereich | Technologie |
|---------|-------------|
| **Edge-Hardware** | Raspberry Pi 4, Pi Camera Module (3280×2464) |
| **Edge-KI** | YOLO26n (Ultralytics), PyTorch |
| **Server** | Python Flask + Flask-SocketIO |
| **Server-KI** | Grounding DINO, Florence-2, SAM2 (HuggingFace Transformers) |
| **Datenbank** | Supabase (PostgreSQL) |
| **ERP-Integration** | SAP Business One (via Celonis Make Webhook) |
| **E-Mail** | SendGrid API |
| **Frontend** | Vue.js 3, Vite 8, TailwindCSS 4, Pinia 3, Lucide Icons |
| **Echtzeit** | Socket.IO (WebSocket) |
| **Deployment** | GitHub Actions + Tailscale VPN + systemd |
| **Training** | Roboflow (Labeling), Custom Training (200+ Epochen, >90% mAP) |

---

## 12. Tests

Das Projekt enthält eine automatisierte Test-Suite mit **pytest**, die alle API-Endpunkte und die Kerngeschäftslogik abdeckt. Die Tests laufen ohne Netzwerk oder Datenbank – alle externen Abhängigkeiten (Supabase, SendGrid, SAP) werden gemockt.

### Testausführung

```bash
# Tests ausführen
python -m pytest tests/ -v

# Mit Coverage-Report
python -m pytest tests/ --cov=server --cov-report=term-missing
```

### Testabdeckung (31 Tests)

| Testklasse | Tests | Geprüfte Funktionalität |
|---|---|---|
| **TestHealth** | 2 | Health-Check, Root-Endpoint |
| **TestDashboard** | 1 | Dashboard liefert products/orders/scans |
| **TestScan** | 7 | Input-Validierung, Schwellwert-Logik (count <= min_qty), Doppelbestellungs-Schutz, Scan-Logging |
| **TestWareneingang** | 4 | Validierung, Stock-Aufstockung (current_stock + received_qty), WARENEINGANG-Logging |
| **TestProductUpdate** | 4 | Erlaubte/nicht erlaubte Felder, Whitelist-Filter, 404 |
| **TestPathTraversal** | 4 | Path Traversal Schutz (.., \\, ungültige Pfade) |
| **TestCamera** | 4 | Upload-Validierung, Storage Toggle, Fehlerbehandlung |
| **TestSAPSync** | 2 | Erfolg + Fehlerfall |
| **TestSendGrid** | 2 | CSV-Format (Semikolon-Delimiter), Default-Einheit |

### Wichtige getestete Geschäftsregeln

- **Schwellwert**: `count <= min_qty` löst Bestellung aus (inkl. `0 <= 0`)
- **Doppelbestellungs-Schutz**: Keine zweite Bestellung wenn PENDING existiert
- **Wareneingang**: `sap_stock = current_stock + received_qty`
- **Security**: Path Traversal wird blockiert, nur erlaubte Felder bei Product Update
- **Fehlerbehandlung**: Fehlende Felder, ungültiges JSON, Produkt nicht gefunden

---

## 13. Quick Start

### Server (PC/Laptop)
```bash
# Repository klonen
git clone <repo-url>
cd Hackathon_Baden_2026

# Virtual Environment erstellen
python -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements_server.txt
pip install torch torchvision transformers sam2

# Umgebungsvariablen konfigurieren
cp .env.example .env   # Secrets eintragen

# Server starten
python -m server.server   # Läuft auf Port 5001
```

### Frontend
```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
```

### Pi (Raspberry Pi 4)
```bash
pip install -r requirements_pi.txt
python -m pi.pi_client
```

### Pi Autostart (systemd)
```bash
sudo cp smartshelf.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smartshelf
sudo systemctl start smartshelf
```

### Supabase einrichten
SQL im Supabase Dashboard SQL Editor ausführen (siehe `supabase_setup.sql`).
