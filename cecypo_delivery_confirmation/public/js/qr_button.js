// Adds a "Generate QR Code" button to source DocType forms.
// Registered in hooks.py doctype_js for each configured DocType.
// When this file executes, frappe.get_route()[1] is the current doctype name.

(function () {
	const doctype = frappe.get_route ? frappe.get_route()[1] : null;
	if (!doctype) return;

	frappe.ui.form.on(doctype, {
		refresh(frm) {
			if (frm.doc.__islocal || !frm.doc.name) return;

			frm.add_custom_button(
				__("Generate QR Code"),
				function () {
					frappe.call({
						method: "cecypo_delivery_confirmation.api.generate_qr_code",
						args: { doc_type: frm.doctype, doc_name: frm.doc.name },
						freeze: true,
						freeze_message: __("Generating QR Code\u2026"),
						callback(r) {
							if (!r.message) return;
							const { qr_code, url } = r.message;

							const d = new frappe.ui.Dialog({
								title: __("Delivery Confirmation QR Code"),
								fields: [{ fieldtype: "HTML", fieldname: "qr_html" }],
								primary_action_label: __("Download PNG"),
								primary_action() {
									const a = document.createElement("a");
									a.href = qr_code;
									a.download = `QR-${frm.doc.name}.png`;
									a.click();
								},
							});

							d.fields_dict.qr_html.$wrapper.html(`
								<div style="text-align:center;padding:20px 16px 8px;">
									<img src="${qr_code}"
										style="max-width:260px;width:100%;border:1px solid #e5e7eb;border-radius:8px;" />
									<p style="margin:12px 0 4px;font-size:0.8em;color:#6b7280;word-break:break-all;">${url}</p>
								</div>
							`);

							d.show();
						},
					});
				},
				__("Delivery")
			);
		},
	});
})();
