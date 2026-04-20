import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from factory_rag.runtime import get_runtime


if __name__ == "__main__":
    runtime = get_runtime()
    results = runtime.ingestion_service.ingest_path(runtime.settings.data_dir)
    for item in results:
        print(item)
