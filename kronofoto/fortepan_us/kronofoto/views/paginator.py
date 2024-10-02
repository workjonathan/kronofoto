from django.core.paginator import Paginator, EmptyPage, Page
from itertools import chain
from django.db.models import QuerySet
from typing import Any, List, Dict, Union, Optional, TYPE_CHECKING, Generator
if TYPE_CHECKING:
    from django.core.paginator import _SupportsPagination


EMPTY_PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='

FAKE_PHOTO = dict(thumbnail=dict(url=EMPTY_PNG, height=75, width=75), is_spacer=True)

class KeysetPaginator(Paginator):
    def __init__(self, object_list: "_SupportsPagination[Any]", per_page: int):
        super().__init__(object_list, per_page)
        self.object_list = object_list
        self.per_page = per_page

    def get_page(self, number: Union[str, None, float, str, Dict[str, Any]]) -> Page:
        assert isinstance(number, dict)
        assert hasattr(self.object_list, "photos_after")
        assert hasattr(self.object_list, "photos_before")
        has_next = None
        has_prev = None
        try:
            if not number['reverse']:
                page_objs = list(self.object_list.photos_after(year=number['year'], id=number['id'])[:self.per_page+1])
                has_next = False
                if len(page_objs) > self.per_page:
                    page_objs.pop()
                    has_next = True
            else:
                page_objs = list(self.object_list.photos_before(year=number['year'], id=number['id'])[:self.per_page+1])
                has_prev = False
                if len(page_objs) > self.per_page:
                    page_objs.pop()
                    has_prev = True
                page_objs.reverse()
        except KeyError:
            page_objs = list(self.object_list[:self.per_page+1])
            if len(page_objs) > self.per_page:
                page_objs.pop()
                has_next = True
        page = KeysetPage(page_objs, number, self, has_prev=has_prev, has_next=has_next, queryset=self.object_list)
        return page
    @property
    def num_pages(self) -> Any:
        return dict(year=2050, id=99999999, reverse=True)

class KeysetPage(Page):
    def __init__(self, object_list: "_SupportsPagination[Any]", number: Dict[str, Any], paginator: Paginator, *args: int, has_prev: Optional[bool], has_next: Optional[bool], queryset: "_SupportsPagination[Any]", **kwargs: int):
        super().__init__(object_list, number, paginator, *args, **kwargs) # type: ignore
        self._has_prev = has_prev
        self._has_next = has_next
        self.queryset = queryset

    def has_previous(self) -> bool:
        if self.object_list and self._has_prev == None:
            object = self.object_list[0]
            assert hasattr(self.queryset, 'photos_before')
            self._has_prev = self.queryset.photos_before(year=object.year, id=object.id).exists()
        return self._has_prev or False

    def has_next(self) -> bool:
        if self.object_list and self._has_next == None:
            object = self.object_list[-1]
            assert hasattr(self.queryset, 'photos_after')
            self._has_next = self.queryset.photos_after(year=object.year, id=object.id).exists()
        return self._has_next or False

    def previous_page_number(self) -> Any:
        object = self.object_list[0]
        return dict(year=object.year, id=object.id, reverse=True)

    def next_page_number(self) -> Any:
        object = self.object_list[-1]
        return dict(year=object.year, id=object.id, reverse=False)


    def start_index(self) -> Any:
        return None
    def end_index(self) -> Any:
        return None

class FakeTimelinePage(Page):
    def __init__(self) -> None:
        pass
    def __iter__(self) -> Generator:
        yield from []

    object_list = [FAKE_PHOTO] * 10

    def find(self, pk: int) -> None:
        raise KeyError(pk)

class TimelinePage(Page):
    def find(self, pk: int) -> Any:
        for i, p in enumerate(self):
            if p.id == pk:
                p.active = True
                p.row_number = self.start_index() + i - 1
                return p
        raise KeyError(pk)


class PageSelection:
    def __init__(self, pages: List):
        self.pages = pages

    def find(self, pk: int) -> Any:
        return self.main_page().find(pk)

    def main_page(self) -> TimelinePage:
        return self.pages[len(self.pages)//2]

    def photos(self) -> Generator:
        last = None
        for p in chain(*self.pages):
            yield p
            if last:
                p.previous = last
                last.next = p
            last = p


class TimelinePaginator(Paginator):
    def get_pageselection(self, pages: List) -> PageSelection:
        return PageSelection(pages)

    def get_pages(self, number: int, buffer: int=1) -> PageSelection:
        return PageSelection([self.get_page(n) for n in range(number-buffer, number+buffer+1)])

    def get_page(self, number: Union[int, float, str, None]) -> Page:
        assert isinstance(number, int)
        try:
            page = super().page(number)
            for item in page:
                item.page = page
            return page
        except EmptyPage:
            return FakeTimelinePage()

    def _get_page(self, *args: Any, **kwargs: Any) -> TimelinePage:
        return TimelinePage(*args, **kwargs)
