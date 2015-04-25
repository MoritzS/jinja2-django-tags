# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.test import SimpleTestCase, override_settings
from jinja2 import Environment, TemplateSyntaxError
from jinja2.ext import Extension
from jdj_tags.extensions import DjangoCompat, DjangoCsrf, DjangoI18n, DjangoStatic, DjangoUrl

try:
    from unittest import mock
except ImportError:
    import mock


class DjangoCsrfTest(SimpleTestCase):
    def setUp(self):
        self.env = Environment(extensions=[DjangoCsrf])
        self.template = self.env.from_string("{% csrf_token %}")

    def test_token(self):
        context = {'csrf_token': 'a_csrf_token'}
        expected = '<input type="hidden" name="csrfmiddlewaretoken" value="a_csrf_token" />'

        self.assertEqual(expected, self.template.render(context))

    def test_empty_token(self):
        context1 = {}
        context2 = {'csrf_token': 'NOTPROVIDED'}

        self.assertEqual('', self.template.render(context1))
        self.assertEqual('', self.template.render(context2))


@override_settings(USE_L10N=True)
class DjangoI18nLocalizeTest(SimpleTestCase):
    def setUp(self):
        self.localize = mock.Mock(side_effect=lambda s: '{} - localized'.format(s))

        with mock.patch('jdj_tags.extensions.localize', self.localize):
            self.env = Environment(extensions=[DjangoI18n])

    def test_localize(self):
        template = self.env.from_string("{{ foo }}")

        self.assertEqual('foovar - localized', template.render({'foo': 'foovar'}))
        self.localize.assert_called_with('foovar')

    def test_existing_finalize(self):
        finalize_mock = mock.Mock(side_effect=lambda s: s)

        class TestExtension(Extension):
            def __init__(self, environment):
                environment.finalize = finalize_mock

        with mock.patch('jdj_tags.extensions.localize', self.localize):
            env = Environment(extensions=[TestExtension, DjangoI18n])
            template = env.from_string("{{ foo }}")

            self.assertEqual('foovar - localized', template.render({'foo': 'foovar'}))

        finalize_mock.assert_called_with('foovar')
        self.localize.assert_called_with('foovar')


gettext_mock = mock.Mock(side_effect=lambda s: '{} - translated'.format(s))
pgettext_mock = mock.Mock(side_effect=lambda c, s: '{} - alt translated'.format(s))


class DjangoI18nTransTest(SimpleTestCase):
    def setUp(self):
        with mock.patch('jdj_tags.extensions.ugettext', gettext_mock), \
                mock.patch('jdj_tags.extensions.pgettext', pgettext_mock):
            self.env = Environment(extensions=[DjangoI18n])

        self.str = 'Hello World'
        self.trans1 = '{} - translated'.format(self.str)
        self.trans2 = '{} - alt translated'.format(self.str)

    def test_simple_trans(self):
        template1 = self.env.from_string("{% trans 'Hello World' %}")
        template2 = self.env.from_string(
            "{% trans 'Hello World' context 'some context' %}"
        )
        template3 = self.env.from_string("{{ _('Hello World') }}")
        template4 = self.env.from_string("{{ gettext('Hello World') }}")
        template5 = self.env.from_string("{{ pgettext('some context', 'Hello World') }}")

        self.assertEqual(self.trans1, template1.render())
        gettext_mock.assert_called_with('Hello World')
        self.assertEqual(self.trans2, template2.render())
        pgettext_mock.assert_called_with('some context', 'Hello World')
        self.assertEqual(self.trans1, template3.render())
        gettext_mock.assert_called_with('Hello World')
        self.assertEqual(self.trans1, template4.render())
        gettext_mock.assert_called_with('Hello World')
        self.assertEqual(self.trans2, template5.render())
        pgettext_mock.assert_called_with('some context', 'Hello World')

    def test_noop(self):
        template = self.env.from_string("{% trans 'Hello World' noop %}")

        self.assertEqual(self.str, template.render())

    def test_as_var(self):
        template = self.env.from_string(
            "{% trans 'Hello World' as myvar %}My var is: {{ myvar }}!"
        )

        self.assertEqual('My var is: {}!'.format(self.trans1), template.render())
        gettext_mock.assert_called_with('Hello World')

    def test_noop_as_var(self):
        template1 = self.env.from_string(
            "{% trans 'Hello World' noop as myvar %}My var is: {{ myvar }}!"
        )
        template2 = self.env.from_string(
            "{% trans 'Hello World' as myvar noop %}My var is: {{ myvar }}!"
        )

        expected_str = 'My var is: {}!'.format(self.str)

        self.assertEqual(expected_str, template1.render())
        self.assertEqual(expected_str, template2.render())

    def test_errors(self):
        template1 = "{% trans 'Hello World' foo %}"
        template2 = "{% trans 'Hello World' noop context 'some context' %}"
        template3 = "{% trans 'Hello World' context 'some context' noop %}"

        error_messages = [
            (template1, "expected 'noop', 'context' or 'as'"),
            (template2, "noop translation can't have context"),
            (template3, "noop translation can't have context"),
        ]

        for template, msg in error_messages:
            with self.assertRaisesMessage(TemplateSyntaxError, msg):
                self.env.from_string(template)


