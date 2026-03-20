import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def lookup_document_by_qr(qr_string):
	"""
	Parse a raw QR code string, extract the matching value per settings,
	and return the doc_type + doc_name of the matched document.
	"""
	if not qr_string:
		return {"found": False, "error": _("Empty QR code.")}

	settings = frappe.get_single("Delivery Confirmation Settings")

	if not settings.source_doctype or not settings.match_field or not settings.qr_extract_method:
		return {"found": False, "error": _("Delivery Confirmation Settings are not fully configured.")}

	value = _extract_qr_value(qr_string, settings)
	if not value:
		return {"found": False, "error": _("Could not extract a value from this QR code.")}

	doc_name = frappe.db.get_value(settings.source_doctype, {settings.match_field: value}, "name")
	if not doc_name:
		return {
			"found": False,
			"error": _("No {0} found where {1} = {2}.").format(
				settings.source_doctype, settings.match_field, value
			),
		}

	return {
		"found": True,
		"doc_type": settings.source_doctype,
		"doc_name": doc_name,
		"matched_value": value,
	}


def _extract_qr_value(qr_string, settings):
	"""Extract the relevant value from the raw QR string based on configured method."""
	method = settings.qr_extract_method

	if method == "URL Parameter":
		from urllib.parse import parse_qs, urlparse

		try:
			parsed = urlparse(qr_string)
			params = parse_qs(parsed.query)
			param_name = (settings.qr_url_param or "").strip()
			if param_name and param_name in params:
				return params[param_name][0]
		except Exception:
			pass

	elif method == "Regex":
		import re

		pattern = (settings.qr_regex_pattern or "").strip()
		if pattern:
			try:
				m = re.search(pattern, qr_string)
				if m:
					return m.group(1) if m.lastindex else m.group(0)
			except re.error:
				pass

	elif method == "Full String":
		return qr_string.strip() or None

	return None


@frappe.whitelist(allow_guest=True)
def get_confirmation_status(doc_type, doc_name):
	"""
	Check if a delivery has already been confirmed for this document.
	Returns status 'confirmed' with details, or 'pending'.
	On duplicate scan: increments scan_count, appends to scan_log, and sends notifications.
	"""
	existing_name = frappe.db.get_value(
		"Delivery Confirmation",
		{"document_type": doc_type, "document_name": doc_name, "status": "First Scan"},
		"name",
	)

	if existing_name:
		dc_doc = frappe.get_doc("Delivery Confirmation", existing_name)
		dc_doc.scan_count = (dc_doc.scan_count or 1) + 1
		dc_doc.append("scan_log", {
			"scanned_by": frappe.session.user,
			"scanned_at": frappe.utils.now_datetime(),
		})
		dc_doc.save(ignore_permissions=True)

		_send_duplicate_notification(doc_type, doc_name, dc_doc)
		return {
			"status": "confirmed",
			"confirmation": {
				"name": dc_doc.name,
				"scanned_by": dc_doc.scanned_by,
				"scanned_at": dc_doc.scanned_at,
				"delivered_to_name": dc_doc.delivered_to_name,
				"delivered_to_id": dc_doc.delivered_to_id,
				"delivered_to_phone": dc_doc.delivered_to_phone,
				"number_plate": dc_doc.number_plate,
				"other_info": dc_doc.other_info,
				"photo": dc_doc.photo,
				"scan_count": dc_doc.scan_count,
			},
		}

	return {"status": "pending"}


@frappe.whitelist(allow_guest=True)
def submit_delivery_confirmation(
	doc_type,
	doc_name,
	delivered_to_name=None,
	delivered_to_id=None,
	delivered_to_phone=None,
	number_plate=None,
	other_info=None,
	photo=None,
):
	"""Submit a first-time delivery confirmation for a document."""
	existing = frappe.db.exists(
		"Delivery Confirmation",
		{"document_type": doc_type, "document_name": doc_name, "status": "First Scan"},
	)
	if existing:
		frappe.throw(_("This delivery has already been confirmed."))

	now = frappe.utils.now_datetime()

	doc = frappe.new_doc("Delivery Confirmation")
	doc.document_type = doc_type
	doc.document_name = doc_name
	doc.status = "First Scan"
	doc.scan_count = 1
	doc.scanned_by = frappe.session.user  # "Guest" for unauthenticated users
	doc.scanned_at = now
	doc.delivered_to_name = delivered_to_name
	doc.delivered_to_id = delivered_to_id
	doc.delivered_to_phone = delivered_to_phone
	doc.number_plate = number_plate
	doc.other_info = other_info
	doc.photo = photo
	doc.append("scan_log", {
		"scanned_by": frappe.session.user,
		"scanned_at": now,
	})
	doc.insert(ignore_permissions=True)

	_send_client_notification(doc_type, doc_name, doc)

	return {"name": doc.name, "status": "success"}


