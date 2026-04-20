CANONICAL_FIELDS = {
    "doc_number": {
        "aliases": [
            "invoice no",
            "invoice number",
            "document no",
            "document number",
            "bill no",
            "bill number",
            "voucher no",
            "voucher number",
            "bom no",
            "bom number",
            "ref no",
            "reference no",
        ],
        "type": "text",
    },
    "supplier_name": {
        "aliases": [
            "supplier",
            "supplier name",
            "vendor",
            "vendor name",
            "seller",
            "seller name",
            "from",
            "issued by",
            "manufacturer",
        ],
        "type": "text",
    },
    "buyer_name": {
        "aliases": [
            "buyer",
            "buyer name",
            "customer name",
            "bill to",
            "ship to",
            "consignee",
            "to",
        ],
        "type": "text",
    },
    "doc_date": {
        "aliases": [
            "date",
            "invoice date",
            "document date",
            "bill date",
            "issue date",
            "created date",
            "posting date",
            "effective date",
        ],
        "type": "date",
    },
    "amount": {
        "aliases": [
            "grand total",
            "total amount",
            "invoice total",
            "net amount",
            "amount payable",
            "final amount",
            "total invoice value",
            "total",
        ],
        "type": "amount",
    },
    "currency": {
        "aliases": ["currency"],
        "type": "text",
    },
    "gstin": {
        "aliases": ["gstin", "supplier gstin", "gst number"],
        "type": "gstin",
    },
    "buyer_gstin": {
        "aliases": ["buyer gstin", "customer gstin", "consignee gstin", "bill to gstin"],
        "type": "gstin",
    },
    "po_number": {
        "aliases": [
            "po no",
            "po number",
            "purchase order no",
            "purchase order number",
            "customer po",
        ],
        "type": "text",
    },
    "payment_terms": {
        "aliases": ["payment terms", "terms of payment", "payment condition"],
        "type": "text",
    },
    "part_number": {
        "aliases": [
            "part no",
            "part number",
            "assembly no",
            "assembly number",
            "material code",
            "item code",
        ],
        "type": "text",
    },
    "revision": {
        "aliases": ["revision", "rev", "revision no", "revision number"],
        "type": "text",
    },
    "plant_code": {
        "aliases": ["plant", "plant code", "site", "site code", "location code"],
        "type": "text",
    },
}


DOC_TYPE_FIELDS = {
    "invoice": [
        "doc_number",
        "supplier_name",
        "buyer_name",
        "doc_date",
        "amount",
        "currency",
        "gstin",
        "buyer_gstin",
        "po_number",
        "payment_terms",
    ],
    "bom": [
        "doc_number",
        "supplier_name",
        "buyer_name",
        "doc_date",
        "part_number",
        "revision",
        "plant_code",
        "currency",
    ],
    "receipt": [
        "doc_number",
        "supplier_name",
        "buyer_name",
        "doc_date",
        "amount",
        "currency",
    ],
    "unknown": [
        "doc_number",
        "supplier_name",
        "buyer_name",
        "doc_date",
        "amount",
        "currency",
    ],
}


BOM_LINE_ITEM_FIELDS = {
    "item_no": ["item", "item no", "item number", "sr no", "line no", "position", "pos"],
    "part_number": ["part no", "part number", "component code", "material code", "item code", "code"],
    "description": ["description", "component", "component name", "part description", "material description"],
    "quantity": ["qty", "quantity", "req qty", "required qty", "usage qty"],
    "unit": ["unit", "uom", "measure", "unit of measure"],
    "revision": ["rev", "revision"],
    "remarks": ["remarks", "remark", "note", "notes"],
}
