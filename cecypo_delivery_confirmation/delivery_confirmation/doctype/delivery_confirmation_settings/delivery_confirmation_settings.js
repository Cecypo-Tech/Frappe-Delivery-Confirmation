// Copyright (c) 2026, Cecypo.Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Delivery Confirmation Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Open Delivery Page"), function () {
			window.open("/delivery", "_blank");
		});
	},
});
