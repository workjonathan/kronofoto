from django.views.generic.detail import DetailView
from .basetemplate import BaseTemplateMixin
from ..models.photosphere import PhotoSphere, PhotoSpherePair

class PhotoSphereView(BaseTemplateMixin, DetailView):
    model = PhotoSphere

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        object = context['object']
        context['sphere_data'] = dict(
            sphere_image_url=object.image.url,
            photos=[dict(
                url=position.photo.h700.url,
                height=position.photo.h700.height,
                width=position.photo.h700.width,
                azimuth=position.azimuth,
                inclination=position.inclination,
                distance=position.distance,
             ) for position in PhotoSpherePair.objects.filter(photosphere__pk=object.pk)],
        )
        return context

