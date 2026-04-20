import json
from dataclasses import dataclass
from pathlib import Path

from fpdf import FPDF


ROOT = Path(__file__).resolve().parent
PDF_DIR = ROOT / "pdfs"
EXTRACTION_DATASET = ROOT / "final_metrics_extraction_eval.json"
RETRIEVAL_DATASET = ROOT / "final_metrics_retrieval_golden.json"


@dataclass
class Party:
    name: str
    gstin: str
    address: str
    contact: str
    email: str


SUPPLIERS = [
    Party("Asterion Drive Systems Pvt Ltd", "27AAECA1111A1Z8", "Plot 11, Talegaon MIDC, Pune, Maharashtra 410507", "+91-20-41001111", "finance@asteriondrive.in"),
    Party("BriskVolt Mobility Components LLP", "29AACCB2222B1Z7", "No. 6, Bommasandra Industrial Area, Bengaluru, Karnataka 560099", "+91-80-42002222", "accounts@briskvolt.in"),
    Party("Crestline Fabrication Works Pvt Ltd", "24AACCC3333C1Z6", "Survey 48, Changodar GIDC, Ahmedabad, Gujarat 382213", "+91-2717-430333", "billing@crestlinefab.in"),
    Party("Dynorail Precision India Pvt Ltd", "33AACCD4444D1Z5", "SIDCO Industrial Estate, Guindy, Chennai, Tamil Nadu 600032", "+91-44-44004444", "ap@dynorail.in"),
    Party("Elara Industrial Plastics Pvt Ltd", "06AACCE5555E1Z4", "Plot 23, IMT Manesar, Gurugram, Haryana 122050", "+91-124-4500555", "finance@elaraip.in"),
    Party("ForgePeak Thermal Systems LLP", "07AACCF6666F1Z3", "Bawana Industrial Area, Delhi 110039", "+91-11-46006666", "accounts@forgepeak.in"),
    Party("GlintAxis Electronics Pvt Ltd", "36AACCG7777G1Z2", "Plot 72, Hardware Park, Shamshabad, Hyderabad, Telangana 501218", "+91-40-47007777", "billing@glintaxis.in"),
    Party("HexaMotion Castings Pvt Ltd", "19AACCH8888H1Z1", "Dankuni Industrial Belt, Hooghly, West Bengal 712311", "+91-33-48008888", "ap@hexamotion.in"),
    Party("IonGrid Warehouse Solutions LLP", "32AACCI9999I1Z9", "Angamaly Industrial Cluster, Ernakulam, Kerala 683572", "+91-484-4900999", "finance@iongrid.in"),
    Party("Jovian Fleet Tech Pvt Ltd", "23AACCJ1212J1Z8", "Pithampur Sector 3, Dhar, Madhya Pradesh 454775", "+91-7292-401212", "billing@jovianfleet.in"),
    Party("KineticRidge Assemblies Pvt Ltd", "27AACCK1313K1Z7", "Plot 57, Ranjangaon MIDC, Pune, Maharashtra 412220", "+91-2138-401313", "accounts@kineticridge.in"),
    Party("Lumina Rack Infrastructure LLP", "29AACCL1414L1Z6", "KIADB Industrial Area, Nelamangala, Karnataka 562123", "+91-80-41401414", "finance@luminarack.in"),
    Party("Meraki Console Systems Pvt Ltd", "24AACCM1515M1Z5", "Kathwada Industrial Estate, Ahmedabad, Gujarat 382430", "+91-79-41501515", "billing@merakiconsole.in"),
    Party("NorthArc Network Hardware Pvt Ltd", "33AACCN1616N1Z4", "Ambattur Industrial Estate, Chennai, Tamil Nadu 600058", "+91-44-41601616", "ap@northarc.in"),
    Party("Orbis Seating Technologies LLP", "06AACCO1717O1Z3", "Sector 37, Faridabad Industrial Zone, Haryana 121003", "+91-129-4170171", "accounts@orbisseating.in"),
    Party("PrimeSpan Logistics Interfaces Pvt Ltd", "07AACCP1818P1Z2", "Okhla Industrial Area Phase II, New Delhi 110020", "+91-11-41801818", "billing@primespan.in"),
    Party("QuantaForge Cab Systems Pvt Ltd", "36AACCQ1919Q1Z1", "Kompally Industrial Extension, Hyderabad, Telangana 500100", "+91-40-41901919", "finance@quantaforge.in"),
    Party("RivetBridge Dispatch Solutions LLP", "19AACCR2020R1Z9", "Howrah Logistics Hub, Howrah, West Bengal 711302", "+91-33-42002020", "accounts@rivetbridge.in"),
]


