from django.test import RequestFactory, SimpleTestCase, tag, Client
from django.core import mail
from django.contrib.auth.models import AnonymousUser, User
from hypothesis import given, strategies as st, note, settings
from hypothesis.extra.django import TestCase, from_model
from django.urls import reverse
from ..reverse import reverse as krono_reverse
from ..views.grid import GridView
from .util import MockQuerySet, MockPhoto, photos, tags, donors, archives, terms, tags
from ..models.photo import PhotoTag, Photo
from ..models.tag import Tag
from ..models.term import Term
from ..models.photosphere import PhotoSphere, PhotoSpherePair
import re

@tag("newtests")
class GridTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @given(
        from_model(
            PhotoTag,
            tag=from_model(Tag, tag=st.just("silly"), slug=st.just("silly")),
            accepted=st.just(True),
            photo=photos(),
        ),
        st.builds(MockQuerySet, st.lists(st.builds(MockPhoto), min_size=0, unique_by=lambda p: p.id)),
    )
    def testContextData(self, phototag, object_list):
        request = self.factory.get(reverse('kronofoto:gridview'))
        request.user = AnonymousUser()
        view = GridView()
        view.setup(request)
        context = view.get_context_data(object_list=object_list)
        self.assertGreaterEqual(view.paginate_by, len(context['page_obj']))
        self.assertEqual(context['noresults'], len(object_list)==0)

