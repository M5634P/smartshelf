"""SmartShelf Detection Pipeline – SAM2 + Florence-2 + Grounding DINO."""

import os
import re
import warnings
from pathlib import Path

os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
warnings.filterwarnings("ignore")

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision.ops import nms
from transformers import (
    AutoModelForCausalLM,
    AutoModelForZeroShotObjectDetection,
    AutoProcessor,
)

from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

# ─── Konfiguration ───────────────────────────────────────────────────────────

SAM2_CHECKPOINT = os.getenv("SAM2_CHECKPOINT", str(Path(__file__).resolve().parent.parent / "models" / "sam2_hiera_tiny.pt"))
SAM2_CONFIG = "sam2_hiera_t"

# Zonen-Definition: (name, prod_id, (x1,y1,x2,y2), color_bgr, method, prompt)
# method: "dino" | "florence_hybrid" | "none"
ZONES = [
    # EBENE 1 (oben) – eng innerhalb der Regalpfosten
    ("Rolle",            "013880",      (640, 510, 1180, 790),   (255, 255, 0),   "dino",            "towel. rolled towel. fabric roll."),
    ("USB Plug",         "013999",      (1180, 510, 2100, 790),  (255, 0, 255),   "none",            ""),
    ("Dymo",             "0319.3776",   (2100, 420, 2600, 790),  (255, 0, 0),     "dino",            "label printer box. DYMO box."),
    # EBENE 2 (mitte)
    ("Audi Ersatzteil",  "0319.3775",   (640, 1130, 1550, 1370), (0, 255, 255),   "none",            ""),
    ("BMW Ersatzteil",   "0319.3774",   (1550, 1130, 2600, 1370),(0, 0, 255),     "none",            ""),
    # EBENE 3 (unten)
    ("Kopfhörer",        "0319.3770",   (640, 1530, 930, 1940),  (200, 100, 255), "dino",            "headphones. earphones. headset."),
    ("Bostichbox",       "0319.3772",   (930, 1530, 1450, 1940), (255, 200, 0),   "dino",            "cardboard box."),
    ("Schokolade",       "0319.3771",   (1450, 1530, 2020, 1940),(0, 255, 255),   "sam2",            "chocolate bar. flat package. candy bar."),
    ("Jasskarten",       "0319.377098", (2020, 1530, 2500, 1940),(0, 255, 0),     "florence_hybrid",  "small box. white box. package."),
]

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


# ─── Model Loading ───────────────────────────────────────────────────────────

_models = {}


def load_models():
    """Lädt alle AI-Modelle einmalig."""
    if _models:
        return _models

    print("[detect] Loading Grounding DINO...")
    _models["dino_processor"] = AutoProcessor.from_pretrained("IDEA-Research/grounding-dino-tiny")
    _models["dino_model"] = AutoModelForZeroShotObjectDetection.from_pretrained("IDEA-Research/grounding-dino-tiny")

    print("[detect] Loading Florence-2...")
    _models["fl_processor"] = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)
    _models["fl_model"] = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)

    print("[detect] Loading SAM 2...")
    sam2 = build_sam2(SAM2_CONFIG, SAM2_CHECKPOINT, device="cpu")
    _models["sam2_predictor"] = SAM2ImagePredictor(sam2)
    _models["sam2_mask_generator"] = SAM2AutomaticMaskGenerator(
        model=sam2,
        points_per_side=32,
        pred_iou_thresh=0.7,
        stability_score_thresh=0.8,
        min_mask_region_area=200,
    )

    print("[detect] All models loaded!")
    return _models


# ─── Detection Helpers ───────────────────────────────────────────────────────