BUYERS = [
    "Helios Auto Modules Pvt Ltd",
    "NovaTorque EV Manufacturing Ltd",
    "Saffron Mobility Assembly Park",
    "BluePeak Fleet Services Ltd",
    "Vertex Transit Components Pvt Ltd",
    "Aquila Industrial Controls Ltd",
    "Trionix Mobility Platforms Pvt Ltd",
    "Eastern Drivetrain Consortium",
    "Pioneer Road Systems Ltd",
    "Summit Vehicle Interiors Pvt Ltd",
]


INVOICE_ITEMS = [
    [
        ("Traction Inverter Assembly", "8504", 6, 48500.00, 18),
        ("Motor Controller Harness", "8544", 12, 5850.00, 18),
        ("Coolant Distribution Manifold", "3917", 10, 2240.00, 18),
    ],
    [
        ("Battery Pack Compression Rail", "7616", 20, 3180.00, 18),
        ("Cell Monitoring Board", "8538", 16, 9450.00, 18),
        ("HV Junction Box", "8536", 8, 12400.00, 18),
    ],
    [
        ("Front Subframe Cross Member", "8708", 10, 8625.00, 18),
        ("Steering Knuckle LH", "8708", 14, 4120.00, 18),
        ("Steering Knuckle RH", "8708", 14, 4120.00, 18),
    ],
    [
        ("Telematics Control Unit", "8517", 9, 18850.00, 18),
        ("Antenna Interface Module", "8529", 18, 2140.00, 18),
        ("CAN Gateway Board", "8538", 12, 6640.00, 18),
    ],
    [
        ("Air Intake Resonator", "8421", 25, 1860.00, 18),
        ("Radiator Side Shroud", "3926", 30, 920.00, 18),
        ("Fuse Cover Housing", "3926", 60, 245.00, 18),
    ],
    [
        ("Heat Exchanger Core", "8419", 7, 26400.00, 18),
        ("Thermal Bypass Valve", "8481", 18, 3980.00, 18),
        ("Coolant Pressure Sensor", "9026", 24, 1150.00, 18),
    ],
    [
        ("Cluster Display Assembly", "8528", 11, 14300.00, 18),
        ("Touch Input Controller", "8537", 11, 3870.00, 18),
        ("Backlight Driver Board", "8504", 15, 1740.00, 18),
    ],
    [
        ("Suspension Control Arm", "8708", 22, 2860.00, 18),
        ("Stabilizer Bush Kit", "4016", 30, 480.00, 18),
        ("Wheel Speed Sensor", "9031", 18, 1385.00, 18),
    ],
    [
        ("Warehouse Racking Upright", "7308", 40, 6720.00, 18),
        ("Beam Locking Pair", "8302", 80, 540.00, 18),
        ("Aisle Protection Guard", "7326", 16, 3250.00, 18),
    ],
    [
        ("Fleet Gateway ECU", "8537", 13, 22150.00, 18),
        ("Diagnostics Service Harness", "8544", 20, 1980.00, 18),
        ("Vehicle Data Logger Module", "8523", 12, 11450.00, 18),
    ],
]