def _send_duplicate_notification(doc_type, doc_name, dc_doc):
	"""Send email notification to configured recipients when a duplicate scan is detected."""
	try:
		settings = frappe.get_single("Delivery Confirmation Settings")
		if not settings.send_notification_on_duplicate:
			return

		recipients = [row.email for row in settings.notification_recipients if row.email]
		if not recipients:
			return

		scanned_at = frappe.utils.format_datetime(dc_doc.scanned_at) if dc_doc.scanned_at else "N/A"

		subject = f"\u26a0\ufe0f Duplicate QR Scan: {doc_type} \u2013 {doc_name}"
		message = f"""
<p>A <strong>duplicate QR code scan</strong> has been detected. Please investigate.</p>

<table style="border-collapse:collapse;width:100%;max-width:500px;">
  <tr style="background:#fef2f2;">
    <td style="padding:8px 12px;border:1px solid #fca5a5;font-weight:600;">Document</td>
    <td style="padding:8px 12px;border:1px solid #fca5a5;">{doc_type} &ndash; {doc_name}</td>
  </tr>
  <tr>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;font-weight:600;">Scan Count</td>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;">{dc_doc.scan_count}</td>
  </tr>
  <tr>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;font-weight:600;">Originally Confirmed By</td>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;">{dc_doc.scanned_by or "N/A"}</td>
  </tr>
  <tr>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;font-weight:600;">Originally Confirmed At</td>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;">{scanned_at}</td>
  </tr>
  <tr>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;font-weight:600;">Delivered To</td>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;">{dc_doc.delivered_to_name or "N/A"}</td>
  </tr>
  <tr>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;font-weight:600;">ID Number</td>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;">{dc_doc.delivered_to_id or "N/A"}</td>
  </tr>
  <tr>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;font-weight:600;">Phone</td>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;">{dc_doc.delivered_to_phone or "N/A"}</td>
  </tr>
</table>

<p style="margin-top:16px;color:#6b7280;font-size:0.875em;">
  This notification was sent automatically by Delivery Confirmation.
</p>
"""
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			now=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Delivery Confirmation: Duplicate Scan Notification Error")


def _send_client_notification(doc_type, doc_name, dc_doc):
	"""Send email notification to the client contact on the scanned document after first confirmation."""
	try:
		settings = frappe.get_single("Delivery Confirmation Settings")
		if not settings.send_notification_to_client:
			return

		client_email_field = (settings.client_email_field or "").strip()
		if not client_email_field:
			return

		client_email = frappe.db.get_value(doc_type, doc_name, client_email_field)
		if not client_email:
			return

		scanned_at = frappe.utils.format_datetime(dc_doc.scanned_at) if dc_doc.scanned_at else "N/A"

		subject = (settings.client_notification_subject or "Delivery Confirmed – {doc_name}").format(
			doc_name=doc_name,
			doc_type=doc_type,
		)

		if settings.client_notification_message:
			message = settings.client_notification_message.format(
				doc_type=doc_type,
				doc_name=doc_name,
				delivered_to_name=dc_doc.delivered_to_name or "N/A",
				scanned_at=scanned_at,
			)
		else:
			message = f"""
<p>Dear Customer,</p>
<p>Your delivery for <strong>{doc_type} &ndash; {doc_name}</strong> has been confirmed.</p>
<table style="border-collapse:collapse;width:100%;max-width:500px;">
  <tr>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;font-weight:600;">Delivered To</td>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;">{dc_doc.delivered_to_name or "N/A"}</td>
  </tr>
  <tr>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;font-weight:600;">Confirmed At</td>
    <td style="padding:8px 12px;border:1px solid #e5e7eb;">{scanned_at}</td>
  </tr>
</table>
<p style="margin-top:16px;color:#6b7280;font-size:0.875em;">
  This notification was sent automatically by Delivery Confirmation.
</p>
"""

		frappe.sendmail(
			recipients=[client_email],
			subject=subject,
			message=message,
			now=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Delivery Confirmation: Client Notification Error")
