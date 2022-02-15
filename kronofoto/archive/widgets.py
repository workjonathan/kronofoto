from django.forms.widgets import NumberInput

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

class PositioningWidget(NumberInput):
    sphere_width = 600
    sphere_height = 800

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if 'photo' in self.attrs:
            self.template_name = 'archive/widgets/positioning.html'
            context['sphere_image'] = self.attrs['photosphere']
            context['photo'] = self.attrs['photo']
            context['photo_h'] = self.attrs['photo_h']
            context['photo_w'] = self.attrs['photo_w']
            context['init_azimuth'] = self.attrs['azimuth']
            context['init_inclination'] = self.attrs['inclination']
            context['init_distance'] = self.attrs['distance']
            context['id'] = attrs['id']
            context['sphere_width'] = self.sphere_width
            context['sphere_height'] = self.sphere_height
            context['module'] = 'archive_positioning'
        return context
