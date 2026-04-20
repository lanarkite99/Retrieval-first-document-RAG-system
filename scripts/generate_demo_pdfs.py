import argparse
import json
from pathlib import Path

import fitz


SUPPLIERS = [
    {
        "name": "Shakti Auto Parts Pvt Ltd",
        "gstin": "27AALCS4521M1ZP",
        "address": "Plot 18, MIDC Chakan, Pune, Maharashtra 410501",
    },
    {
        "name": "Vertex Industrial Supply",
        "gstin": "29AACCV7788Q1Z4",
        "address": "No 42, Peenya Phase 2, Bengaluru, Karnataka 560058",
    },
    {
        "name": "PrimeFab Components LLP",
        "gstin": "24AATFP6622C1Z8",
        "address": "Survey 77, Sanand GIDC, Ahmedabad, Gujarat 382110",
    },
    {
        "name": "Apex Motion Systems",
        "gstin": "33AARFA1188J1Z6",
        "address": "SIDCO Estate, Hosur Main Road, Chennai, Tamil Nadu 600032",
    },
]

BUYERS = [
    {
        "name": "Falcon Motors Plant 2",
        "address": "Sector 14, Bhosari Industrial Area, Pune, Maharashtra 411026",
    },
    {
        "name": "Nexa Drive Assembly Unit",
        "address": "Kolar Road, Vemagal Industrial Zone, Karnataka 563101",
    },
    {
        "name": "Trident EV Manufacturing",
        "address": "Industrial Corridor, Sanand, Gujarat 382170",
    },
]

