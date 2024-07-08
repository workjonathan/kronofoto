from django.core.files.storage import DefaultStorage
from typing import Any

class OverwriteStorage(DefaultStorage):
    def _save(self: Any, name: str, contents: str) -> Any:
        self.delete(name)
        return super()._save(name, contents) # type: ignore

    def get_available_name(self, name: str, max_length: int) -> str:
        return name
