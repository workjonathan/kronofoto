from archive.models import Photo
from django.db.models import Sum, FloatField

def evaluate(expression, qs):
    f2 = expression.filter2()
    f1 = expression.filter1()
    q = (f1 | f2) if f1 and f2 else f1 if f1 else f2

    return (
        qs.filter(q)
            .annotate(
                **{k: Sum(v, output_field=FloatField()) for (k, v) in expression.annotations1().items()}
            )
            .defer(*(f.name for f in Photo._meta.fields))
            .annotate(relevance=expression.scoreF(False))
            .filter(relevance__gt=0)
            .order_by('-relevance', 'year', 'id')
    )


def sort(expression, qs):
    return qs
