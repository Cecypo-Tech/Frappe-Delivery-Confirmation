// Copyright (c) 2026, Cecypo.Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Delivery Confirmation", {
	refresh(frm) {
		const count = frm.doc.scan_count || 1;
		if (count > 1) {
			frm.page.set_indicator(__("Scanned {0}×", [count]), "red");
		} else {
			frm.page.set_indicator(__("Delivered"), "green");
		}
	},
});