INVOICE_CASES = [
    {
        "file_name": "gst_invoice_batch_1001.pdf",
        "supplier": SUPPLIERS[0],
        "buyer": BUYERS[0],
        "invoice_number": "GST-INV-2026-1001",
        "invoice_date": "14/04/2026",
        "payment_terms": "30 Days",
        "po_number": "PO-78001",
        "extra_label": "Dispatch Mode",
        "extra_value": "Road",
        "items": [
            {"description": "Brake Pad Set", "hsn": "8708", "qty": 12, "rate": 1450.00, "gst": 18},
            {"description": "Clutch Cable", "hsn": "8708", "qty": 30, "rate": 320.00, "gst": 18},
            {"description": "Head Lamp Assembly", "hsn": "8512", "qty": 8, "rate": 2180.00, "gst": 18},
        ],
    },
    {
        "file_name": "gst_invoice_batch_1002.pdf",
        "supplier": SUPPLIERS[1],
        "buyer": BUYERS[1],
        "invoice_number": "GST-INV-2026-1002",
        "invoice_date": "14/04/2026",
        "payment_terms": "45 Days",
        "po_number": "PO-78002",
        "extra_label": "Vehicle No",
        "extra_value": "KA01AB4455",
        "items": [
            {"description": "Radiator Hose", "hsn": "4009", "qty": 20, "rate": 265.00, "gst": 18},
            {"description": "Wheel Bearing Kit", "hsn": "8482", "qty": 10, "rate": 1840.00, "gst": 18},
            {"description": "Air Filter Element", "hsn": "8421", "qty": 25, "rate": 490.00, "gst": 12},
        ],
    },
    {
        "file_name": "gst_invoice_batch_1003.pdf",
        "supplier": SUPPLIERS[2],
        "buyer": BUYERS[2],
        "invoice_number": "GST-INV-2026-1003",
        "invoice_date": "14/04/2026",
        "payment_terms": "15 Days",
        "po_number": "PO-78003",
        "extra_label": "E-Way Bill",
        "extra_value": "EWB99887766",
        "items": [
            {"description": "Battery Tray", "hsn": "8708", "qty": 14, "rate": 960.00, "gst": 18},
            {"description": "Control Arm", "hsn": "8708", "qty": 16, "rate": 1750.00, "gst": 18},
            {"description": "Engine Mount", "hsn": "8708", "qty": 18, "rate": 840.00, "gst": 18},
        ],
    },
    {
        "file_name": "gst_invoice_batch_1004.pdf",
        "supplier": SUPPLIERS[3],
        "buyer": BUYERS[0],
        "invoice_number": "GST-INV-2026-1004",
        "invoice_date": "14/04/2026",
        "payment_terms": "Advance",
        "po_number": "PO-78004",
        "extra_label": "Plant Code",
        "extra_value": "PUNE-02",
        "items": [
            {"description": "Seat Belt Retractor", "hsn": "8708", "qty": 6, "rate": 2650.00, "gst": 18},
            {"description": "Door Handle Assembly", "hsn": "8302", "qty": 22, "rate": 430.00, "gst": 18},
            {"description": "Wiper Motor", "hsn": "8501", "qty": 5, "rate": 3380.00, "gst": 18},
        ],
    },
    {
        "file_name": "gst_invoice_batch_1005.pdf",
        "supplier": SUPPLIERS[0],
        "buyer": BUYERS[2],
        "invoice_number": "GST-INV-2026-1005",
        "invoice_date": "14/04/2026",
        "payment_terms": "21 Days",
        "po_number": "PO-78005",
        "extra_label": "Transporter",
        "extra_value": "SafeHaul Logistics",
        "items": [
            {"description": "Fog Lamp Housing", "hsn": "8512", "qty": 12, "rate": 1280.00, "gst": 18},
            {"description": "Horn Assembly", "hsn": "8512", "qty": 15, "rate": 540.00, "gst": 18},
            {"description": "Fuel Cap", "hsn": "8302", "qty": 40, "rate": 155.00, "gst": 18},
        ],
    },
    {
        "file_name": "gst_invoice_batch_1006.pdf",
        "supplier": SUPPLIERS[1],
        "buyer": BUYERS[1],
        "invoice_number": "GST-INV-2026-1006",
        "invoice_date": "14/04/2026",
        "payment_terms": "30 Days",
        "po_number": "PO-78006",
        "extra_label": "Warehouse",
        "extra_value": "BLR-RAW-01",
        "items": [
            {"description": "Steering Coupling", "hsn": "8708", "qty": 9, "rate": 1890.00, "gst": 18},
            {"description": "Tie Rod End", "hsn": "8708", "qty": 24, "rate": 410.00, "gst": 18},
            {"description": "ABS Sensor", "hsn": "9031", "qty": 11, "rate": 1485.00, "gst": 18},
        ],
    },
    {
        "file_name": "gst_invoice_batch_1007.pdf",
        "supplier": SUPPLIERS[2],
        "buyer": BUYERS[0],
        "invoice_number": "GST-INV-2026-1007",
        "invoice_date": "14/04/2026",
        "payment_terms": "60 Days",
        "po_number": "PO-78007",
        "extra_label": "Inspection Ref",
        "extra_value": "IR-4412",
        "items": [
            {"description": "Lower Suspension Arm", "hsn": "8708", "qty": 8, "rate": 2840.00, "gst": 18},
            {"description": "Stabilizer Link", "hsn": "8708", "qty": 20, "rate": 620.00, "gst": 18},
            {"description": "Wheel Speed Sensor", "hsn": "9031", "qty": 10, "rate": 1325.00, "gst": 18},
        ],
    },
]

