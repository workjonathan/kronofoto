from django import forms
from fortepan_us.kronofoto.models import PhotoSphereInfo
from fortepan_us.kronofoto.widgets import InfoPositionWidget
from typing import Any, Tuple, Union, Dict

class InfoPositionField(forms.MultiValueField):
    widget = InfoPositionWidget
    def __init__(self, **kwargs: Any):
        fields = (
            forms.FloatField(),
            forms.FloatField(),
        )
        super().__init__(fields=fields, **kwargs)

    def compress(self, data_list: Tuple[Union[int, float], Union[int, float], Union[int, float]]) -> Dict[str, Union[int, float]]:
        return dict(yaw=data_list[0], pitch=data_list[1])

class PhotoSphereInfoInlineForm(forms.ModelForm):
    position = InfoPositionField(required=True)
    class Meta:
        models = PhotoSphereInfo
        fields = ['text', 'width', 'height']

    def __init__(self, *args: Any, **kwargs: Any):
        if 'instance' in kwargs and kwargs['instance']:
            instance = kwargs['instance']
            initial = dict(
                position=dict(
                    yaw=instance.yaw,
                    pitch=instance.pitch,
                )
            )
            kwargs['initial'] = initial
            super().__init__(
                *args,
                **kwargs,
            )
            position = self.fields['position'].widget
            position.attrs['photosphere'] = instance.photosphere.image.url
            position.attrs['info-text'] = instance.text
            position.attrs['info-width'] = instance.width
        else:
            super().__init__(
                *args,
                **kwargs,
            )

    def save(self, *args: Any, **kwargs: Any) -> PhotoSphereInfo:
        position = self.cleaned_data['position']
        self.instance.yaw = position['yaw']
        self.instance.pitch = position['pitch']
        return super().save(*args, **kwargs)
