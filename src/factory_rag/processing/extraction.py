import fitz

from factory_rag.utils import clean_text


def extract_pdf(pdf_path):
    document = fitz.open(pdf_path)
    pages = []
    page_number = 1

    for page in document:
        text = clean_text(page.get_text("text"))
        pages.append(
            {
                "page_number": page_number,
                "text": text,
                "text_length": len(text),
            }
        )
        page_number += 1

    full_text_parts = []
    for page in pages:
        full_text_parts.append(page["text"])

    return {
        "pages": pages,
        "page_count": len(pages),
        "full_text": "\n\n".join(full_text_parts).strip(),
    }

