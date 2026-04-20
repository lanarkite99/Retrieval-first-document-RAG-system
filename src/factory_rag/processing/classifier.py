def classify_document(text):
    lowered = (text or "").lower()

    if "bill of material" in lowered or "bill of materials" in lowered or "\nbom" in lowered:
        return "bom"
    if "tax invoice" in lowered or "invoice no" in lowered or "invoice number" in lowered:
        return "invoice"
    if "receipt" in lowered:
        return "receipt"
    return "unknown"

