### Delivery Confirmation

Confirm delivery status by scanning a QR code on any mobile device. No login required for the scanner.

---

### How It Works

1. A QR code on a physical document (e.g. a KRA eTIMS invoice) is scanned using the built-in camera scanner at `/delivery`.
2. The app extracts a value from the raw QR string based on the configured extraction method.
3. It looks up the matching document in ERPNext (e.g. the Sales Invoice where `etr_invoice_number = 999555`).
4. **First scan** → green screen, recipient fills in their details and confirms delivery.
5. **Subsequent scans** → red alert showing who confirmed it and when. Optionally sends an email notification to configured admins.

---

### Configuration

Go to **Delivery Confirmation Settings** (Settings menu or `/desk/delivery-confirmation-settings`).

#### Document Matching

| Setting | Description |
|---|---|
| **Source DocType** | The DocType to search in, e.g. `Sales Invoice` |
| **Match Field** | The field whose value is extracted from the QR, e.g. `etr_invoice_number` |
| **QR Value Extraction Method** | How to pull the value out of the raw QR string (see below) |

#### Extraction Methods

**URL Parameter** — for QR codes that are URLs with query parameters.

Example QR string:
```
https://itax.kra.go.ke/KRA-Portal/invoiceChk.htm?actionCode=loadPage&invoiceNo=999555
```
Set `URL Parameter Name` = `invoiceNo` → extracts `999555`.

---

**Regex** — for any QR string where a regex can capture the value.

Example QR string: `INV-999555-KE`
Set `Regex Pattern` = `INV-(\w+)-` → extracts `999555`.
The first capture group `(...)` is used as the value.

---

**Full String** — the entire raw QR string is used as the field value directly.
Use this when the QR encodes exactly the field value with no extra text.

---

#### Duplicate Scan Notifications

Enable **Send Notification on Duplicate Scan** and add email addresses to the **Notification Recipients** table. An email is sent automatically whenever an already-confirmed document is scanned again.

---

### Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch version-16
bench install-app cecypo_delivery_confirmation
bench --site <your-site> migrate
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/cecypo_delivery_confirmation
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
