EXTRACTION_CASES = [
    {
        "file": "data/1.pdf",
        "doc_type": "invoice",
        "doc_number": "2343-AB-34",
        "supplier_name": "ACB LED solutions",
    },
    {
        "file": "data/GST_Invoice_INV-202604-1001.pdf",
        "doc_type": "invoice",
        "doc_number": "INV-202604-1001",
        "supplier_name": "ElectroMart India",
    },
]

TEXT_EXTRACTION_CASES = [
    {
        "name": "invoice_alias_fields",
        "doc_type": "invoice",
        "text": """
        TAX INVOICE
        Bill No: ZX-4451
        Vendor Name: Precision Castparts Ltd
        Customer Name: AutoMotion Systems Pvt Ltd
        Issue Date: 14-04-2026
        Amount Payable: INR 45678.90
        Purchase Order No: PO-77881
        Payment Terms: 45 Days
        Dispatch Mode: Road Transport
        """,
        "expected": {
            "doc_number": "ZX-4451",
            "supplier_name": "Precision Castparts Ltd",
            "buyer_name": "AutoMotion Systems Pvt Ltd",
            "amount": 45678.9,
            "po_number": "PO-77881",
            "payment_terms": "45 Days",
        },
        "extra_fields": {
            "dispatch mode": "Road Transport",
        },
    },
    {
        "name": "invoice_split_labels",
        "doc_type": "invoice",
        "text": """
        TAX INVOICE
        Document Number:
        INV-SPLIT-9001
        Seller:
        Alpha Industrial Supplies
        Buyer:
        Nova Motors Plant 2
        Date:
        13 Apr 2026
        Net Amount:
        98765.40
        Currency: INR
        """,
        "expected": {
            "doc_number": "INV-SPLIT-9001",
            "supplier_name": "Alpha Industrial Supplies",
            "buyer_name": "Nova Motors Plant 2",
            "amount": 98765.4,
            "currency": "INR",
        },
        "extra_fields": {},
    },
    {
        "name": "bom_supplier_variation",
        "doc_type": "bom",
        "text": """
        BILL OF MATERIAL
        BOM Number: BOM-AXLE-2207
        Manufacturer: Vertex Components
        Assembly Number: ASM-7788-Z
        Rev: C3
        Effective Date: 2026-04-01
        Plant Code: Pune-02
        Customer Ref: RFQ-99881
        Coating Spec: Zinc Nickel
        Item No  Part No      Description              Qty   UOM   Rev   Remarks
        10       BRK-221      Brake Caliper Assembly  2     Nos   C3    Machined
        20       PIP-998      Hydraulic Pipe          4     Nos   B1    Zinc coated
        """,
        "expected": {
            "doc_number": "BOM-AXLE-2207",
            "supplier_name": "Vertex Components",
            "part_number": "ASM-7788-Z",
            "revision": "C3",
            "plant_code": "Pune-02",
        },
        "extra_fields": {
            "customer ref": "RFQ-99881",
            "coating spec": "Zinc Nickel",
        },
        "expected_line_items": [
            {
                "item_no": "10",
                "part_number": "BRK-221",
                "description": "Brake Caliper Assembly",
                "quantity": 2,
                "unit": "Nos",
                "revision": "C3",
                "remarks": "Machined",
            },
            {
                "item_no": "20",
                "part_number": "PIP-998",
                "description": "Hydraulic Pipe",
                "quantity": 4,
                "unit": "Nos",
                "revision": "B1",
                "remarks": "Zinc coated",
            },
        ],
    },
    {
        "name": "bom_column_alias_mapping",
        "doc_type": "bom",
        "text": """
        BILL OF MATERIAL
        BOM No: BOM-FRAME-1101
        Supplier: Atlas Fabrication Works
        Part Number: FRAME-1101-A
        Revision: R7
        Position | Component Code | Component Name | Required Qty | Unit of Measure | Note
        1 | C-100 | Side Rail LH | 2 | Nos | Laser cut
        2 | C-101 | Side Rail RH | 2 | Nos | Laser cut
        3 | C-250 | Cross Member Front | 1 | Nos | Welded
        """,
        "expected": {
            "doc_number": "BOM-FRAME-1101",
            "supplier_name": "Atlas Fabrication Works",
            "part_number": "FRAME-1101-A",
            "revision": "R7",
        },
        "extra_fields": {},
        "expected_line_items": [
            {
                "item_no": "1",
                "part_number": "C-100",
                "description": "Side Rail LH",
                "quantity": 2,
                "unit": "Nos",
                "remarks": "Laser cut",
            },
            {
                "item_no": "2",
                "part_number": "C-101",
                "description": "Side Rail RH",
                "quantity": 2,
                "unit": "Nos",
                "remarks": "Laser cut",
            },
            {
                "item_no": "3",
                "part_number": "C-250",
                "description": "Cross Member Front",
                "quantity": 1,
                "unit": "Nos",
                "remarks": "Welded",
            },
        ],
    },
]

ROUTING_CASES = [
    {"query": "INV-202604-1001", "route": "exact_match"},
    {"query": "invoice from ElectroMart India in Apr 2026", "route": "lexical"},
    {"query": "wireless mouse invoice", "route": "hybrid"},
    {"query": "which item has the rate of 85000.00?", "route": "lexical"},
]

RETRIEVAL_CASES = [
    {"query": "INV-202604-1001", "expected_doc_number": "INV-202604-1001"},
    {"query": "invoice from ElectroMart India", "expected_supplier_name": "ElectroMart India"},
    {"query": "which item has the rate of 85000.00?", "expected_doc_number": "INV-2025-0412"},
]
