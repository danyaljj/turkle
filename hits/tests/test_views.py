# -*- coding: utf-8 -*-
import os.path

import django.test
from django.core.handlers.wsgi import WSGIRequest
from django.contrib.auth.models import User

from hits.models import Hit, HitBatch, HitTemplate
from hits.views import submission


class TestHitBatch(django.test.TestCase):
    def setUp(self):
        User.objects.create_superuser('admin', 'foo@bar.foo', 'secret')

    def test_batch_add(self):
        hit_template = HitTemplate(name='foo', form='<p>${foo}: ${bar}</p>')
        hit_template.save()

        self.assertFalse(HitBatch.objects.filter(name='hit_batch_save').exists())

        client = django.test.Client()
        client.login(username='admin', password='secret')
        with open(os.path.abspath('hits/tests/resources/form_1_vals.csv')) as fp:
            response = client.post(
                u'/admin/hits/hitbatch/add/',
                {
                    'hit_template': hit_template.id,
                    'name': 'hit_batch_save',
                    'csv_file': fp
                })
        self.assertTrue('error' not in response.content)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], u'/admin/hits/hitbatch/')
        self.assertTrue(HitBatch.objects.filter(name='hit_batch_save').exists())
        matching_hit_batch = HitBatch.objects.filter(name='hit_batch_save').first()
        self.assertEqual(matching_hit_batch.filename, u'form_1_vals.csv')
        self.assertEqual(matching_hit_batch.total_hits(), 1)

    def test_batch_add_csv_with_emoji(self):
        hit_template = HitTemplate(name='foo', form='<p>${emoji}: ${more_emoji}</p>')
        hit_template.save()

        self.assertFalse(HitBatch.objects.filter(name='hit_batch_save').exists())

        client = django.test.Client()
        client.login(username='admin', password='secret')
        with open(os.path.abspath('hits/tests/resources/emoji.csv')) as fp:
            response = client.post(
                u'/admin/hits/hitbatch/add/',
                {
                    'hit_template': hit_template.id,
                    'name': 'hit_batch_save',
                    'csv_file': fp
                })
        self.assertTrue('error' not in response.content)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], u'/admin/hits/hitbatch/')
        self.assertTrue(HitBatch.objects.filter(name='hit_batch_save').exists())
        matching_hit_batch = HitBatch.objects.filter(name='hit_batch_save').first()
        self.assertEqual(matching_hit_batch.filename, u'emoji.csv')

        self.assertEqual(matching_hit_batch.total_hits(), 3)
        hits = matching_hit_batch.hit_set.all()
        self.assertEqual(hits[0].input_csv_fields['emoji'], u'😀')
        self.assertEqual(hits[0].input_csv_fields['more_emoji'], u'😃')
        self.assertEqual(hits[2].input_csv_fields['emoji'], u'🤔')
        self.assertEqual(hits[2].input_csv_fields['more_emoji'], u'🤭')

    def test_batch_add_missing_file_field(self):
        hit_template = HitTemplate(name='foo', form='<p>${emoji}: ${more_emoji}</p>')
        hit_template.save()

        self.assertFalse(HitBatch.objects.filter(name='hit_batch_save').exists())

        client = django.test.Client()
        client.login(username='admin', password='secret')
        response = client.post(
            u'/admin/hits/hitbatch/add/',
            {
                'hit_template': hit_template.id,
                'name': 'hit_batch_save',
            })
        self.assertTrue('error' in response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('This field is required' in response.content)

    def test_batch_add_validation_extra_fields(self):
        hit_template = HitTemplate(name='foo', form='<p>${f2}</p>')
        hit_template.save()

        self.assertFalse(HitBatch.objects.filter(name='hit_batch_save').exists())

        client = django.test.Client()
        client.login(username='admin', password='secret')
        # CSV file has fields 'f2' and 'f3'
        with open(os.path.abspath('hits/tests/resources/mismatched_fields.csv')) as fp:
            response = client.post(
                u'/admin/hits/hitbatch/add/',
                {
                    'hit_template': hit_template.id,
                    'name': 'hit_batch_save',
                    'csv_file': fp
                })
        self.assertEqual(response.status_code, 200)
        self.assertTrue('error' in response.content)
        self.assertTrue('extra fields' in response.content)
        self.assertTrue('missing fields' not in response.content)

    def test_batch_add_validation_missing_fields(self):
        hit_template = HitTemplate(name='foo', form='<p>${f1} ${f2} ${f3}</p>')
        hit_template.save()

        self.assertFalse(HitBatch.objects.filter(name='hit_batch_save').exists())

        client = django.test.Client()
        client.login(username='admin', password='secret')
        # CSV file has fields 'f2' and 'f3'
        with open(os.path.abspath('hits/tests/resources/mismatched_fields.csv')) as fp:
            response = client.post(
                u'/admin/hits/hitbatch/add/',
                {
                    'hit_template': hit_template.id,
                    'name': 'hit_batch_save',
                    'csv_file': fp
                })
        self.assertEqual(response.status_code, 200)
        self.assertTrue('error' in response.content)
        self.assertTrue('extra fields' not in response.content)
        self.assertTrue('missing fields' in response.content)

    def test_batch_add_validation_variable_fields_per_row(self):
        hit_template = HitTemplate(name='foo', form='<p>${f1} ${f2} ${f3}</p>')
        hit_template.save()

        self.assertFalse(HitBatch.objects.filter(name='hit_batch_save').exists())

        client = django.test.Client()
        client.login(username='admin', password='secret')
        # CSV file has fields 'f2' and 'f3'
        with open(os.path.abspath('hits/tests/resources/variable_fields_per_row.csv')) as fp:
            response = client.post(
                u'/admin/hits/hitbatch/add/',
                {
                    'hit_template': hit_template.id,
                    'name': 'hit_batch_save',
                    'csv_file': fp
                })
        self.assertEqual(response.status_code, 200)
        self.assertTrue('error' in response.content)
        self.assertTrue('line 2 has 2 fields' in response.content)
        self.assertTrue('line 4 has 4 fields' in response.content)

    def test_batch_change_get_page(self):
        self.test_batch_add()
        batch = HitBatch.objects.get(name='hit_batch_save')

        client = django.test.Client()
        client.login(username='admin', password='secret')
        response = client.get(
            u'/admin/hits/hitbatch/%d/change/' % batch.id
        )
        self.assertTrue('error' not in response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('no file selected' not in response.content)

    def test_batch_change_update(self):
        self.test_batch_add()
        batch = HitBatch.objects.get(name='hit_batch_save')

        client = django.test.Client()
        client.login(username='admin', password='secret')
        response = client.post(
            u'/admin/hits/hitbatch/%d/change/' % batch.id,
            {
                'hit_template': batch.hit_template.id,
                'name': 'hit_batch_save_modified',
            })
        self.assertTrue('error' not in response.content)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], u'/admin/hits/hitbatch/')
        self.assertFalse(HitBatch.objects.filter(name='hit_batch_save').exists())
        self.assertTrue(HitBatch.objects.filter(name='hit_batch_save_modified').exists())