BOM_ITEMS = [
    [
        ("10", "KR-CH-201", "Floor Tunnel Stamping", 1, "Nos", "Welded"),
        ("20", "KR-CH-224", "Rear Torsion Beam", 1, "Nos", "Machined"),
        ("30", "KR-CH-238", "Front Mount Bracket", 2, "Nos", "Coated"),
        ("40", "KR-CH-252", "Battery Tray Support", 1, "Nos", "Laser Cut"),
    ],
    [
        ("10", "LR-RK-310", "Rack Upright 2400mm", 4, "Nos", "Powder Coat"),
        ("20", "LR-RK-322", "Load Beam 1800mm", 8, "Nos", "High Tensile"),
        ("30", "LR-RK-345", "Decking Panel", 8, "Nos", "Galvanized"),
        ("40", "LR-RK-351", "Base Plate Assembly", 4, "Nos", "Machined"),
    ],
    [
        ("10", "MC-CS-110", "Console Main Frame", 1, "Nos", "Bent"),
        ("20", "MC-CS-122", "Switch Panel Insert", 1, "Nos", "Silk Print"),
        ("30", "MC-CS-146", "HVAC Vent Housing", 2, "Nos", "Textured"),
        ("40", "MC-CS-153", "Storage Bin Liner", 1, "Nos", "Injection Molded"),
    ],
    [
        ("10", "NA-NH-410", "24 Port Main PCB", 1, "Nos", "SMT"),
        ("20", "NA-NH-432", "Cooling Fan Module", 2, "Nos", "40mm"),
        ("30", "NA-NH-458", "Power Supply Unit", 1, "Nos", "AC Input"),
        ("40", "NA-NH-472", "RJ45 Shield Cage", 24, "Nos", "Stamped"),
    ],
    [
        ("10", "OR-ST-510", "Seat Frame Base", 1, "Nos", "Coated"),
        ("20", "OR-ST-536", "Seat Foam Cushion", 1, "Nos", "Molded"),
        ("30", "OR-ST-548", "Seat Back Foam", 1, "Nos", "Molded"),
        ("40", "OR-ST-562", "Trim Cover Fabric", 1, "Nos", "Charcoal"),
    ],
]


EWAY_CASES = [
    {
        "invoice_no": "FM-GST-2026-2001",
        "ewb_no": "381245670001",
        "vehicle_no": "MH14-GH-4211",
        "from_state": "Pune, Maharashtra",
        "to_state": "Indore, Madhya Pradesh",
        "goods": "Traction Inverter Assembly and related electronics",
        "hsn": "8504",
        "value": 417072.00,
        "weight": "620 Kg",
        "valid_till": "22-Apr-2026",
    },
    {
        "invoice_no": "FM-GST-2026-2006",
        "ewb_no": "381245670002",
        "vehicle_no": "DL1L-ZT-9088",
        "from_state": "New Delhi, Delhi",
        "to_state": "Jaipur, Rajasthan",
        "goods": "Heat Exchanger Core and thermal bypass valves",
        "hsn": "8419",
        "value": 350048.40,
        "weight": "540 Kg",
        "valid_till": "24-Apr-2026",
    },
    {
        "invoice_no": "FM-GST-2026-2010",
        "ewb_no": "381245670003",
        "vehicle_no": "WB23-AX-1164",
        "from_state": "Howrah, West Bengal",
        "to_state": "Jamshedpur, Jharkhand",
        "goods": "Fleet gateway ECU and diagnostics service harness",
        "hsn": "8537",
        "value": 506514.00,
        "weight": "410 Kg",
        "valid_till": "25-Apr-2026",
    },
]


def money(value):
    return f"{value:,.2f}"


def make_invoice_cases():
    cases = []
    for index in range(10):
        supplier = SUPPLIERS[index]
        buyer = BUYERS[index]
        items = []
        for description, hsn, qty, rate, gst in INVOICE_ITEMS[index]:
            taxable = round(qty * rate, 2)
            gst_amount = round(taxable * gst / 100.0, 2)
            items.append(
                {
                    "description": description,
                    "hsn": hsn,
                    "qty": qty,
                    "rate": rate,
                    "taxable": taxable,
                    "gst": gst,
                    "gst_amount": gst_amount,
                }
            )
        taxable_total = round(sum(item["taxable"] for item in items), 2)
        gst_total = round(sum(item["gst_amount"] for item in items), 2)
        grand_total = round(taxable_total + gst_total, 2)
        cases.append(
            {
                "file_name": f"FM_GST_Invoice_{index + 1:02d}.pdf",
                "doc_number": f"FM-GST-2026-{2001 + index}",
                "date": f"{10 + index:02d}-Apr-2026",
                "supplier": supplier,
                "buyer": buyer,
                "buyer_gstin": f"{20 + index:02d}AAACF{4100 + index}K1Z{(index % 9) + 1}",
                "po_number": f"PO-FM-{7600 + index}",
                "payment_terms": f"{15 + (index % 4) * 15} Days",
                "place_of_supply": ["Madhya Pradesh", "Karnataka", "Gujarat", "Tamil Nadu", "Haryana", "Delhi", "Telangana", "West Bengal", "Kerala", "Maharashtra"][index],
                "items": items,
                "taxable_total": taxable_total,
                "gst_total": gst_total,
                "grand_total": grand_total,
            }
        )
    return cases


