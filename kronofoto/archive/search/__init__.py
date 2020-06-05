
def evaluate(expression, qs):
    return qs.filter(expression.evaluate()).distinct()


def sort(expression, qs):
    if len(qs):
        return [photo for (s, _, _, photo) in reversed(sorted((expression.score(photo, False), -photo.year, -photo.id, photo) for photo in qs)) if s > 0]
    else:
        return qs