@tag("integration")
class ViewIntegrationTests(TestCase):
    @settings(deadline=4000)#, max_examples=5)
    @given(
        st.lists(archives(), min_size=1).flatmap(lambda archives:
        st.lists(terms()).flatmap(lambda terms:
        st.lists(tags(tag=st.text(min_size=1).filter(lambda tag: len(tag.tag.strip()) and len(tag.slug) and 0 == sum(1 for c in tag.tag if c in ['\r', '\n', "'", "\\"])))).flatmap(lambda tags:
        st.lists(donors(archive=st.sampled_from(archives)), min_size=1).flatmap(lambda donors:
        st.lists(photos(
            is_published=st.just(True),
            year=st.integers(min_value=1800, max_value=1999),
            archive=st.sampled_from(archives),
            local_context_id=st.just(None),
            donor=st.sampled_from(donors)), min_size=1).flatmap(lambda photos:
        st.lists(from_model(Photo.terms.through, photo=st.sampled_from(photos), term=st.sampled_from(terms)) if terms else st.none()).flatmap(lambda _:
        st.lists(from_model(Photo.tags.through, photo=st.sampled_from(photos), tag=st.sampled_from(tags)) if tags else st.none()).flatmap(lambda _:
        st.tuples(st.sampled_from(photos), (st.sampled_from(tags) if tags else st.none()), st.sampled_from(archives))
    ))))))), from_model(User))
    def testPhotos(self, stuff, user):
        photo, tag, archive = stuff
        c = Client()
        authenticated = Client()
        authenticated.force_login(user)
        self.assertEqual(c.get(reverse('kronofoto:random-image')).status_code, 302)
        self.assertEqual(c.get(reverse('kronofoto:random-image', kwargs={'short_name': photo.archive.slug})).status_code, 302)
        self.assertNotContains(c.get(reverse('kronofoto:photoview', kwargs={'photo': photo.id})), 'href="/photos')
        self.assertNotContains(c.get(reverse('kronofoto:photoview', kwargs={'short_name': photo.archive.slug, 'photo': photo.id})), 'href="//example.com/photo')
        if tag and tag in photo.get_accepted_tags():
            self.assertEqual(c.get(reverse('kronofoto:photoview', kwargs={'photo': photo.id}), {'tag': tag.tag}).status_code, 200)
        elif tag and len(tag.tag):
            note(f'{repr(tag.tag)=} {tag.tag=}')
            self.assertEqual(c.get(reverse('kronofoto:photoview', kwargs={'photo': photo.id}), {'tag': tag.tag}).status_code, 404)
        self.assertEqual(c.get(reverse('kronofoto:photoview', kwargs={'short_name': archive.slug, 'photo': photo.id})).status_code, 200 if archive.slug == photo.archive.slug else 404)

        self.assertNotContains(c.get(reverse('kronofoto:download', kwargs={'pk': photo.id})), 'href="/photos')
        self.assertContains(c.get(reverse('kronofoto:download', kwargs={'pk': photo.id})), 'href="{}'.format(krono_reverse("kronofoto:gridview")))
        self.assertNotContains(c.get(reverse('kronofoto:download', kwargs={'short_name': photo.archive.slug, 'pk': photo.id})), 'href="//example.com/photo')
        self.assertEqual(c.get(reverse('kronofoto:addtag', kwargs={'photo': photo.id})).status_code, 302)
        self.assertEqual(c.get(reverse('kronofoto:addtag', kwargs={'short_name': photo.archive.slug, 'photo': photo.id})).status_code, 302)
        self.assertEqual(authenticated.get(reverse('kronofoto:addtag', kwargs={'photo': photo.id})).status_code, 200)
        self.assertEqual(authenticated.get(reverse('kronofoto:addtag', kwargs={'short_name': photo.archive.slug, 'photo': photo.id})).status_code, 200)
        self.assertEqual(c.get(reverse('kronofoto:add-to-list', kwargs={'photo': photo.id})).status_code, 302)
        self.assertEqual(c.get(reverse('kronofoto:add-to-list', kwargs={'short_name': photo.archive.slug, 'photo': photo.id})).status_code, 302)
        self.assertEqual(authenticated.get(reverse('kronofoto:add-to-list', kwargs={'photo': photo.id})).status_code, 200)
        self.assertEqual(authenticated.get(reverse('kronofoto:add-to-list', kwargs={'short_name': photo.archive.slug, 'photo': photo.id})).status_code, 200)
        resp = c.get(reverse('kronofoto:gridview', kwargs={}))
        if Photo.objects.count() > 1:
            self.assertNotContains(resp, 'href="/photos')
        else:
            self.assertRedirects(resp, krono_reverse('kronofoto:photoview', kwargs={'photo': photo.id}), fetch_redirect_response=False)
        resp = c.get(reverse('kronofoto:gridview', kwargs={'short_name': archive.slug}))
        if Photo.objects.filter(archive=archive).count() != 1:
            self.assertNotContains(resp, 'href="//example.com/photo')
        elif Photo.objects.filter(archive=archive).count == 1:
            self.assertRedirects(resp, krono_reverse('kronofoto:photoview', kwargs={'short_name': archive.slug, 'photo': photo.id}), fetch_redirect_response=False)

        self.assertEqual(c.get(reverse('kronofoto:gridview', kwargs={}), photo.page_number()).status_code, 200 if Photo.objects.count() != 1 else 302)
        self.assertEqual(c.get(reverse('kronofoto:gridview', kwargs={'short_name': archive.slug}), photo.page_number()).status_code, 200 if Photo.objects.filter(archive=archive).count() != 1 else 302)


    @settings(deadline=4000, max_examples=5)
    @given(
        archives().flatmap(lambda archive:
        st.lists(donors(archive=archives())).flatmap(lambda _:
        st.lists(terms()).flatmap(lambda _:
        st.lists(tags()).flatmap(lambda _:
        photos(
            is_published=st.just(True),
            year=st.integers(min_value=1800, max_value=1999),
            archive=st.just(archive),
            local_context_id=st.just(None),
            donor=donors(archive=st.just(archive))).flatmap(lambda photo:
        st.lists(from_model(Photo.terms.through, photo=st.just(photo), term=terms())).flatmap(lambda _:
        st.lists(from_model(Photo.tags.through, photo=st.just(photo), tag=tags())).flatmap(lambda _:
        st.just(photo))
    )))))), from_model(User))
    def testPhoto(self, photo, user):
        pass

    @settings(deadline=1000, max_examples=2)
    @given(from_model(User))
    def test_auth_urls(self, user):
        c = Client()
        self.assertEqual(c.get(reverse('login')).status_code, 200)
        self.assertEqual(c.get(reverse('logout')).status_code, 200)
        self.assertEqual(c.get(reverse('password_change')).status_code, 302)
        self.assertEqual(c.get(reverse('password_change_done')).status_code, 302)
        self.assertEqual(c.get(reverse('password_reset')).status_code, 200)
        self.assertEqual(c.post(reverse('password_reset'), {"email": user.email}).status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(c.get(reverse('password_reset_done')).status_code, 200)
        resetURL = re.search("(?P<url>https?://[^\s]+)", mail.outbox[0].body).group("url")
        resp = c.get(resetURL)
        self.assertEqual(resp.status_code, 302)
        resetURL = resp.headers['Location']

        resp = c.get(resetURL)
        self.assertEqual(resp.status_code, 200)
        password = "SDKLJFLKSDJFLKAJLKDSJF"
        self.assertEqual(c.post(resetURL, {'new_password1': password, 'new_password2': password}).status_code, 302)
        resp = c.post(reverse('login'), {'username': user.username, 'password': password})
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(c.get(reverse('password_change')).status_code, 200)
        new_password = 'DJFSKLFJDSKLFJ'
        self.assertEqual(c.post(reverse('password_change'), {'old_password': password, 'new_password1': new_password, 'new_password2': new_password}).status_code, 302)
        self.assertEqual(c.get(reverse('password_change_done')).status_code, 200)

        self.assertEqual(c.get(reverse('password_reset_complete')).status_code, 200)
        self.assertEqual(c.get(reverse('kronofoto:user-page', kwargs={'username': user.username})).status_code, 200)
        self.assertEqual(c.get(reverse('logout')).status_code, 200)

        self.assertEqual(c.get(reverse('register-account')).status_code, 200)
        self.assertEqual(c.get(reverse('email-sent')).status_code, 200)
