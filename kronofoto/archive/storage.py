from django.core.files.storage import DefaultStorage

class OverwriteStorage(DefaultStorage):
    def _save(self, name, contents):
        self.delete(name)
        return super()._save(name, contents)

    def get_available_name(self, name, max_length):
        return name