class TestSubmission(django.test.TestCase):

    def setUp(self):
        hit_template = HitTemplate(name='foo', form='<p></p>')
        hit_template.save()
        hit_batch = HitBatch(hit_template=hit_template)
        hit_batch.save()
        self.hit = Hit(hit_batch=hit_batch, input_csv_fields='{}')
        self.hit.save()

    def test_0(self):
        post_request = RequestFactory().post(
            u'/hits/1/submission',
            {u'foo': u'bar'}
        )
        post_request.csrf_processing_done = True
        submission(post_request, 1)
        h = Hit.objects.get(id=1)

        expect = {u'foo': u'bar'}
        actual = h.answers
        self.assertEqual(expect, actual)


# This was grabbed from
# http://djangosnippets.org/snippets/963/
class RequestFactory(django.test.Client):
    """
    Class that lets you create mock Request objects for use in testing.

    Usage:

    rf = RequestFactory()
    get_request = rf.get('/hello/')
    post_request = rf.post('/submit/', {'foo': 'bar'})

    This class re-uses the django.test.client.Client interface, docs here:
    http://www.djangoproject.com/documentation/testing/#the-test-client

    Once you have a request object you can pass it to any view function,
    just as if that view had been hooked up using a URLconf.

    """
    def request(self, **request):
        """
        Similar to parent class, but returns the request object as soon as it
        has created it.
        """
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)


__all__ = (
    'RequestFactory',
    'TestSubmission',
)
