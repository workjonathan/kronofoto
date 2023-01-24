from django.core.paginator import Paginator, EmptyPage, Page
from itertools import chain


EMPTY_PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='

FAKE_PHOTO = dict(thumbnail=dict(url=EMPTY_PNG, height=75, width=75))


class FakeTimelinePage:
    def __iter__(self):
        yield from []

    object_list = [FAKE_PHOTO] * 10

    def find(self, pk):
        raise KeyError(pk)

class TimelinePage(Page):
    def find(self, pk):
        for i, p in enumerate(self):
            if p.id == pk:
                p.active = True
                p.row_number = self.start_index() + i - 1
                return p
        raise KeyError(pk)


class PageSelection:
    def __init__(self, pages):
        self.pages = pages

    def find(self, pk):
        return self.main_page().find(pk)

    def main_page(self):
        return self.pages[len(self.pages)//2]

    def photos(self):
        last = None
        for p in chain(*self.pages):
            yield p
            if last:
                p.previous = last
                last.next = p
            last = p


class TimelinePaginator(Paginator):
    def get_pageselection(self, pages):
        return PageSelection(pages)

    def get_pages(self, number, buffer=1):
        return PageSelection([self.get_page(n) for n in range(number-buffer, number+buffer+1)])

    def get_page(self, number):
        try:
            page = super().page(number)
            for item in page:
                item.page = page
            return page
        except EmptyPage:
            return FakeTimelinePage()

    def _get_page(self, *args, **kwargs):
        return TimelinePage(*args, **kwargs)