BOM_CASES = [
    {
        "file_name": "bom_batch_2001.pdf",
        "supplier": SUPPLIERS[0],
        "bom_number": "BOM-CHASSIS-2001",
        "assembly_number": "ASM-CH-2001-A",
        "revision": "R2",
        "plant_code": "PUNE-02",
        "extra_label": "Coating Spec",
        "extra_value": "Powder Coat Black",
        "header": "Item No  Part No       Description               Qty   UOM   Remarks",
        "rows": [
            {"item_no": "10", "part_number": "CH-110", "description": "Cross Member Front", "quantity": 1, "unit": "Nos", "remarks": "Welded"},
            {"item_no": "20", "part_number": "CH-120", "description": "Side Rail Left", "quantity": 1, "unit": "Nos", "remarks": "Laser Cut"},
            {"item_no": "30", "part_number": "CH-121", "description": "Side Rail Right", "quantity": 1, "unit": "Nos", "remarks": "Laser Cut"},
        ],
    },
    {
        "file_name": "bom_batch_2002.pdf",
        "supplier": SUPPLIERS[1],
        "bom_number": "BOM-DOOR-2002",
        "assembly_number": "DR-ASM-4401",
        "revision": "B4",
        "plant_code": "BLR-01",
        "extra_label": "Customer Ref",
        "extra_value": "RFQ-DOOR-91",
        "header": "Position  Component Code  Component Name         Required Qty  Unit of Measure  Note",
        "rows": [
            {"item_no": "1", "part_number": "DR-201", "description": "Outer Door Panel", "quantity": 1, "unit": "Nos", "remarks": "Stamped"},
            {"item_no": "2", "part_number": "DR-202", "description": "Inner Door Panel", "quantity": 1, "unit": "Nos", "remarks": "Stamped"},
            {"item_no": "3", "part_number": "DR-310", "description": "Window Channel", "quantity": 2, "unit": "Nos", "remarks": "Rolled"},
        ],
    },
    {
        "file_name": "bom_batch_2003.pdf",
        "supplier": SUPPLIERS[3],
        "bom_number": "BOM-SEAT-2003",
        "assembly_number": "ST-ASM-7782",
        "revision": "C1",
        "plant_code": "CHN-03",
        "extra_label": "Process Route",
        "extra_value": "Cutting > Stitching > Assembly",
        "header": "Pos  Material Code  Description            Qty  UOM  Rev  Note",
        "rows": [
            {"item_no": "1", "part_number": "ST-410", "description": "Seat Frame Base", "quantity": 1, "unit": "Nos", "revision": "C1", "remarks": "Powder Coat"},
            {"item_no": "2", "part_number": "ST-520", "description": "Seat Foam Cushion", "quantity": 1, "unit": "Nos", "revision": "C1", "remarks": "Molded"},
            {"item_no": "3", "part_number": "ST-610", "description": "Seat Cover Fabric", "quantity": 1, "unit": "Nos", "revision": "C1", "remarks": "Black Trim"},
        ],
    },
]


def money(value):
    return f"{value:.2f}"


def compute_invoice_totals(items):
    taxable_total = 0.0
    gst_total = 0.0

    for item in items:
        taxable = item["qty"] * item["rate"]
        gst_amount = taxable * item["gst"] / 100.0
        item["taxable"] = round(taxable, 2)
        item["gst_amount"] = round(gst_amount, 2)
        taxable_total += taxable
        gst_total += gst_amount

    grand_total = taxable_total + gst_total
    return round(taxable_total, 2), round(gst_total, 2), round(grand_total, 2)


def add_lines(page, lines):
    y = 40
    for line in lines:
        page.insert_text((40, y), line, fontsize=11, fontname="cour")
        y += 18


def build_invoice_lines(case):
    taxable_total, gst_total, grand_total = compute_invoice_totals(case["items"])
    supplier = case["supplier"]
    buyer = case["buyer"]

    lines = []
    lines.append("GST TAX INVOICE")
    lines.append(f"Supplier: {supplier['name']}")
    lines.append(f"GSTIN: {supplier['gstin']}")
    lines.append(f"Address: {supplier['address']}")
    lines.append(f"Invoice No: {case['invoice_number']}")
    lines.append(f"Date: {case['invoice_date']}")
    lines.append(f"Buyer Name: {buyer['name']}")
    lines.append(f"Bill To Address: {buyer['address']}")
    lines.append(f"PO Number: {case['po_number']}")
    lines.append(f"Payment Terms: {case['payment_terms']}")
    lines.append(f"{case['extra_label']}: {case['extra_value']}")
    lines.append("")
    lines.append("HSN  Description                   Qty   Rate       Taxable    GST%   GST Amt")

    for item in case["items"]:
        description = item["description"][:27]
        row = f"{item['hsn']:<4} {description:<27} {item['qty']:>3} {money(item['rate']):>10} {money(item['taxable']):>10} {item['gst']:>4}% {money(item['gst_amount']):>9}"
        lines.append(row)

    lines.append("")
    lines.append(f"Taxable Amount: {money(taxable_total)}")
    lines.append(f"Total GST: {money(gst_total)}")
    lines.append(f"Grand Total: {money(grand_total)} INR")
    lines.append("Declaration: Goods received in good condition.")
    return lines, grand_total


