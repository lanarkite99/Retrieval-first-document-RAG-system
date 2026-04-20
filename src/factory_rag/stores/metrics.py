from datetime import datetime


class Metrics:
    def __init__(self):
        self.query_count = 0
        self.cache_hits = 0
        self.route_counts = {}
        self.ingest_count = 0
        self.ingest_status_counts = {}
        self.last_query = None
        self.last_ingest = None
        self.last_error = None
        self.total_query_latency_ms = 0.0

    def record_query(self, route, latency_ms, cache_hit):
        self.query_count += 1
        self.total_query_latency_ms += latency_ms
        self.route_counts[route] = self.route_counts.get(route, 0) + 1
        if cache_hit:
            self.cache_hits += 1
        self.last_query = datetime.utcnow().isoformat()

    def record_ingest(self, status, file_name):
        self.ingest_count += 1
        self.ingest_status_counts[status] = self.ingest_status_counts.get(status, 0) + 1
        self.last_ingest = {
            "file_name": file_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def record_error(self, message):
        self.last_error = {
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def snapshot(self):
        average_latency = 0.0
        if self.query_count:
            average_latency = self.total_query_latency_ms / self.query_count
        return {
            "query_count": self.query_count,
            "cache_hits": self.cache_hits,
            "route_counts": dict(self.route_counts),
            "ingest_count": self.ingest_count,
            "ingest_status_counts": dict(self.ingest_status_counts),
            "last_query": self.last_query,
            "last_ingest": self.last_ingest,
            "last_error": self.last_error,
            "average_query_latency_ms": round(average_latency, 2),
        }

