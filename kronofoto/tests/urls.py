from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .test_agreement import AgreementFormView, Agreement, UserAgreementCheck, AgreementForm
from .models import UserAgreement

testpatterns = [
    path('postagreement/<int:pk>', AgreementFormView.as_view(model=Agreement, user_agreement_model=UserAgreement, form_class=AgreementForm, template_name='tests/agreement.html'), name="tests/agreement.html"),
    path('agreementcheck/<int:pk>', UserAgreementCheck.as_view(pattern_name="tests/agreement.html")),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('fortepan_us.kronofoto.auth.urls')),
    path('test/', include(testpatterns)),
    path('kf/', include('fortepan_us.kronofoto.urls', namespace="kronofoto")),
]
