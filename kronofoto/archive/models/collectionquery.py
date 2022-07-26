import hashlib


class CollectionQuery:
    def __init__(self, expr, user):
        self.expr = expr
        self.user = user

    def filter(self, qs):
        if not self.expr:
            return qs.filter(year__isnull=False, is_published=True)
        if self.expr.is_collection():
            return self.expr.as_collection(qs, self.user)
        else:
            return self.expr.as_search(qs, self.user)

    def make_key(self, s):
        m = hashlib.md5()
        m.update(s.encode('utf-8'))
        return m.hexdigest()

    def cache_encoding(self):
        return self.make_key(repr(self.expr))

    def __str__(self):
        if not self.expr:
            return "All Photos"
        return str(self.expr.description())