@mock.patch('jdj_tags.extensions.ugettext', gettext_mock)
@mock.patch('jdj_tags.extensions.pgettext', pgettext_mock)
class DjangoI18nBlocktransTest(SimpleTestCase):
    def setUp(self):
        self.env = Environment(extensions=[DjangoI18n])

    def test_simple(self):
        template1 = self.env.from_string('{% blocktrans %}Translate me!{% endblocktrans %}')
        template2 = self.env.from_string(
            "{% blocktrans context 'foo' %}Translate me!{% endblocktrans %}"
        )

        self.assertEqual('Translate me! - translated', template1.render())
        gettext_mock.assert_called_with('Translate me!')
        self.assertEqual('Translate me! - alt translated', template2.render())
        pgettext_mock.assert_called_with('foo', 'Translate me!')

    def test_trimmed(self):
        template = self.env.from_string("""{% blocktrans trimmed %}
                Translate
                me!
            {% endblocktrans %}""")

        self.assertEqual('Translate me! - translated', template.render())
        gettext_mock.assert_called_with('Translate me!')

    def test_with(self):
        template1 = self.env.from_string(
            "{% blocktrans with foo=bar %}Trans: {{ foo }}{% endblocktrans %}"
        )
        template2 = self.env.from_string(
            "{% blocktrans with foo=bar spam=eggs %}Trans: {{ foo }} and "
            "{{ spam }}{% endblocktrans %}"
        )
        template3 = self.env.from_string(
            "{{ foo }} {% blocktrans with foo=bar %}Trans: {{ foo }}"
            "{% endblocktrans %} {{ foo }}"
        )
        template4 = self.env.from_string(
            "{% blocktrans with foo=bar|upper %}Trans: {{ foo }}{% endblocktrans %}"
        )

        self.assertEqual(
            'Trans: barvar - translated',
            template1.render({'bar': 'barvar'})
        )
        gettext_mock.assert_called_with('Trans: %(foo)s')
        self.assertEqual(
            'Trans: barvar and eggsvar - translated',
            template2.render({'bar': 'barvar', 'eggs': 'eggsvar'})
        )
        gettext_mock.assert_called_with('Trans: %(foo)s and %(spam)s')
        self.assertEqual(
            'foovar Trans: barvar - translated foovar',
            template3.render({'foo': 'foovar', 'bar': 'barvar'})
        )
        gettext_mock.assert_called_with('Trans: %(foo)s')
        self.assertEqual(
            'Trans: BARVAR - translated',
            template4.render({'bar': 'barvar'})
        )
        gettext_mock.assert_called_with('Trans: %(foo)s')

    def test_global_var(self):
        template = self.env.from_string("{% blocktrans %}Trans: {{ foo }}{% endblocktrans %}")

        self.assertEqual(
            'Trans: foovar - translated',
            template.render({'foo': 'foovar'})
        )
        gettext_mock.assert_called_with('Trans: %(foo)s')


static_mock = mock.Mock(side_effect=lambda s: 'Static: {}'.format(s))


@mock.patch('jdj_tags.extensions.django_static', static_mock)
class DjangoStaticTest(SimpleTestCase):
    def setUp(self):
        self.env = Environment(extensions=[DjangoStatic])

    def test_simple(self):
        template = self.env.from_string("{% static 'static.png' %}")

        self.assertEqual('Static: static.png', template.render())
        static_mock.assert_called_with('static.png')

    def test_as_var(self):
        template = self.env.from_string(
            "{% static 'static.png' as my_url %}My url is: {{ my_url }}!"
        )

        self.assertEqual('My url is: Static: static.png!', template.render())
        static_mock.assert_called_with('static.png')


reverse_mock = mock.Mock(side_effect=lambda name, *args, **kwargs: 'Url for: {}'.format(name))


