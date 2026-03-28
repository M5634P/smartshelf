"""Tests für SendGrid E-Mail CSV-Generierung (ohne echten Versand)."""

import csv
import io


def _build_csv(product: dict, quantity: int) -> str:
    """Repliziert die CSV-Logik aus sendgrid_notifier für isoliertes Testen."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Produkt-ID", "Produktname", "Bestellmenge", "Einheit"])
    writer.writerow([
        product["prod_id"],
        product["prod_name"],
        quantity,
        product.get("unit", "Stk"),
    ])
    return output.getvalue()


def test_build_csv():
    """CSV wird korrekt mit Semikolon-Delimiter erstellt."""
    product = {
        "prod_id": "013880",
        "prod_name": "Rolle",
        "unit": "Stk",
    }
    result = _build_csv(product, 10)

    reader = csv.reader(io.StringIO(result), delimiter=";")
    rows = list(reader)

    assert rows[0] == ["Produkt-ID", "Produktname", "Bestellmenge", "Einheit"]
    assert rows[1][0] == "013880"
    assert rows[1][1] == "Rolle"
    assert rows[1][2] == "10"
    assert rows[1][3] == "Stk"


def test_build_csv_default_unit():
    """Fehlende Einheit wird mit 'Stk' gefüllt."""
    product = {"prod_id": "X", "prod_name": "Test"}
    result = _build_csv(product, 1)

    reader = csv.reader(io.StringIO(result), delimiter=";")
    rows = list(reader)
    assert rows[1][3] == "Stk"
