import re
import time
import uuid

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from factory_rag.utils import build_search_text, extract_search_terms, json_ready, normalize_name, normalize_search_text


class PostgresStore:
    def __init__(self, settings):
        self.settings = settings
        self.connection = None

    def _get_connection(self):
        if self.connection is not None and not self.connection.closed:
            return self.connection

        last_error = None
        attempts = max(1, self.settings.postgres_connect_retries)

        for attempt in range(attempts):
            try:
                self.connection = psycopg2.connect(
                    self.settings.postgres_dsn,
                    connect_timeout=self.settings.postgres_connect_timeout,
                )
                return self.connection
            except psycopg2.OperationalError as exc:
                last_error = exc
                self.connection = None
                if attempt < attempts - 1:
                    time.sleep(self.settings.postgres_connect_retry_delay)

        raise last_error

    def ping(self):
        try:
            with self._get_connection().cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception:
            return False

    def _column_exists(self, table_name, column_name):
        connection = self._get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                  AND column_name = %s
                """,
                [table_name, column_name],
            )
            return cursor.fetchone() is not None

    def _index_exists(self, index_name):
        connection = self._get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = %s
                """,
                [index_name],
            )
            return cursor.fetchone() is not None

    def _reset_scaffold_schema(self):
        connection = self._get_connection()
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS query_logs CASCADE")
            cursor.execute("DROP TABLE IF EXISTS chunks CASCADE")
            cursor.execute("DROP TABLE IF EXISTS documents CASCADE")
            cursor.execute("DROP TABLE IF EXISTS suppliers CASCADE")
        connection.commit()

    def init_schema(self):
        if self._column_exists("documents", "id") and not self._column_exists("documents", "checksum"):
            self._reset_scaffold_schema()

        sql = """
        CREATE TABLE IF NOT EXISTS suppliers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            checksum TEXT NOT NULL,
            source_filename TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            doc_number TEXT,
            supplier_id TEXT REFERENCES suppliers(id),
            buyer_name TEXT,
            doc_date DATE,
            amount NUMERIC(14,2),
            currency TEXT NOT NULL DEFAULT 'INR',
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            status TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            page_count INTEGER NOT NULL DEFAULT 0,
            text_length INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            page_number INTEGER NOT NULL,
            section TEXT,
            chunk_text TEXT NOT NULL,
            search_text TEXT NOT NULL DEFAULT '',
            token_count INTEGER NOT NULL DEFAULT 0,
            embedding_model TEXT NOT NULL,
            qdrant_point_id TEXT,
            evidence_type TEXT NOT NULL DEFAULT 'text_chunk',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(doc_id, chunk_index)
        );

        CREATE TABLE IF NOT EXISTS query_logs (
            id TEXT PRIMARY KEY,
            query_text TEXT NOT NULL,
            route_name TEXT NOT NULL,
            filters JSONB NOT NULL DEFAULT '{}'::jsonb,
            latency_ms NUMERIC(12,2) NOT NULL DEFAULT 0,
            result_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """

        connection = self._get_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cursor.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS evidence_type TEXT NOT NULL DEFAULT 'text_chunk'")
            cursor.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS search_text TEXT NOT NULL DEFAULT ''")
        connection.commit()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE chunks c
                SET search_text = LOWER(
                    REGEXP_REPLACE(
                        REPLACE(
                            COALESCE(d.doc_number, '') || ' ' ||
                            COALESCE(s.name, '') || ' ' ||
                            COALESCE(c.section, '') || ' ' ||
                            COALESCE(c.chunk_text, ''),
                            ',',
                            ''
                        ),
                        '\s+',
                        ' ',
                        'g'
                    )
                )
                FROM documents d
                LEFT JOIN suppliers s ON s.id = d.supplier_id
                WHERE c.doc_id = d.id
                  AND (c.search_text = '' OR c.search_text IS NULL)
                """
            )
        connection.commit()

        index_statements = [
            ("idx_documents_checksum", "CREATE INDEX idx_documents_checksum ON documents(checksum)"),
            ("idx_documents_doc_number", "CREATE INDEX idx_documents_doc_number ON documents(doc_number)"),
            ("idx_documents_doc_type", "CREATE INDEX idx_documents_doc_type ON documents(doc_type)"),
            ("idx_documents_doc_date", "CREATE INDEX idx_documents_doc_date ON documents(doc_date)"),
            ("idx_documents_amount", "CREATE INDEX idx_documents_amount ON documents(amount)"),
            ("idx_documents_metadata", "CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata)"),
            ("idx_chunks_doc_id", "CREATE INDEX idx_chunks_doc_id ON chunks(doc_id)"),
            ("idx_chunks_search", "CREATE INDEX idx_chunks_search ON chunks USING GIN(to_tsvector('simple', search_text))"),
        ]

        with connection.cursor() as cursor:
            for index_name, statement in index_statements:
                if not self._index_exists(index_name):
                    cursor.execute(statement)
        connection.commit()

    def _fetch_one(self, sql, params=None):
        connection = self._get_connection()
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params or [])
            row = cursor.fetchone()
        return json_ready(row) if row else None

    def _fetch_all(self, sql, params=None):
        connection = self._get_connection()
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params or [])
            rows = cursor.fetchall()
        return json_ready(rows)

    def _get_or_create_supplier(self, name):
        if not name:
            return None

        normalized_name = normalize_name(name)
        existing = self._fetch_one(
            "SELECT id FROM suppliers WHERE normalized_name = %s",
            [normalized_name],
        )
        if existing:
            return existing["id"]

        supplier_id = str(uuid.uuid4())
        connection = self._get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO suppliers(id, name, normalized_name)
                VALUES (%s, %s, %s)
                """,
                [supplier_id, name, normalized_name],
            )
        connection.commit()
        return supplier_id

    def find_duplicate(self, checksum):
        return self._fetch_one(
            """
            SELECT d.*, s.name AS supplier_name
            FROM documents d
            LEFT JOIN suppliers s ON s.id = d.supplier_id
            WHERE d.checksum = %s
            ORDER BY d.created_at DESC
            LIMIT 1
            """,
            [checksum],
        )

    def _next_version(self, doc_number, source_filename):
        row = self._fetch_one(
            """
            SELECT COALESCE(MAX(version), 0) AS max_version
            FROM documents
            WHERE (doc_number = %s AND %s IS NOT NULL)
               OR source_filename = %s
            """,
            [doc_number, doc_number, source_filename],
        )
        return int(row["max_version"]) + 1

    def create_document(self, record):
        doc_id = str(uuid.uuid4())
        supplier_id = self._get_or_create_supplier(record.get("supplier_name"))
        version = self._next_version(record.get("doc_number"), record["source_filename"])
        metadata = json_ready(record.get("metadata", {}))
        connection = self._get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO documents(
                    id,
                    checksum,
                    source_filename,
                    storage_path,
                    doc_type,
                    doc_number,
                    supplier_id,
                    buyer_name,
                    doc_date,
                    amount,
                    currency,
                    metadata,
                    status,
                    version,
                    page_count,
                    text_length,
                    error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    doc_id,
                    record["checksum"],
                    record["source_filename"],
                    record["storage_path"],
                    record["doc_type"],
                    record.get("doc_number"),
                    supplier_id,
                    record.get("buyer_name"),
                    record.get("doc_date"),
                    record.get("amount"),
                    record.get("currency", "INR"),
                    Json(metadata),
                    record["status"],
                    version,
                    record.get("page_count", 0),
                    record.get("text_length", 0),
                    record.get("error_message"),
                ],
            )
        connection.commit()
        return self.get_document(doc_id)

    def upsert_document(self, doc_id, record):
        supplier_id = self._get_or_create_supplier(record.get("supplier_name"))
        metadata = json_ready(record.get("metadata", {}))
        connection = self._get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE documents
                SET checksum = %s,
                    source_filename = %s,
                    storage_path = %s,
                    doc_type = %s,
                    doc_number = %s,
                    supplier_id = %s,
                    buyer_name = %s,
                    doc_date = %s,
                    amount = %s,
                    currency = %s,
                    metadata = %s,
                    status = %s,
                    page_count = %s,
                    text_length = %s,
                    error_message = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                [
                    record["checksum"],
                    record["source_filename"],
                    record["storage_path"],
                    record["doc_type"],
                    record.get("doc_number"),
                    supplier_id,
                    record.get("buyer_name"),
                    record.get("doc_date"),
                    record.get("amount"),
                    record.get("currency", "INR"),
                    Json(metadata),
                    record["status"],
                    record.get("page_count", 0),
                    record.get("text_length", 0),
                    record.get("error_message"),
                    doc_id,
                ],
            )
        connection.commit()
        return self.get_document(doc_id)

    def update_document(self, doc_id, status, error_message=None, metadata=None):
        connection = self._get_connection()
        with connection.cursor() as cursor:
            if metadata is None:
                cursor.execute(
                    """
                    UPDATE documents
                    SET status = %s,
                        error_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    [status, error_message, doc_id],
                )
            else:
                cursor.execute(
                    """
                    UPDATE documents
                    SET status = %s,
                        error_message = %s,
                        metadata = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    [status, error_message, Json(json_ready(metadata)), doc_id],
                )
        connection.commit()

    def replace_chunks(self, doc_id, chunks, embedding_model):
        connection = self._get_connection()
        rows = []

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM chunks WHERE doc_id = %s", [doc_id])

            for index, chunk in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                search_parts = [
                    chunk.get("doc_number") or "",
                    chunk.get("supplier_name") or "",
                    chunk.get("section") or "",
                    chunk["chunk_text"],
                ]
                search_text = build_search_text(" ".join(part for part in search_parts if part))
                cursor.execute(
                    """
                    INSERT INTO chunks(
                        id,
                        doc_id,
                        chunk_index,
                        page_number,
                        section,
                        chunk_text,
                        search_text,
                        token_count,
                        embedding_model,
                        qdrant_point_id,
                        evidence_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        chunk_id,
                        doc_id,
                        index,
                        chunk["page_number"],
                        chunk.get("section"),
                        chunk["chunk_text"],
                        search_text,
                        chunk.get("token_count", 0),
                        embedding_model,
                        chunk_id,
                        chunk.get("evidence_type", "text_chunk"),
                    ],
                )

                row = dict(chunk)
                row["id"] = chunk_id
                row["doc_id"] = doc_id
                row["chunk_index"] = index
                row["qdrant_point_id"] = chunk_id
                row["embedding_model"] = embedding_model
                row["search_text"] = search_text
                rows.append(row)

        connection.commit()
        return rows

    def exact_lookup_candidates(self, identifier, limit=20):
        return self._fetch_all(
            """
            SELECT
                d.*,
                s.name AS supplier_name,
                CASE
                    WHEN d.doc_number = %s THEN 1.0
                    WHEN d.source_filename = %s THEN 0.98
                    WHEN d.metadata ->> 'invoice no' = %s THEN 0.96
                    WHEN d.metadata ->> 'invoice number' = %s THEN 0.95
                    WHEN d.metadata ->> 'ewb no' = %s THEN 0.9
                    WHEN d.doc_number ILIKE %s THEN 0.88
                    WHEN d.source_filename ILIKE %s THEN 0.86
                    ELSE 0.0
                END AS lookup_score
            FROM documents d
            LEFT JOIN suppliers s ON s.id = d.supplier_id
            WHERE d.doc_number = %s
               OR d.source_filename = %s
               OR d.metadata ->> 'invoice no' = %s
               OR d.metadata ->> 'invoice number' = %s
               OR d.metadata ->> 'ewb no' = %s
               OR d.doc_number ILIKE %s
               OR d.source_filename ILIKE %s
            ORDER BY lookup_score DESC, d.created_at DESC
            LIMIT %s
            """,
            [
                identifier,
                identifier,
                identifier,
                identifier,
                identifier,
                identifier + " %",
                identifier + "%",
                identifier,
                identifier,
                identifier,
                identifier,
                identifier,
                identifier + " %",
                identifier + "%",
                limit,
            ],
        )

    def exact_lookup(self, identifier):
        candidates = self.exact_lookup_candidates(identifier, limit=1)
        if candidates:
            return candidates[0]
        return None

    def get_document(self, doc_id):
        return self._fetch_one(
            """
            SELECT d.*, s.name AS supplier_name
            FROM documents d
            LEFT JOIN suppliers s ON s.id = d.supplier_id
            WHERE d.id = %s
            """,
            [doc_id],
        )

    def search_documents(self, filters, limit=20):
        conditions = []
        params = []

        if filters.get("doc_type"):
            conditions.append("d.doc_type = %s")
            params.append(filters["doc_type"])

        if filters.get("doc_number"):
            conditions.append("d.doc_number = %s")
            params.append(filters["doc_number"])

        if filters.get("supplier_name"):
            conditions.append("s.name ILIKE %s")
            params.append("%" + filters["supplier_name"] + "%")

        if filters.get("amount") is not None:
            conditions.append("d.amount = %s")
            params.append(filters["amount"])

        if filters.get("gstin"):
            conditions.append("(d.metadata ->> 'gstin' = %s OR d.metadata ->> 'buyer_gstin' = %s)")
            params.append(filters["gstin"])
            params.append(filters["gstin"])

        if filters.get("year"):
            conditions.append("EXTRACT(YEAR FROM d.doc_date) = %s")
            params.append(filters["year"])

        if filters.get("month"):
            conditions.append("EXTRACT(MONTH FROM d.doc_date) = %s")
            params.append(filters["month"])

        where_sql = ""
        if conditions:
            where_sql = "WHERE " + " AND ".join(conditions)

        params.append(limit)

        return self._fetch_all(
            f"""
            SELECT d.*, s.name AS supplier_name
            FROM documents d
            LEFT JOIN suppliers s ON s.id = d.supplier_id
            {where_sql}
            ORDER BY d.doc_date DESC NULLS LAST, d.created_at DESC
            LIMIT %s
            """,
            params,
        )

    def get_first_chunks(self, doc_ids):
        if not doc_ids:
            return []

        return self._fetch_all(
            """
            SELECT DISTINCT ON (c.doc_id)
                c.id AS chunk_id,
                c.doc_id,
                c.page_number,
                c.section,
                c.chunk_text,
                c.evidence_type,
                d.doc_number,
                d.doc_type,
                d.source_filename,
                d.storage_path,
                d.doc_date,
                d.amount,
                d.currency,
                d.metadata,
                s.name AS supplier_name
            FROM chunks c
            JOIN documents d ON d.id = c.doc_id
            LEFT JOIN suppliers s ON s.id = d.supplier_id
            WHERE c.doc_id = ANY(%s)
            ORDER BY c.doc_id, c.chunk_index
            """,
            [doc_ids],
        )

    def get_chunks_by_ids(self, chunk_ids):
        if not chunk_ids:
            return []

        return self._fetch_all(
            """
            SELECT
                c.id AS chunk_id,
                c.doc_id,
                c.chunk_index,
                c.page_number,
                c.section,
                c.chunk_text,
                c.evidence_type,
                d.doc_number,
                d.doc_type,
                d.source_filename,
                d.storage_path,
                d.doc_date,
                d.amount,
                d.currency,
                d.metadata,
                s.name AS supplier_name
            FROM chunks c
            JOIN documents d ON d.id = c.doc_id
            LEFT JOIN suppliers s ON s.id = d.supplier_id
            WHERE c.id = ANY(%s)
            """,
            [chunk_ids],
        )

    def keyword_search_chunks(self, query, allowed_doc_ids=None, limit=10):
        normalized_query = normalize_search_text(query)
        terms = extract_search_terms(query)
        text_terms = []
        like_patterns = []

        for term in terms:
            like_patterns.append(f"%{term}%")
            if not re.search(r"\d", term):
                text_terms.append(term)

        text_query = " ".join(text_terms)
        if not like_patterns and normalized_query:
            like_patterns = [f"%{normalized_query}%"]

        conditions = []
        params = [text_query, text_query, like_patterns, text_query, text_query, like_patterns]

        if allowed_doc_ids:
            conditions.append("c.doc_id = ANY(%s)")
            params.append(allowed_doc_ids)

        where_sql = ""
        if conditions:
            where_sql = "AND " + " AND ".join(conditions)

        params.append(limit)

        return self._fetch_all(
            f"""
            SELECT
                c.id AS chunk_id,
                c.doc_id,
                c.page_number,
                c.section,
                c.chunk_text,
                c.evidence_type,
                d.doc_number,
                d.doc_type,
                d.source_filename,
                d.storage_path,
                d.doc_date,
                d.amount,
                d.currency,
                d.metadata,
                s.name AS supplier_name,
                (
                    CASE
                        WHEN %s <> '' THEN ts_rank_cd(
                            to_tsvector('simple', c.search_text),
                            plainto_tsquery('simple', %s)
                        )
                        ELSE 0
                    END
                    + COALESCE(
                        (
                            SELECT SUM(
                                CASE
                                    WHEN pattern ~ '[0-9]' THEN 0.8
                                    ELSE 0.18
                                END
                            )
                            FROM unnest(%s::text[]) AS pattern
                            WHERE c.search_text ILIKE pattern
                        ),
                        0
                    )
                ) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.doc_id
            LEFT JOIN suppliers s ON s.id = d.supplier_id
            WHERE (
                (%s <> '' AND to_tsvector('simple', c.search_text) @@ plainto_tsquery('simple', %s))
                OR c.search_text ILIKE ANY(%s)
            )
            {where_sql}
            ORDER BY score DESC, c.chunk_index
            LIMIT %s
            """,
            params,
        )

    def log_query(self, query_text, route_name, filters, latency_ms, result_count):
        connection = self._get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO query_logs(id, query_text, route_name, filters, latency_ms, result_count)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    str(uuid.uuid4()),
                    query_text,
                    route_name,
                    Json(json_ready(filters)),
                    latency_ms,
                    result_count,
                ],
            )
        connection.commit()
