"""SendGrid E-Mail-Versand mit CSV-Anhang für Nachbestellungen."""

import base64
import csv
import html
import io
import os
import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition,
)
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("smartshelf-server")

_api_key = os.getenv("SENDGRID_API_KEY")
_from_email = os.getenv("FROM_EMAIL")

if not _api_key or not _from_email:
    raise RuntimeError("SENDGRID_API_KEY und FROM_EMAIL müssen in .env gesetzt sein")

sg = SendGridAPIClient(_api_key)


def _build_csv(product: dict, quantity: int) -> str:
    """Erstellt CSV-Inhalt für die Bestellung."""
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


def send_order_mail(product: dict, quantity: int) -> bool:
    """
    Sendet eine Bestell-E-Mail an den Lieferanten mit CSV-Anhang.

    Args:
        product: Produktdaten aus Supabase (inkl. supplier_email, supplier_name, etc.)
        quantity: Bestellmenge (reorder_qty)

    Returns:
        True bei Erfolg, False bei Fehler
    """
    supplier_email = product["supplier_email"]
    safe_email = html.escape(supplier_email)
    prod_name = html.escape(product["prod_name"])
    prod_id = html.escape(product["prod_id"])
    unit = html.escape(product.get("unit", "Stk"))
    qty = int(quantity)

    csv_content = _build_csv(product, quantity)
    csv_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")

    import datetime
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    message = Mail(
        from_email=_from_email,
        to_emails=supplier_email,
        subject=f"SmartShelf Nachbestellung: {prod_name} ({prod_id})",
        html_content=f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background-color:#f4f6f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9; padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:12px; overflow:hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr>
          <td style="background: linear-gradient(135deg, #1e293b 0%, #334155 100%); padding:32px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <h1 style="color:#ffffff; margin:0; font-size:22px; font-weight:700; letter-spacing:-0.3px;">SmartShelf</h1>
                  <p style="color:#94a3b8; margin:4px 0 0; font-size:13px;">Automatische Lagerbestandsverwaltung</p>
                </td>
                <td align="right">
                  <span style="background-color:#ef4444; color:#ffffff; padding:6px 14px; border-radius:20px; font-size:12px; font-weight:600;">Nachbestellung</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px;">
            <p style="color:#1e293b; font-size:15px; margin:0 0 20px; line-height:1.6;">
              Guten Tag,
            </p>
            <p style="color:#475569; font-size:14px; margin:0 0 28px; line-height:1.6;">
              Unser automatisches Lagersystem hat einen niedrigen Bestand erkannt und eine Nachbestellung ausgeloest.
            </p>

            <!-- Order Card -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; overflow:hidden; margin-bottom:28px;">
              <tr>
                <td style="padding:20px 24px; border-bottom:1px solid #e2e8f0;">
                  <p style="color:#64748b; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0 0 6px; font-weight:600;">Produkt</p>
                  <p style="color:#1e293b; font-size:18px; font-weight:700; margin:0;">{prod_name}</p>
                  <p style="color:#94a3b8; font-size:12px; margin:4px 0 0; font-family:monospace;">{prod_id}</p>
                </td>
              </tr>
              <tr>
                <td style="padding:0;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td width="50%" style="padding:16px 24px; border-right:1px solid #e2e8f0;">
                        <p style="color:#64748b; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0 0 4px; font-weight:600;">Bestellmenge</p>
                        <p style="color:#1e293b; font-size:24px; font-weight:700; margin:0;">{qty} <span style="font-size:14px; color:#64748b; font-weight:400;">{unit}</span></p>
                      </td>
                      <td width="50%" style="padding:16px 24px;">
                        <p style="color:#64748b; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0 0 4px; font-weight:600;">Empfaenger</p>
                        <p style="color:#1e293b; font-size:14px; font-weight:600; margin:0;">{safe_email}</p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <p style="color:#475569; font-size:13px; margin:0 0 8px; line-height:1.6;">
              Die vollstaendigen Bestelldetails finden Sie im beigefuegten <strong>CSV-Anhang</strong>.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background-color:#f8fafc; padding:20px 40px; border-top:1px solid #e2e8f0;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <p style="color:#94a3b8; font-size:11px; margin:0;">Automatisch generiert am {now}</p>
                  <p style="color:#94a3b8; font-size:11px; margin:4px 0 0;">SmartShelf &middot; Data Unit AG &middot; Hackathon Baden 2026</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
        """,
    )

    attachment = Attachment(
        FileContent(csv_b64),
        FileName(f"bestellung_{product['prod_id']}.csv"),
        FileType("text/csv"),
        Disposition("attachment"),
    )
    message.attachment = attachment

    try:
        response = sg.send(message)
        log.info(
            "E-Mail an %s gesendet (Status: %d)",
            supplier_email,
            response.status_code,
        )
        return response.status_code in (200, 201, 202)
    except Exception as e:
        log.error("SendGrid-Fehler: %s", e)
        return False
