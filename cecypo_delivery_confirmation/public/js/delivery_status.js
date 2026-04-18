(function () {
	const CACHE_KEY = "dc_source_doctype";
	const CACHE_EXPIRY_KEY = "dc_source_doctype_expiry";
	const CACHE_TTL_MS = 10 * 60 * 1000; // 10 minutes

	// Feather-style truck SVG (inline, no dependency on Frappe icon sprite)
	const TRUCK_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"
		viewBox="0 0 24 24" fill="none" stroke="currentColor"
		stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
		<rect x="1" y="3" width="15" height="13"></rect>
		<polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon>
		<circle cx="5.5" cy="18.5" r="2.5"></circle>
		<circle cx="18.5" cy="18.5" r="2.5"></circle>
	</svg>`;

	function getCachedSourceDoctype() {
		try {
			const expiry = parseInt(localStorage.getItem(CACHE_EXPIRY_KEY) || "0", 10);
			if (Date.now() < expiry) {
				return localStorage.getItem(CACHE_KEY) || null;
			}
		} catch (e) {
			// localStorage unavailable
		}
		return undefined; // cache miss
	}

	function setCachedSourceDoctype(value) {
		try {
			localStorage.setItem(CACHE_KEY, value || "");
			localStorage.setItem(CACHE_EXPIRY_KEY, Date.now() + CACHE_TTL_MS);
		} catch (e) {
			// ignore
		}
	}

	function getSourceDoctype(callback) {
		const cached = getCachedSourceDoctype();
		if (cached !== undefined) {
			callback(cached);
			return;
		}
		frappe.call({
			method: "cecypo_delivery_confirmation.api.get_source_doctype",
			callback(r) {
				const dt = r.message || "";
				setCachedSourceDoctype(dt);
				callback(dt);
			},
		});
	}

	function renderTruckIcon(frm, status, confirmation) {
		// Remove any previously injected icon
		$(frm.wrapper).find(".dc-truck-btn").remove();

		const $statsArea = $(frm.wrapper).find(".form-stats-likes");
		if (!$statsArea.length) return;

		const confirmed = status === "confirmed";
		const duplicate = confirmed && confirmation.scan_count > 1;
		const color = !confirmed
			? "var(--gray-400, #adb5bd)"
			: duplicate
				? "var(--red-500, #e53935)"
				: "var(--green-500, #28a745)";

		const deliveredTo = confirmed
			? (confirmation.delivered_to_name || frappe.datetime.str_to_user(confirmation.scanned_at || ""))
			: "";
		const title = !confirmed
			? "Pending Delivery"
			: duplicate
				? `Duplicate Scans Detected – ${deliveredTo}`
				: `Delivery Confirmed – ${deliveredTo}`;

		const $btn = $(`
			<span class="dc-truck-btn d-flex align-items-center"
				title="${frappe.utils.escape_html(title)}"
				style="cursor:${confirmed ? "pointer" : "default"};color:${color};margin-left:6px;">
				${TRUCK_SVG}
			</span>
		`);

		if (confirmed && confirmation) {
			$btn.on("click", function () {
				frappe.set_route("Form", "Delivery Confirmation", confirmation.name);
			});
		}

		$statsArea.append($btn);
	}

	function showDeliveryStatus(frm) {
		// Guard: prevent duplicate calls for the same document
		const docKey = frm.doctype + "::" + frm.doc.name;
		if (frm._dc_shown === docKey) return;
		frm._dc_shown = docKey;

		frappe.call({
			method: "cecypo_delivery_confirmation.api.get_delivery_status",
			args: { doc_type: frm.doctype, doc_name: frm.doc.name },
			callback(r) {
				if (!r.message) return;
				const { status, confirmation } = r.message;
				renderTruckIcon(frm, status, confirmation);
			},
		});
	}

	function tryCurrentForm(sourceDoctype) {
		if (!sourceDoctype) return;
		if (
			window.cur_frm &&
			cur_frm.doctype === sourceDoctype &&
			cur_frm.doc &&
			!cur_frm.doc.__islocal &&
			cur_frm.doc.name
		) {
			showDeliveryStatus(cur_frm);
		}
	}

	function registerFormHandler(sourceDoctype) {
		if (!sourceDoctype) return;

		frappe.ui.form.on(sourceDoctype, {
			refresh(frm) {
				if (frm.doc.__islocal || !frm.doc.name) return;
				// Reset guard on each refresh so re-navigating to same doc works
				frm._dc_shown = null;
				showDeliveryStatus(frm);
			},
		});

		// Fix race condition: form may already be open when this handler is registered
		tryCurrentForm(sourceDoctype);
	}

	function setupRouteListener(sourceDoctype) {
		if (!sourceDoctype || !frappe.router) return;
		frappe.router.on("change", function () {
			const route = frappe.get_route();
			if (route[0] === "Form" && route[1] === sourceDoctype) {
				setTimeout(function () {
					tryCurrentForm(sourceDoctype);
				}, 50);
			}
		});
	}

	function init() {
		getSourceDoctype(function (sourceDoctype) {
			registerFormHandler(sourceDoctype);
			setupRouteListener(sourceDoctype);
		});
	}

	$(document).ready(init);
})();
