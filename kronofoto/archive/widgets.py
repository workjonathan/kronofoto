from django.forms.widgets import NumberInput
from django.forms import MultiWidget, HiddenInput

class HeadingWidget(NumberInput):
    sphere_width = 600
    sphere_height = 400

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if 'photo' in self.attrs:
            self.template_name = 'archive/widgets/heading.html'
            context['sphere_image'] = self.attrs['photo']
            context['id'] = attrs['id']
            context['sphere_width'] = self.sphere_width
            context['sphere_height'] = self.sphere_height
            context['module'] = 'archive_heading'
        return context

class PositioningWidget(MultiWidget):
    sphere_width = 600
    sphere_height = 800
    template_name = 'archive/widgets/positioning.html'

    def __init__(self, attrs=None, **kwargs):
        widgets = (
            NumberInput(attrs=dict(anglename="azimuth")),
            NumberInput(attrs=dict(anglename="inclination")),
            NumberInput(attrs=dict(anglename="distance")),
        )
        super().__init__(widgets=widgets, attrs=attrs, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if 'photo' in self.attrs:
            context['sphere_image'] = self.attrs['photosphere']
            context['photo'] = self.attrs['photo']
            context['photo_h'] = self.attrs['photo_h']
            context['photo_w'] = self.attrs['photo_w']
            context['id'] = attrs['id']
            context['sphere_width'] = self.sphere_width
            context['sphere_height'] = self.sphere_height
        return context

    def decompress(self, value):
        if value:
            return [value['azimuth'], value['inclination'], value['distance']]
        return [0, 0, 500]
