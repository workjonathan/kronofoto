import hashlib
from django.contrib.auth.models import User
from django.db.models import QuerySet
from typing import Any


class CollectionQuery:
    def __init__(self, expr: Any, user: User):
        self.expr = expr
        self.user = user

    def filter(self, qs: QuerySet) -> QuerySet:
        if not self.expr:
            return qs.filter(year__isnull=False, is_published=True)
        if self.expr.is_collection():
            return self.expr.as_collection(qs, self.user)
        else:
            return self.expr.as_search(qs, self.user)

    def make_key(self, s: str) -> str:
        m = hashlib.md5()
        m.update(s.encode('utf-8'))
        return m.hexdigest()

    def cache_encoding(self) -> str:
        return self.make_key(repr(self.expr))

    def __str__(self) -> str:
        if not self.expr:
            return "All Photos"
        return str(self.expr.description())


