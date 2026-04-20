from pathlib import Path

from factory_rag.chunking import build_chunks
from factory_rag.classifier import classify_document
from factory_rag.extraction import extract_pdf
from factory_rag.metadata import extract_metadata
from factory_rag.utils import clean_text, sha256_file


class IngestionService:
    def __init__(self, settings, db, embedder, qdrant_store, opensearch_store, document_store, metrics):
        self.settings = settings
        self.db = db
        self.embedder = embedder
        self.qdrant_store = qdrant_store
        self.opensearch_store = opensearch_store
        self.document_store = document_store
        self.metrics = metrics

    def bootstrap(self):
        self.db.init_schema()

    def ingest_path(self, input_path, force=False):
        input_path = Path(input_path)
        self.bootstrap()

        if input_path.is_file():
            return [self.ingest_file(input_path, force=force)]

        results = []
        for file_path in sorted(input_path.glob("*.pdf")):
            results.append(self.ingest_file(file_path, force=force))
        return results

    def ingest_file(self, file_path, force=False):
        file_path = Path(file_path)
        checksum = sha256_file(file_path)
        duplicate = self.db.find_duplicate(checksum)
        if duplicate and duplicate["status"] == "processed" and not force:
            self.metrics.record_ingest("duplicate", file_path.name)
            return {
                "status": "duplicate",
                "doc_id": duplicate["id"],
                "source_filename": duplicate["source_filename"],
                "doc_number": duplicate.get("doc_number"),
            }

        document_row = None

        try:
            extracted = extract_pdf(file_path)
            doc_type = classify_document(extracted["full_text"])
            metadata = extract_metadata(doc_type, extracted["full_text"])
            storage_path = self.document_store.store(file_path, checksum)

            record = {
                "checksum": checksum,
                "source_filename": file_path.name,
                "storage_path": storage_path,
                "doc_type": doc_type,
                "doc_number": metadata.get("doc_number"),
                "supplier_name": metadata.get("supplier_name"),
                "buyer_name": metadata.get("buyer_name"),
                "doc_date": metadata.get("doc_date"),
                "amount": metadata.get("amount"),
                "currency": metadata.get("currency", "INR"),
                "metadata": metadata,
                "page_count": extracted["page_count"],
                "text_length": len(extracted["full_text"]),
                "status": "processing",
            }

            if duplicate and force:
                self.qdrant_store.delete_document_chunks(duplicate["id"])
                self.opensearch_store.delete_document_chunks(duplicate["id"])
                document_row = self.db.upsert_document(duplicate["id"], record)
            else:
                document_row = self.db.create_document(record)

            chunks = build_chunks(
                extracted["pages"],
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
            )
            chunks.extend(self._build_metadata_chunks(metadata, extracted["pages"]))

            for chunk in chunks:
                chunk["doc_type"] = document_row["doc_type"]
                chunk["doc_number"] = document_row.get("doc_number")
                chunk["supplier_name"] = document_row.get("supplier_name")

            vectors = self.embedder.embed_texts([chunk["chunk_text"] for chunk in chunks])
            chunk_rows = self.db.replace_chunks(document_row["id"], chunks, self.embedder.backend_name)

            vector_indexed = self.qdrant_store.upsert_chunks(chunk_rows, vectors)
            keyword_indexed = self.opensearch_store.index_chunks(chunk_rows)

            metadata["index_status"] = {
                "vector": "ready" if vector_indexed else "unavailable",
                "keyword": "ready" if keyword_indexed else "unavailable",
            }

            status = "processed" if vector_indexed and keyword_indexed else "partial"
            self.db.update_document(document_row["id"], status=status, metadata=metadata)
            self.metrics.record_ingest(status, file_path.name)

            return {
                "status": status,
                "doc_id": document_row["id"],
                "doc_number": document_row.get("doc_number"),
                "doc_type": document_row["doc_type"],
                "chunks": len(chunk_rows),
                "embedding_backend": self.embedder.backend_name,
                "index_status": metadata["index_status"],
            }
        except Exception as exc:
            message = str(exc)
            if document_row:
                self.db.update_document(document_row["id"], status="failed", error_message=message)
            self.metrics.record_ingest("failed", file_path.name)
            self.metrics.record_error(message)
            return {
                "status": "failed",
                "source_filename": file_path.name,
                "error": message,
            }

    def _build_metadata_chunks(self, metadata, pages):
        chunks = []
        header_chunk = self._build_header_chunk(metadata, pages)
        if header_chunk:
            chunks.append(header_chunk)

        line_items = metadata.get("line_items") or []
        if not line_items:
            return chunks

        page_number = self._default_page_number(pages)
        section = self._default_section(metadata, pages)
        product = metadata.get("extra_fields", {}).get("product") or metadata.get("part_number") or metadata.get("doc_number")

        for item in line_items:
            row_text = self._format_line_item_chunk(item, product)
            if not row_text:
                continue
            chunks.append(
                {
                    "page_number": page_number,
                    "section": section,
                    "chunk_text": row_text,
                    "token_count": len(row_text.split()),
                    "evidence_type": "table_row",
                }
            )

        return chunks

    def _build_header_chunk(self, metadata, pages):
        fields = [
            ("Document Type", metadata.get("doc_type")),
            ("Document Number", metadata.get("doc_number")),
            ("Supplier", metadata.get("supplier_name")),
            ("Buyer", metadata.get("buyer_name")),
            ("Date", metadata.get("doc_date")),
            ("Amount", metadata.get("amount")),
            ("Currency", metadata.get("currency")),
            ("Part Number", metadata.get("part_number")),
            ("Revision", metadata.get("revision")),
        ]

        extra_fields = metadata.get("extra_fields") or {}
        for key in ["product", "invoice no", "ewb no", "vehicle no", "goods description", "place of supply"]:
            value = extra_fields.get(key)
            if value:
                fields.append((key.title(), value))

        parts = []
        for label, value in fields:
            if value in (None, ""):
                continue
            parts.append(f"{label}: {value}")

        if not parts:
            return None

        text = " | ".join(parts)
        return {
            "page_number": self._default_page_number(pages),
            "section": self._default_section(metadata, pages),
            "chunk_text": text,
            "token_count": len(text.split()),
            "evidence_type": "header_field",
        }

    def _build_line_chunks(self, metadata, pages):
        chunks = []
        seen = set()

        for page in pages:
            page_number = page.get("page_number", 1)
            section = self._page_section(page, metadata)
            for line in self._iter_candidate_lines(page.get("text") or ""):
                if line in seen:
                    continue
                seen.add(line)
                chunks.append(
                    {
                        "page_number": page_number,
                        "section": section,
                        "chunk_text": line,
                        "token_count": len(line.split()),
                        "evidence_type": "line_chunk",
                    }
                )
        return chunks

    def _iter_candidate_lines(self, page_text):
        for raw_line in page_text.splitlines():
            line = clean_text(raw_line)
            if len(line) < 6:
                continue
            if len(line) > 320:
                continue
            if not any(character.isalnum() for character in line):
                continue
            if line.lower() in {"page 1", "page 2", "page 3"}:
                continue
            yield line

    def _format_line_item_chunk(self, item, product=None):
        fields = []
        if product:
            fields.append(("Product", product))

        fields.extend(
            [
                ("Position", item.get("item_no")),
                ("Material Code", item.get("part_number")),
                ("Description", item.get("description")),
                ("Quantity", item.get("quantity")),
                ("Unit", item.get("unit")),
                ("Revision", item.get("revision")),
                ("Note", item.get("remarks")),
            ]
        )

        parts = []
        for label, value in fields:
            if value in (None, ""):
                continue
            parts.append(f"{label}: {value}")
        return " | ".join(parts)

    def _default_page_number(self, pages):
        if not pages:
            return 1
        return pages[0].get("page_number", 1)

    def _default_section(self, metadata, pages):
        if pages:
            first_page = pages[0].get("text") or ""
            if "BILL OF MATERIAL" in first_page.upper():
                return "BILL OF MATERIAL"
        return (metadata.get("doc_type") or "document").upper()

    def _page_section(self, page, metadata):
        page_text = page.get("text") or ""
        for line in page_text.splitlines():
            cleaned = clean_text(line)
            if cleaned:
                return cleaned[:80]
        return self._default_section(metadata, [page])