def make_bom_cases():
    titles = [
        ("KR-ASM-4401", "Electric Chassis Sub Assembly", "R3", "PUNE-TRIM-01"),
        ("LR-ASM-6102", "Warehouse Rack Frame Assembly", "B2", "BLR-WH-04"),
        ("MC-ASM-7303", "Driver Console Module", "C1", "AHM-CAB-02"),
        ("NA-ASM-8404", "Managed Network Switch", "R5", "CHN-ELX-03"),
        ("OR-ASM-9505", "Premium Seating Module", "D4", "FBD-TRIM-09"),
    ]
    cases = []
    for index in range(5):
        supplier = SUPPLIERS[10 + index]
        part_number, product, revision, plant_code = titles[index]
        rows = []
        total_cost = 0.0
        for pos, part_code, description, qty, unit, note in BOM_ITEMS[index]:
            unit_cost = round(850 + (index * 140) + (qty * 37.5) + len(description) * 9.5, 2)
            ext_cost = round(unit_cost * qty, 2)
            total_cost += ext_cost
            rows.append(
                {
                    "position": pos,
                    "part_number": part_code,
                    "description": description,
                    "quantity": qty,
                    "unit": unit,
                    "unit_cost": unit_cost,
                    "extended_cost": ext_cost,
                    "note": note,
                }
            )
        cases.append(
            {
                "file_name": f"FM_BOM_{index + 1:02d}.pdf",
                "doc_number": f"FM-BOM-2026-{3101 + index}",
                "supplier": supplier,
                "product": product,
                "part_number": part_number,
                "revision": revision,
                "plant_code": plant_code,
                "effective_date": f"{14 + index:02d}-Apr-2026",
                "rows": rows,
                "total_cost": round(total_cost, 2),
            }
        )
    return cases


def make_eway_cases(invoice_cases):
    eway_suppliers = SUPPLIERS[15:18]
    cases = []
    for index, template in enumerate(EWAY_CASES):
        supplier = eway_suppliers[index]
        invoice_case = next(case for case in invoice_cases if case["doc_number"] == template["invoice_no"])
        cases.append(
            {
                "file_name": f"FM_Eway_{index + 1:02d}.pdf",
                "supplier": supplier,
                "generated_on": f"{18 + index:02d}-Apr-2026",
                **template,
                "supplier_address": supplier.address,
                "gstin": supplier.gstin,
                "source_invoice_file": invoice_case["file_name"],
            }
        )
    return cases


class StyledPDF(FPDF):
    def header_band(self, title, subtitle=None):
        self.set_fill_color(18, 51, 89)
        self.rect(0, 0, 210, 20, style="F")
        self.set_text_color(255, 255, 255)
        self.set_xy(12, 7)
        self.set_font("Helvetica", "B", 15)
        self.cell(0, 0, title)
        if subtitle:
            self.set_xy(12, 13)
            self.set_font("Helvetica", "", 8)
            self.cell(0, 0, subtitle)
        self.set_text_color(0, 0, 0)
        self.set_y(26)

    def section_title(self, label):
        self.set_fill_color(233, 239, 245)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, label, new_x="LMARGIN", new_y="NEXT", fill=True)

    def kv_row(self, left_label, left_value, right_label="", right_value=""):
        self.set_font("Helvetica", "B", 9)
        self.cell(28, 7, left_label, border=1)
        self.set_font("Helvetica", "", 9)
        self.cell(72, 7, left_value, border=1)
        self.set_font("Helvetica", "B", 9)
        self.cell(28, 7, right_label, border=1)
        self.set_font("Helvetica", "", 9)
        self.cell(62, 7, right_value, border=1, new_x="LMARGIN", new_y="NEXT")


