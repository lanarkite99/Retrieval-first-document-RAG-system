import shutil
from pathlib import Path


class DocumentStore:
    def __init__(self, settings):
        self.settings = settings
        self.settings.ensure_dirs()

    def store(self, source_path, checksum):
        source_path = Path(source_path)
        target_name = checksum + source_path.suffix.lower()
        target_path = self.settings.storage_dir / target_name

        if not target_path.exists():
            shutil.copy2(source_path, target_path)

        return str(target_path)

