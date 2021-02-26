from archive.models import Photo
from django.db.models import Sum, FloatField, Max

def evaluate(expression, qs):
    return expression.as_search(qs)