def build_invoice_pdf(case, output_path):
    pdf = StyledPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.header_band("GST TAX INVOICE", "Factory Metrics Benchmark Dataset")

    pdf.section_title("Supplier / Buyer Details")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(95, 7, "Supplier", border=1, fill=False)
    pdf.cell(95, 7, "Buyer", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(95, 5, f"{case['supplier'].name}\n{case['supplier'].address}\nGSTIN: {case['supplier'].gstin}\n{case['supplier'].contact} | {case['supplier'].email}", border=1, new_x="RIGHT", new_y="TOP")
    pdf.multi_cell(95, 5, f"{case['buyer']}\nRegistered Delivery Address\nBuyer GSTIN: {case['buyer_gstin']}\nprocurement@{case['buyer'].split()[0].lower()}.example.com", border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.section_title("Invoice Metadata")
    pdf.kv_row("Invoice No", case["doc_number"], "Invoice Date", case["date"])
    pdf.kv_row("PO Number", case["po_number"], "Payment Terms", case["payment_terms"])
    pdf.kv_row("Place of Supply", case["place_of_supply"], "Currency", "INR")

    pdf.ln(3)
    pdf.section_title("Line Items")
    widths = [14, 74, 18, 24, 24, 16, 20]
    headers = ["HSN", "Description", "Qty", "Rate", "Taxable", "GST%", "GST Amt"]
    pdf.set_font("Helvetica", "B", 9)
    for width, header in zip(widths, headers):
        pdf.cell(width, 8, header, border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for item in case["items"]:
        row = [
            item["hsn"],
            item["description"],
            str(item["qty"]),
            money(item["rate"]),
            money(item["taxable"]),
            str(item["gst"]),
            money(item["gst_amount"]),
        ]
        aligns = ["C", "L", "C", "R", "R", "C", "R"]
        for width, value, align in zip(widths, row, aligns):
            pdf.cell(width, 8, value, border=1, align=align)
        pdf.ln()

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(sum(widths[:-3]), 8, "", border=0)
    pdf.cell(24, 8, "Taxable", border=1)
    pdf.cell(16, 8, "", border=1)
    pdf.cell(20, 8, money(case["taxable_total"]), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(sum(widths[:-3]), 8, "", border=0)
    pdf.cell(24, 8, "GST Total", border=1)
    pdf.cell(16, 8, "", border=1)
    pdf.cell(20, 8, money(case["gst_total"]), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(sum(widths[:-3]), 8, "", border=0)
    pdf.cell(24, 8, "Grand Total", border=1)
    pdf.cell(16, 8, "INR", border=1, align="C")
    pdf.cell(20, 8, money(case["grand_total"]), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 5, "Declaration: This invoice is generated for benchmark testing of retrieval-first document search workflows. Goods are deemed packed and dispatched in good condition.")
    pdf.output(str(output_path))


def build_bom_pdf(case, output_path):
    pdf = StyledPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.header_band("BILL OF MATERIAL", "Factory Metrics Benchmark Dataset")

    pdf.section_title("Assembly Details")
    pdf.kv_row("BOM No", case["doc_number"], "Effective Date", case["effective_date"])
    pdf.kv_row("Product", case["product"], "Assembly Code", case["part_number"])
    pdf.kv_row("Revision", case["revision"], "Plant Code", case["plant_code"])

    pdf.section_title("Manufacturer")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 6, f"{case['supplier'].name}\n{case['supplier'].address}\nGSTIN: {case['supplier'].gstin}\n{case['supplier'].contact} | {case['supplier'].email}", border=1)

    pdf.ln(3)
    pdf.section_title("Component Table")
    widths = [16, 28, 66, 16, 18, 22, 24]
    headers = ["Pos", "Part No", "Description", "Qty", "UOM", "Unit Cost", "Ext Cost"]
    pdf.set_font("Helvetica", "B", 9)
    for width, header in zip(widths, headers):
        pdf.cell(width, 8, header, border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for row in case["rows"]:
        values = [
            row["position"],
            row["part_number"],
            row["description"],
            str(row["quantity"]),
            row["unit"],
            money(row["unit_cost"]),
            money(row["extended_cost"]),
        ]
        aligns = ["C", "L", "L", "C", "C", "R", "R"]
        for width, value, align in zip(widths, values, aligns):
            pdf.cell(width, 8, value, border=1, align=align)
        pdf.ln()

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(sum(widths[:-1]), 8, "Grand Total Cost", border=1, align="R")
    pdf.cell(widths[-1], 8, money(case["total_cost"]), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 5, "Manufacturing note: Dimensions and costing are intended for benchmark evaluation only. Use released revision and plant routing before production.")
    pdf.output(str(output_path))


def build_eway_pdf(case, output_path):
    pdf = StyledPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.header_band("E-WAY BILL", "Factory Metrics Benchmark Dataset")

    pdf.section_title("Document Metadata")
    pdf.kv_row("EWB No", case["ewb_no"], "Generated On", case["generated_on"])
    pdf.kv_row("Invoice No", case["invoice_no"], "Invoice Value", f"Rs. {money(case['value'])}")
    pdf.kv_row("Vehicle No", case["vehicle_no"], "Valid Till", case["valid_till"])

    pdf.section_title("Dispatch Parties")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(95, 7, "From", border=1)
    pdf.cell(95, 7, "To", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(95, 5, f"{case['supplier'].name}\n{case['supplier_address']}\nGSTIN: {case['gstin']}\nDispatch State: {case['from_state']}", border=1, new_x="RIGHT", new_y="TOP")
    pdf.multi_cell(95, 5, f"Consignee Site\nIndustrial Receiving Yard\nDestination State: {case['to_state']}", border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.section_title("Goods Summary")
    widths = [38, 44, 48, 30, 30]
    headers = ["Goods Description", "HSN", "Gross Weight", "Invoice Value", "Vehicle"]
    pdf.set_font("Helvetica", "B", 9)
    for width, header in zip(widths, headers):
        pdf.cell(width, 8, header, border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(widths[0], 14, case["goods"][:30], border=1)
    pdf.cell(widths[1], 14, case["hsn"], border=1, align="C")
    pdf.cell(widths[2], 14, case["weight"], border=1, align="C")
    pdf.cell(widths[3], 14, money(case["value"]), border=1, align="R")
    pdf.cell(widths[4], 14, case["vehicle_no"], border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 5, f"Linked source invoice file for benchmark provenance: {case['source_invoice_file']}")
    pdf.output(str(output_path))


def build_extraction_dataset(invoice_cases, bom_cases, eway_cases):
    dataset = []
    for case in invoice_cases:
        dataset.append(
            {
                "name": case["doc_number"].lower().replace("-", "_"),
                "supplier": case["supplier"].name,
                "file": str((PDF_DIR / case["file_name"]).as_posix()),
                "doc_type": "invoice",
                "expected_fields": {
                    "doc_number": case["doc_number"],
                    "supplier_name": case["supplier"].name,
                    "buyer_name": case["buyer"],
                    "doc_date": case["date"],
                    "amount": case["grand_total"],
                    "po_number": case["po_number"],
                    "payment_terms": case["payment_terms"],
                },
            }
        )
    for case in bom_cases:
        dataset.append(
            {
                "name": case["doc_number"].lower().replace("-", "_"),
                "supplier": case["supplier"].name,
                "file": str((PDF_DIR / case["file_name"]).as_posix()),
                "doc_type": "bom",
                "expected_fields": {
                    "doc_number": case["doc_number"],
                    "supplier_name": case["supplier"].name,
                    "part_number": case["part_number"],
                    "revision": case["revision"],
                    "plant_code": case["plant_code"],
                    "product": case["product"],
                },
                "expected_line_items": [
                    {
                        "part_number": row["part_number"],
                        "description": row["description"],
                    }
                    for row in case["rows"]
                ],
            }
        )
    for case in eway_cases:
        dataset.append(
            {
                "name": case["ewb_no"],
                "supplier": case["supplier"].name,
                "file": str((PDF_DIR / case["file_name"]).as_posix()),
                "doc_type": "invoice",
                "expected_fields": {
                    "doc_number": case["invoice_no"],
                    "supplier_name": case["supplier"].name,
                    "amount": case["value"],
                },
            }
        )
    return dataset


def build_retrieval_dataset(invoice_cases, bom_cases, eway_cases):
    queries = []
    for index, case in enumerate(invoice_cases, start=1):
        top_item = case["items"][0]
        queries.append(
            {
                "name": f"q_fm_invoice_{index:02d}_number",
                "query": case["doc_number"],
                "query_type": "invoice_number",
                "expected_source_filename": case["file_name"],
                "expected_page": 1,
                "expected_doc_truth": case["doc_number"],
                "expected_snippet_contains": [case["doc_number"]],
            }
        )
        queries.append(
            {
                "name": f"q_fm_invoice_{index:02d}_item",
                "query": f"{top_item['description']} invoice {case['supplier'].name.split()[0].lower()}",
                "query_type": "invoice_line_item",
                "expected_source_filename": case["file_name"],
                "expected_page": 1,
                "expected_snippet_contains": [top_item["description"].split()[0], top_item["description"].split()[-1]],
            }
        )
    for index, case in enumerate(bom_cases, start=1):
        component = case["rows"][1]
        queries.append(
            {
                "name": f"q_fm_bom_{index:02d}_product",
                "query": f"{case['product']} bom",
                "query_type": "bom_product",
                "expected_source_filename": case["file_name"],
                "expected_page": 1,
                "expected_snippet_contains": [case["product"].split()[0], case["part_number"]],
            }
        )
        queries.append(
            {
                "name": f"q_fm_bom_{index:02d}_component",
                "query": f"part number for {component['description']}",
                "query_type": "bom_component_lookup",
                "expected_source_filename": case["file_name"],
                "expected_page": 1,
                "expected_snippet_contains": [component["description"].split()[0], component["part_number"]],
            }
        )
    for index, case in enumerate(eway_cases, start=1):
        queries.append(
            {
                "name": f"q_fm_eway_{index:02d}_number",
                "query": case["ewb_no"],
                "query_type": "eway_number",
                "expected_source_filename": case["file_name"],
                "expected_page": 1,
                "expected_snippet_contains": [case["ewb_no"]],
            }
        )
        queries.append(
            {
                "name": f"q_fm_eway_{index:02d}_vehicle",
                "query": f"vehicle number for e-way bill {case['invoice_no']}",
                "query_type": "eway_vehicle",
                "expected_source_filename": case["file_name"],
                "expected_page": 1,
                "expected_snippet_contains": [case["vehicle_no"]],
            }
        )
    return queries


def generate():
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    invoice_cases = make_invoice_cases()
    bom_cases = make_bom_cases()
    eway_cases = make_eway_cases(invoice_cases)

    for case in invoice_cases:
        build_invoice_pdf(case, PDF_DIR / case["file_name"])
    for case in bom_cases:
        build_bom_pdf(case, PDF_DIR / case["file_name"])
    for case in eway_cases:
        build_eway_pdf(case, PDF_DIR / case["file_name"])

    EXTRACTION_DATASET.write_text(json.dumps(build_extraction_dataset(invoice_cases, bom_cases, eway_cases), indent=2))
    RETRIEVAL_DATASET.write_text(json.dumps(build_retrieval_dataset(invoice_cases, bom_cases, eway_cases), indent=2))

    print(f"Created {len(invoice_cases)} GST invoice PDFs in {PDF_DIR}")
    print(f"Created {len(bom_cases)} BOM PDFs in {PDF_DIR}")
    print(f"Created {len(eway_cases)} E-Way Bill PDFs in {PDF_DIR}")
    print(f"Extraction dataset: {EXTRACTION_DATASET}")
    print(f"Retrieval dataset: {RETRIEVAL_DATASET}")


if __name__ == "__main__":
    generate()
