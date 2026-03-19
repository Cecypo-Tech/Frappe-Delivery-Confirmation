import frappe


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = 0

	if frappe.session.user == "Guest":
		allow_guest = frappe.db.get_single_value("Delivery Confirmation Settings", "allow_guest_access")
		if not allow_guest:
			frappe.local.flags.redirect_location = f"/login?redirect-to={frappe.local.request.path}"
			raise frappe.Redirect