def build_bom_lines(case):
    supplier = case["supplier"]
    lines = []
    lines.append("BILL OF MATERIAL")
    lines.append(f"Manufacturer: {supplier['name']}")
    lines.append(f"GSTIN: {supplier['gstin']}")
    lines.append(f"BOM Number: {case['bom_number']}")
    lines.append(f"Assembly Number: {case['assembly_number']}")
    lines.append(f"Rev: {case['revision']}")
    lines.append("Effective Date: 2026-04-14")
    lines.append(f"Plant Code: {case['plant_code']}")
    lines.append(f"{case['extra_label']}: {case['extra_value']}")
    lines.append("")
    lines.append(case["header"])

    for row in case["rows"]:
        revision = row.get("revision")
        if "Rev" in case["header"]:
            line = f"{row['item_no']:<3}  {row['part_number']:<13} {row['description']:<22} {row['quantity']:>3}  {row['unit']:<3}  {revision or case['revision']:<3}  {row['remarks']}"
        elif "Position" in case["header"]:
            line = f"{row['item_no']:<8} {row['part_number']:<15} {row['description']:<22} {row['quantity']:>6}        {row['unit']:<8} {row['remarks']}"
        else:
            line = f"{row['item_no']:<8} {row['part_number']:<13} {row['description']:<24} {row['quantity']:>3}   {row['unit']:<3}   {row['remarks']}"
        lines.append(line)

    return lines


def write_pdf(path, lines):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    add_lines(page, lines)
    doc.save(path)
    doc.close()


def build_invoice_eval_entry(case, grand_total, base_dir):
    return {
        "name": case["invoice_number"].lower().replace("-", "_"),
        "supplier": case["supplier"]["name"],
        "file": str((base_dir / case["file_name"]).as_posix()),
        "doc_type": "invoice",
        "expected_fields": {
            "doc_number": case["invoice_number"],
            "supplier_name": case["supplier"]["name"],
            "buyer_name": case["buyer"]["name"],
            "amount": grand_total,
            "po_number": case["po_number"],
            "payment_terms": case["payment_terms"],
        },
        "expected_extra_fields": {
            case["extra_label"].lower(): case["extra_value"],
        },
    }


def build_bom_eval_entry(case, base_dir):
    expected_rows = []
    for row in case["rows"]:
        item = {
            "item_no": row["item_no"],
            "part_number": row["part_number"],
            "description": row["description"],
            "quantity": row["quantity"],
            "unit": row["unit"],
            "remarks": row["remarks"],
        }
        if row.get("revision"):
            item["revision"] = row["revision"]
        expected_rows.append(item)

    return {
        "name": case["bom_number"].lower().replace("-", "_"),
        "supplier": case["supplier"]["name"],
        "file": str((base_dir / case["file_name"]).as_posix()),
        "doc_type": "bom",
        "expected_fields": {
            "doc_number": case["bom_number"],
            "supplier_name": case["supplier"]["name"],
            "part_number": case["assembly_number"],
            "revision": case["revision"],
            "plant_code": case["plant_code"],
        },
        "expected_extra_fields": {
            case["extra_label"].lower(): case["extra_value"],
        },
        "expected_line_items": expected_rows,
    }


def generate(output_dir, dataset_path):
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = []

    for case in INVOICE_CASES:
        lines, grand_total = build_invoice_lines(case)
        write_pdf(output_dir / case["file_name"], lines)
        entries.append(build_invoice_eval_entry(case, grand_total, output_dir))

    for case in BOM_CASES:
        lines = build_bom_lines(case)
        write_pdf(output_dir / case["file_name"], lines)
        entries.append(build_bom_eval_entry(case, output_dir))

    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text(json.dumps(entries, indent=2))

    print(f"Created {len(INVOICE_CASES)} invoice PDFs and {len(BOM_CASES)} BOM PDFs in {output_dir}")
    print(f"Evaluation dataset written to {dataset_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate demo GST invoices and BOM PDFs")
    parser.add_argument("--output-dir", default="data/generated_batch")
    parser.add_argument("--dataset", default="eval/datasets/generated_batch_eval.json")
    args = parser.parse_args()

    generate(Path(args.output_dir), Path(args.dataset))
