from django.forms.widgets import NumberInput, Widget, SelectMultiple, ClearableFileInput, CheckboxSelectMultiple, Select
from django.forms import MultiWidget, HiddenInput
from django.db.models import QuerySet
from typing import Dict, Any, List, Union, Optional, Mapping
from django.utils.datastructures import MultiValueDict


class Select2(Select):
    def __init__(self, queryset: QuerySet):
        self.queryset = queryset
        super().__init__()

    def get_context(self, name: str, value: Any, attrs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if value is None or not isinstance(value, int):
            self.choices = []
        else:
            self.choices = [(obj.id, str(obj)) for obj in self.queryset.filter(id=value)]
        return super().get_context(name, value, attrs)

    def value_from_datadict(self, data: Mapping[str, Any], files: "MultiValueDict[str, Any]", name: str) -> Any:
        r = super().value_from_datadict(data, files, name)
        if r:
            return r
        else:
            return None


class ImagePreviewClearableFileInput(ClearableFileInput):
    template_name = "kronofoto/widgets/image_preview_clearable_file_input.html"

    def __init__(self, *args: Any, img_attrs: Optional[Dict[str, Any]]=None, **kwargs: Any):
        self.img_attrs = img_attrs or {}
        super().__init__(*args, **kwargs)

    def get_context(self, name: str, value: Any, attrs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        context = super().get_context(name, value, attrs)
        context['img_attrs'] = self.img_attrs
        return context

class SelectMultipleTerms(CheckboxSelectMultiple):
    template_name = "kronofoto/widgets/selectmultipleterms.html"

class AutocompleteWidget(Widget):
    template_name = "kronofoto/widgets/autocomplete.html"

    def __init__(self, *args: Any, url: str, **kwargs: Any):
        self.url = url
        super().__init__(*args, **kwargs)

    def get_context(self, name: str, value: Any, attrs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        context = super().get_context(name, value, attrs)
        context['widget']['type'] = 'text'
        context['url'] = self.url
        return context

class RecaptchaWidget(Widget):
    template_name = 'kronofoto/widgets/captcha.html'

    def get_context(self, name: str, value: Any, attrs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        context = super().get_context(name, value, attrs)
        context['public_key'] = self.attrs['data-sitekey']
        return context

    def value_from_datadict(self, data: Mapping[str, Any], files: "MultiValueDict[str, Any]", name: str) -> Any:
        return data.get(name, None)

class HeadingWidget(NumberInput):
    sphere_width = 600
    sphere_height = 400
    template_name = 'kronofoto/widgets/heading.html'

    def get_context(self, name: str, value: Any, attrs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        assert attrs
        context = super().get_context(name, value, attrs)
        self.template_name = 'kronofoto/widgets/heading.html'
        context['sphere_image'] = self.attrs['photo']
        context['id'] = attrs['id']
        context['sphere_width'] = self.sphere_width
        context['sphere_height'] = self.sphere_height
        context['module'] = 'archive_heading'
        try:
            context['pan'] = (float(value)-90) / 180 * 3.1415
        except ValueError:
            context['pan'] = ""
        return context

class InfoPositionWidget(MultiWidget):
    sphere_width = 600
    sphere_height = 800
    def __init__(self, attrs: Optional[Dict[str, Any]]=None, **kwargs: Any):
        widgets = (
            NumberInput(attrs=dict(anglename="yaw")),
            NumberInput(attrs=dict(anglename="pitch")),
        )
        super().__init__(widgets=widgets, attrs=attrs, **kwargs)

    def get_context(self, name: str, value: Any, attrs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        assert attrs
        context = super().get_context(name, value, attrs)
        if 'photosphere' in self.attrs:
            self.template_name = 'kronofoto/widgets/info-position-widget.html'
            context['sphere_image'] = self.attrs['photosphere']
            context['info_text'] = self.attrs['info-text']
            context['info_width'] = self.attrs['info-width']
            context['id'] = attrs['id']
            context['sphere_width'] = self.sphere_width
            context['sphere_height'] = self.sphere_height
        return context

    def decompress(self, value: Any) -> List[int]:
        if value:
            return [value['yaw'], value['pitch']]
        return [0, 0]

class PositioningWidget(MultiWidget):
    sphere_width = 600
    sphere_height = 800

    def __init__(self, attrs: Optional[Dict[str, Any]]=None, **kwargs: Any):
        widgets = (
            NumberInput(attrs=dict(anglename="azimuth")),
            NumberInput(attrs=dict(anglename="inclination")),
            NumberInput(attrs=dict(anglename="distance")),
        )
        super().__init__(widgets=widgets, attrs=attrs, **kwargs)


    def get_context(self, name: str, value: Any, attrs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        assert attrs
        context = super().get_context(name, value, attrs)
        if 'photosphere' in self.attrs:
            self.template_name = 'kronofoto/widgets/positioning.html'
            context['sphere_image'] = self.attrs['photosphere']
            context['photo'] = self.attrs['photo']
            context['photo_h'] = self.attrs['photo_h']
            context['photo_w'] = self.attrs['photo_w']
            context['id'] = attrs['id']
            context['sphere_width'] = self.sphere_width
            context['sphere_height'] = self.sphere_height
        return context

    def decompress(self, value: Any) -> List[int]:
        if value:
            return [value['azimuth'], value['inclination'], value['distance']]
        return [0, 0, 500]