@mock.patch('jdj_tags.extensions.reverse', reverse_mock)
class DjangoUrlTest(SimpleTestCase):
    def setUp(self):
        self.env = Environment(extensions=[DjangoUrl])

    def test_simple(self):
        template = self.env.from_string("{% url 'my_view' %}")

        self.assertEqual('Url for: my_view', template.render())
        reverse_mock.assert_called_with('my_view', args=(), kwargs={})

    def test_args(self):
        template1 = self.env.from_string("{% url 'my_view' 'foo' 'bar' %}")
        template2 = self.env.from_string("{% url 'my_view' arg1 'bar' %}")
        template3 = self.env.from_string("{% url 'my_view' arg1 arg2 %}")

        expected = 'Url for: my_view'
        call = mock.call('my_view', args=('foo', 'bar'), kwargs={})

        self.assertEqual(expected, template1.render())
        self.assertEqual(call, reverse_mock.call_args)
        self.assertEqual(expected, template2.render({'arg1': 'foo'}))
        self.assertEqual(call, reverse_mock.call_args)
        self.assertEqual(expected, template3.render({'arg1': 'foo', 'arg2': 'bar'}))
        self.assertEqual(call, reverse_mock.call_args)

    def test_kwargs(self):
        template1 = self.env.from_string("{% url 'my_view' kw1='foo' kw2='bar' %}")
        template2 = self.env.from_string("{% url 'my_view' kw1=arg1 kw2='bar' %}")
        template3 = self.env.from_string("{% url 'my_view' kw1=arg1 kw2=arg2 %}")

        expected = 'Url for: my_view'
        call = mock.call('my_view', args=(), kwargs={'kw1': 'foo', 'kw2': 'bar'})

        self.assertEqual(expected, template1.render())
        self.assertEqual(call, reverse_mock.call_args)
        self.assertEqual(expected, template2.render({'arg1': 'foo'}))
        self.assertEqual(call, reverse_mock.call_args)
        self.assertEqual(expected, template3.render({'arg1': 'foo', 'arg2': 'bar'}))
        self.assertEqual(call, reverse_mock.call_args)

    def test_dotted_expr(self):
        template1 = self.env.from_string("{% url 'my_view' foo.bar %}")
        template2 = self.env.from_string("{% url 'my_view' kw1=foo.bar %}")

        class Foo(object):
            pass

        foo = Foo()
        foo.bar = 'argument'

        self.assertEqual('Url for: my_view', template1.render({'foo': foo}))
        reverse_mock.assert_called_with('my_view', args=('argument',), kwargs={})
        self.assertEqual('Url for: my_view', template2.render({'foo': foo}))
        reverse_mock.assert_called_with('my_view', args=(), kwargs={'kw1': 'argument'})

    def test_as_var(self):
        template1 = self.env.from_string("{% url 'my_view' as my_url %}Url: {{ my_url }}")
        template2 = self.env.from_string(
            "{% url 'my_view' arg1 'bar' as my_url %}Url: {{ my_url }}"
        )
        template3 = self.env.from_string(
            "{% url 'my_view' kw1=arg1 kw2='bar' as my_url %}Url: {{ my_url }}"
        )

        expected = 'Url: Url for: my_view'

        self.assertEqual(expected, template1.render())
        reverse_mock.assert_called_with('my_view', args=(), kwargs={})
        self.assertEqual(expected, template2.render({'arg1': 'foo'}))
        reverse_mock.assert_called_with('my_view', args=('foo', 'bar'), kwargs={})
        self.assertEqual(expected, template3.render({'arg1': 'foo'}))
        reverse_mock.assert_called_with('my_view', args=(), kwargs={'kw1': 'foo', 'kw2': 'bar'})

    def test_errors(self):
        template = "{% url 'my_view' kw1='foo' 123 %}"
        msg = "got 'integer', expected name for keyword argument"

        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.env.from_string(template)


class DjangoCompatTest(SimpleTestCase):
    class CalledParse(Exception):
        pass

    @classmethod
    def make_mock(cls, cls_name):
        def parse(self, parser):
            raise cls.CalledParse(cls_name)
        return mock.Mock(side_effect=parse)

    def setUp(self):
        self.env = Environment(extensions=[DjangoCompat])

    def test_compat(self):
        tags = [
            ('csrf_token', 'DjangoCsrf'),
            ('trans', 'DjangoI18n'),
            ('blocktrans', 'DjangoI18n'),
            ('static', 'DjangoStatic'),
            ('url', 'DjangoUrl'),
        ]

        with mock.patch('jdj_tags.extensions.DjangoCsrf.parse', self.make_mock('DjangoCsrf')), \
                mock.patch('jdj_tags.extensions.DjangoI18n.parse', self.make_mock('DjangoI18n')), \
                mock.patch('jdj_tags.extensions.DjangoStatic.parse', self.make_mock('DjangoStatic')), \
                mock.patch('jdj_tags.extensions.DjangoUrl.parse', self.make_mock('DjangoUrl')):
            for tag, class_name in tags:
                with self.assertRaisesMessage(self.CalledParse, class_name):
                    self.env.from_string('{% ' + tag + ' %}')


if __name__ == '__main__':
    import unittest
    from django.conf import settings
    settings.configure()

    unittest.main()