def florence2_caption_count(crop_pil):
    """Zählt Objekte via Florence-2 Caption."""
    m = load_models()
    task = "<MORE_DETAILED_CAPTION>"
    inputs = m["fl_processor"](text=task, images=crop_pil, return_tensors="pt")
    with torch.no_grad():
        gen = m["fl_model"].generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024, num_beams=3,
        )
    result = m["fl_processor"].batch_decode(gen, skip_special_tokens=False)[0]
    parsed = m["fl_processor"].post_process_generation(
        result, task=task, image_size=(crop_pil.width, crop_pil.height),
    )
    caption = parsed.get(task, "")
    count = 0
    for word, num in NUMBER_WORDS.items():
        if re.search(r"\b" + word + r"\b", caption.lower()):
            if count == 0:
                count = num
    return count, caption


def detect_dino_filtered(crop_pil, prompt, threshold=0.30, nms_iou=0.3):
    """Erkennt Objekte mit Grounding DINO + NMS + Filter."""
    m = load_models()
    cw, ch = crop_pil.size
    inputs = m["dino_processor"](images=crop_pil, text=prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = m["dino_model"](**inputs)
    r = m["dino_processor"].post_process_grounded_object_detection(
        outputs, input_ids=inputs.input_ids,
        box_threshold=threshold, text_threshold=threshold,
        target_sizes=[(ch, cw)],
    )[0]
    if len(r["scores"]) == 0:
        return 0, []
    keep = nms(r["boxes"], r["scores"], nms_iou)
    filtered = []
    for idx in keep:
        b = r["boxes"][idx]
        s = float(r["scores"][idx])
        x1, y1, x2, y2 = [float(c) for c in b]
        bw, bh = x2 - x1, y2 - y1
        if bw / max(bh, 1) > 3.0 or (bw * bh) / (cw * ch) > 0.85:
            continue
        filtered.append((s, [round(x1), round(y1), round(x2), round(y2)]))
    return len(filtered), filtered


def _mask_iou(m1, m2):
    """IoU zwischen zwei boolean-Masken."""
    intersection = np.logical_and(m1, m2).sum()
    union = np.logical_or(m1, m2).sum()
    return intersection / max(union, 1)


# Kalibrierung Schokolade: gemessen aus Referenzbildern
# 1 Tafel = 138px Höhe, jede weitere Tafel addiert ~25px (Perspektive von oben)
CHOCO_SINGLE_HEIGHT = 138
CHOCO_LAYER_HEIGHT = 25


def detect_sam2_calibrated(crop_pil):
    """Kombiniert: DINO findet einzelne Tafeln, SAM2 Masken, Höhe zählt Stapel."""
    m = load_models()
    crop_np = np.array(crop_pil)
    ch, cw = crop_np.shape[:2]

    # 1. DINO: Alle Detektionen finden
    inputs = m["dino_processor"](
        images=crop_pil, text="chocolate bar. flat package.", return_tensors="pt")
    with torch.no_grad():
        outputs = m["dino_model"](**inputs)
    r = m["dino_processor"].post_process_grounded_object_detection(
        outputs, input_ids=inputs.input_ids,
        box_threshold=0.12, text_threshold=0.12,
        target_sizes=[(ch, cw)],
    )[0]

    if len(r["scores"]) == 0:
        print("  [SAM2] DINO fand nichts")
        return 0, []

    # NMS und Filtern
    keep = nms(r["boxes"], r["scores"], 0.3)
    boxes = []
    for idx in keep:
        b = r["boxes"][idx]
        s = float(r["scores"][idx])
        x1, y1, x2, y2 = [float(c) for c in b]
        bw, bh = x2 - x1, y2 - y1
        area_ratio = (bw * bh) / (cw * ch)
        # Filter: zu gross, zu schmal, am Rand (Regalpfosten)
        if area_ratio > 0.60 or area_ratio < 0.03:
            continue
        if bw / max(bh, 1) > 4.0:
            continue
        if min(bw, bh) < 0.08 * min(cw, ch):
            continue
        boxes.append((s, [x1, y1, x2, y2]))

    print(f"  [SAM2] DINO: {len(boxes)} Boxen nach Filter")

    if not boxes:
        return 0, []

    # 2. SAM2: Maske für jede Box
    m["sam2_predictor"].set_image(crop_np)
    all_results = []

    for i, (dino_score, box) in enumerate(boxes):
        x1, y1, x2, y2 = box
        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
        masks, scores, _ = m["sam2_predictor"].predict(
            point_coords=np.array([[cx, cy]]),
            point_labels=np.array([1]),
            multimask_output=True,
        )
        if masks.ndim == 4:
            masks = masks[:, 0]

        best_mask_idx = scores.argmax()
        mask = masks[best_mask_idx]
        score = float(scores[best_mask_idx])

        ys, xs = np.where(mask)
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        mask_height = int(ys.max() - ys.min())
        print(f"  [SAM2]   box {i}: dino={dino_score:.2f}, sam2={score:.2f}, "
              f"height={mask_height}px, bbox={bbox}")
        all_results.append((score, bbox, mask, mask_height))

    # 3. Deduplizieren (überlappende SAM2-Masken)
    unique = []
    for score, bbox, mask, height in sorted(all_results, key=lambda x: -x[0]):
        is_dup = False
        for _, _, existing_mask, _ in unique:
            if _mask_iou(mask, existing_mask) > 0.5:
                is_dup = True
                break
        if not is_dup:
            unique.append((score, bbox, mask, height))

    print(f"  [SAM2] {len(unique)} unique Masken")

    # 4. Zählung: 1 Maske = 1 Objekt
    total_count = len(unique)
    dets = [(score, bbox, mask) for score, bbox, mask, height in unique]

    print(f"  [SAM2] Total: {total_count} Objekte")
    return total_count, dets


# ─── Main Detection Pipeline ────────────────────────────────────────────────

def detect_image(image_path=None, output_path=None, image_pil=None):
    """
    Führt die komplette Detection-Pipeline auf einem Bild aus.

    Args:
        image_path: Pfad zum Bild (oder None wenn image_pil gegeben)
        output_path: Pfad für annotiertes Bild
        image_pil: PIL Image direkt (optional, statt image_path)

    Returns:
        results: Liste von (name, prod_id, count, zone, dets, color, method)
        output_path: Pfad zum annotierten Bild (falls output_path angegeben)
    """
    load_models()
    if image_pil is None:
        image_pil = Image.open(image_path).convert("RGB")
    else:
        image_pil = image_pil.convert("RGB")
    w, h = image_pil.size

    results = []
    for name, prod_id, (zx1, zy1, zx2, zy2), color, method, prompt in ZONES:
        if method == "none":
            results.append((name, prod_id, 0, (zx1, zy1, zx2, zy2), [], color, method))
            continue

        crop = image_pil.crop((zx1, zy1, zx2, zy2))

        if method == "sam2":
            sam2_count, dets = detect_sam2_calibrated(crop)
            results.append((name, prod_id, sam2_count, (zx1, zy1, zx2, zy2), dets, color, method))
            print(f"[detect] {name} [SAM2]: {sam2_count}")
        elif method == "florence_hybrid":
            fl_count, caption = florence2_caption_count(crop)
            dino_count, dets = detect_dino_filtered(crop, prompt, threshold=0.15)
            final_count = max(fl_count, dino_count)
            results.append((name, prod_id, final_count, (zx1, zy1, zx2, zy2), dets, color, method))
            print(f"[detect] {name} [Florence+DINO]: Florence={fl_count} DINO={dino_count} -> {final_count}")
        else:  # dino
            dino_count, dets = detect_dino_filtered(crop, prompt)
            results.append((name, prod_id, dino_count, (zx1, zy1, zx2, zy2), dets, color, method))
            print(f"[detect] {name} [DINO]: {dino_count}")

    # Annotiertes Bild erstellen
    if output_path:
        _draw_results(image_pil, results, output_path)

    return results, output_path


def _draw_results(image_pil_or_path, results, output_path):
    """Zeichnet die Detection-Ergebnisse auf das Bild – sauberer Stil."""
    if isinstance(image_pil_or_path, str):
        img = cv2.imread(image_pil_or_path)
    else:
        img = cv2.cvtColor(np.array(image_pil_or_path), cv2.COLOR_RGB2BGR)

    # 1. Leichter Zonen-Overlay
    overlay = img.copy()
    for name, prod_id, count, (zx1, zy1, zx2, zy2), dets, color, method in results:
        cv2.rectangle(overlay, (zx1, zy1), (zx2, zy2), color, -1)
    img = cv2.addWeighted(overlay, 0.12, img, 0.88, 0)

    # 2. Zonen-Rahmen, Labels, DINO-Boxen (ohne SAM-Masken!)
    for name, prod_id, count, (zx1, zy1, zx2, zy2), dets, color, method in results:
        # Zone border
        cv2.rectangle(img, (zx1, zy1), (zx2, zy2), color, 3)

        # Method tag
        method_str = ""
        if method == "florence_hybrid":
            method_str = " [Florence+DINO]"
        elif method == "sam2":
            method_str = " [SAM2]"

        # Label oben links
        label = f"{name}: {count}{method_str}"
        (tw, th_), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(img, (zx1, zy1 - 30), (zx1 + tw + 10, zy1), color, -1)
        cv2.putText(img, label, (zx1 + 5, zy1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

        # Prod-ID unten links
        if prod_id:
            cv2.putText(img, prod_id, (zx1 + 5, zy2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
            cv2.putText(img, prod_id, (zx1 + 5, zy2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        # Produktname zentriert
        if count > 0:
            cx = (zx1 + zx2) // 2
            cy = (zy1 + zy2) // 2 + 10
            (tw2, _), _ = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
            cv2.putText(img, name, (cx - tw2 // 2, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3)
            cv2.putText(img, name, (cx - tw2 // 2, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

        # Detection-Visualisierung
        det_colors = [(255, 100, 50), (50, 255, 100), (50, 150, 255), (255, 200, 50)]
        if method == "sam2" and dets and len(dets[0]) == 3:
            # SAM2+DINO: Farbige Masken-Overlays mit Nummern
            overlay2 = img.copy()
            for i, (s, b, mask) in enumerate(dets):
                dc = det_colors[i % len(det_colors)]
                # Maske in Bildkoordinaten einsetzen
                mask_bool = mask.astype(bool)
                roi = overlay2[zy1:zy2, zx1:zx2]
                roi[mask_bool] = (
                    roi[mask_bool] * 0.4 + np.array(dc, dtype=np.float64) * 0.6
                ).astype(np.uint8)
                # Kontur zeichnen
                contours, _ = cv2.findContours(
                    mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for c in contours:
                    c[:, :, 0] += zx1
                    c[:, :, 1] += zy1
                cv2.drawContours(overlay2, contours, -1, dc, 2)
                # Nummer in der Mitte der Maske
                x1, y1, x2, y2 = b
                cx = zx1 + (x1 + x2) // 2
                cy = zy1 + (y1 + y2) // 2
                cv2.putText(overlay2, str(i + 1), (cx - 8, cy + 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 4)
                cv2.putText(overlay2, str(i + 1), (cx - 8, cy + 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            img = overlay2
        else:
            # DINO/Florence: Bounding Boxes
            for i, det in enumerate(dets):
                s, b = det[0], det[1]
                x1, y1, x2, y2 = b
                dc = det_colors[i % len(det_colors)]
                cv2.rectangle(img, (zx1 + x1, zy1 + y1), (zx1 + x2, zy1 + y2), dc, 2)

    cv2.imwrite(output_path, img)
    print(f"[detect] Annotiertes Bild gespeichert: {output_path}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m server.detect <image_path> [output_path]")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else image_path.replace(".jp", "_detected.jp")

    results, _ = detect_image(image_path, output_path)

    total = sum(r[2] for r in results)
    print(f"\n{'='*40}")
    print(f"TOTAL: {total} items")
    for name, prod_id, count, *_ in results:
        status = "LEER" if count == 0 else str(count)
        print(f"  {name} ({prod_id}): {status}")
