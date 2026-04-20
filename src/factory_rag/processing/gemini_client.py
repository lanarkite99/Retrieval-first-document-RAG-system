import json
from urllib import error, request


class GeminiClient:
    def __init__(self, settings):
        self.settings = settings

    def is_configured(self):
        return bool(self.settings.gemini_api_key)

    def generate_answer(self, query, hits):
        if not self.is_configured() or not hits:
            return None

        context_blocks = []
        for index, hit in enumerate(hits, start=1):
            citation = hit.get("citation") or {}
            confidence = hit.get("confidence") or {}
            context_blocks.append(
                "\n".join(
                    [
                        f"Hit {index}",
                        f"doc_number: {hit.get('doc_number')}",
                        f"file: {citation.get('file_name')}",
                        f"storage_path: {citation.get('storage_path')}",
                        f"supplier: {hit.get('supplier_name')}",
                        f"date: {hit.get('doc_date')}",
                        f"amount: {hit.get('amount')} {hit.get('currency')}",
                        f"page: {citation.get('page')}",
                        f"section: {citation.get('section')}",
                        f"confidence: {confidence.get('label')} ({confidence.get('score')})",
                        f"match_reasons: {', '.join(hit.get('match_reasons') or [])}",
                        f"snippet: {hit.get('snippet')}",
                    ]
                )
            )

        prompt = "\n\n".join(
            [
                "Answer the user only from the retrieved document evidence.",
                "If the evidence is insufficient, say that clearly.",
                "Prefer naming the matching document, page, and file when helpful.",
                f"User query: {query}",
                "Retrieved evidence:",
                "\n\n".join(context_blocks),
            ]
        )

        payload = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": "You answer document retrieval questions for factory records. Be factual, brief, and citation-oriented."
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": self.settings.llm_temperature,
                "maxOutputTokens": self.settings.llm_max_output_tokens,
            },
        }

        data = self._post(f"models/{self.settings.llm_model}:generateContent", payload)
        if not data or data.get("error"):
            return None

        candidates = data.get("candidates") or []
        if not candidates:
            return None

        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        lines = []
        for part in parts:
            text = part.get("text")
            if text:
                lines.append(text.strip())

        answer = "\n".join(lines).strip()
        return answer or None

    def embed_documents(self, texts):
        return self._embed_many(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text):
        vectors = self._embed_many([text], "RETRIEVAL_QUERY")
        if not vectors:
            return None
        return vectors[0]

    def _embed_many(self, texts, task_type):
        if not self.is_configured() or not texts:
            return []

        vectors = []
        for text in texts:
            payload = {
                "model": f"models/{self.settings.gemini_embedding_model}",
                "content": {
                    "parts": [{"text": text}],
                },
                "taskType": task_type,
                "outputDimensionality": self.settings.vector_size,
            }
            data = self._post(
                f"models/{self.settings.gemini_embedding_model}:embedContent",
                payload,
            )
            if not data or data.get("error"):
                return []

            embedding = data.get("embedding") or {}
            values = embedding.get("values") or []
            if not values:
                return []

            vectors.append(values)

        return vectors

    def _post(self, path, payload):
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.settings.gemini_api_base}/{path}",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.settings.gemini_api_key,
            },
        )

        try:
            with request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            return {"error": details, "status": exc.code}
        except Exception:
            return None
