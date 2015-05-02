# coding: utf-8
from __future__ import unicode_literals

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
    @mock.patch('jdj_tags.extensions.localize')
    def setUp(self, localize):
        localize.side_effect = lambda s: '{} - localized'.format(s)
        self.localize = localize
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


class DjangoI18nTestBase(SimpleTestCase):
    @staticmethod
    def _gettext(string):
        return '{} - translated'.format(string)

    @staticmethod
    def _pgettext(context, string):
        return '{} - alt translated'.format(string)

    def setUp(self):
        gettext_patcher = mock.patch('jdj_tags.extensions.ugettext', side_effect=self._gettext)
        pgettext_patcher = mock.patch('jdj_tags.extensions.pgettext', side_effect=self._pgettext)

        self.gettext = gettext_patcher.start()
        self.pgettext = pgettext_patcher.start()

        self.addCleanup(gettext_patcher.stop)
        self.addCleanup(pgettext_patcher.stop)

        self.env = Environment(extensions=[DjangoI18n])


class DjangoI18nTransTest(DjangoI18nTestBase):
    def test_simple_trans(self):
        template1 = self.env.from_string("{% trans 'Hello World' %}")
        template2 = self.env.from_string(
            "{% trans 'Hello World' context 'some context' %}"
        )
        template3 = self.env.from_string("{{ _('Hello World') }}")
        template4 = self.env.from_string("{{ gettext('Hello World') }}")
        template5 = self.env.from_string("{{ pgettext('some context', 'Hello World') }}")

        trans1 = 'Hello World - translated'
        trans2 = 'Hello World - alt translated'

        self.assertEqual(trans1, template1.render())
        self.gettext.assert_called_with('Hello World')
        self.assertEqual(trans2, template2.render())
        self.pgettext.assert_called_with('some context', 'Hello World')
        self.assertEqual(trans1, template3.render())
        self.gettext.assert_called_with('Hello World')
        self.assertEqual(trans1, template4.render())
        self.gettext.assert_called_with('Hello World')
        self.assertEqual(trans2, template5.render())
        self.pgettext.assert_called_with('some context', 'Hello World')

    def test_noop(self):
        template = self.env.from_string("{% trans 'Hello World' noop %}")

        self.assertEqual('Hello World', template.render())

    def test_as_var(self):
        template = self.env.from_string(
            "{% trans 'Hello World' as myvar %}My var is: {{ myvar }}!"
        )

        self.assertEqual('My var is: Hello World - translated!', template.render())
        self.gettext.assert_called_with('Hello World')

    def test_noop_as_var(self):
        template1 = self.env.from_string(
            "{% trans 'Hello World' noop as myvar %}My var is: {{ myvar }}!"
        )
        template2 = self.env.from_string(
            "{% trans 'Hello World' as myvar noop %}My var is: {{ myvar }}!"
        )

        expected_str = 'My var is: Hello World!'

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


class DjangoI18nBlocktransTest(DjangoI18nTestBase):
    def test_simple(self):
        template1 = self.env.from_string('{% blocktrans %}Translate me!{% endblocktrans %}')
        template2 = self.env.from_string(
            "{% blocktrans context 'foo' %}Translate me!{% endblocktrans %}"
        )

        self.assertEqual('Translate me! - translated', template1.render())
        self.gettext.assert_called_with('Translate me!')
        self.assertEqual('Translate me! - alt translated', template2.render())
        self.pgettext.assert_called_with('foo', 'Translate me!')

    def test_trimmed(self):
        template = self.env.from_string("""{% blocktrans trimmed %}
                Translate
                me!
            {% endblocktrans %}""")

        self.assertEqual('Translate me! - translated', template.render())
        self.gettext.assert_called_with('Translate me!')

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
        self.gettext.assert_called_with('Trans: %(foo)s')
        self.assertEqual(
            'Trans: barvar and eggsvar - translated',
            template2.render({'bar': 'barvar', 'eggs': 'eggsvar'})
        )
        self.gettext.assert_called_with('Trans: %(foo)s and %(spam)s')
        self.assertEqual(
            'foovar Trans: barvar - translated foovar',
            template3.render({'foo': 'foovar', 'bar': 'barvar'})
        )
        self.gettext.assert_called_with('Trans: %(foo)s')
        self.assertEqual(
            'Trans: BARVAR - translated',
            template4.render({'bar': 'barvar'})
        )
        self.gettext.assert_called_with('Trans: %(foo)s')

    def test_global_var(self):
        template = self.env.from_string("{% blocktrans %}Trans: {{ foo }}{% endblocktrans %}")

        self.assertEqual(
            'Trans: foovar - translated',
            template.render({'foo': 'foovar'})
        )
        self.gettext.assert_called_with('Trans: %(foo)s')


class DjangoStaticTest(SimpleTestCase):
    @staticmethod
    def _static(path):
        return 'Static: {}'.format(path)

    def setUp(self):
        patcher = mock.patch('jdj_tags.extensions.django_static', side_effect=self._static)
        self.static = patcher.start()
        self.addCleanup(patcher.stop)

        self.env = Environment(extensions=[DjangoStatic])

    def test_simple(self):
        template = self.env.from_string("{% static 'static.png' %}")

        self.assertEqual('Static: static.png', template.render())
        self.static.assert_called_with('static.png')

    def test_as_var(self):
        template = self.env.from_string(
            "{% static 'static.png' as my_url %}My url is: {{ my_url }}!"
        )

        self.assertEqual('My url is: Static: static.png!', template.render())
        self.static.assert_called_with('static.png')


class DjangoUrlTest(SimpleTestCase):
    @staticmethod
    def _reverse(name, *args, **kwargs):
        return 'Url for: {}'.format(name)

    def setUp(self):
        patcher = mock.patch('jdj_tags.extensions.reverse', side_effect=self._reverse)
        self.reverse = patcher.start()
        self.addCleanup(patcher.stop)

        self.env = Environment(extensions=[DjangoUrl])

    def test_simple(self):
        template = self.env.from_string("{% url 'my_view' %}")

        self.assertEqual('Url for: my_view', template.render())
        self.reverse.assert_called_with('my_view', args=(), kwargs={})

    def test_args(self):
        template1 = self.env.from_string("{% url 'my_view' 'foo' 'bar' %}")
        template2 = self.env.from_string("{% url 'my_view' arg1 'bar' %}")
        template3 = self.env.from_string("{% url 'my_view' arg1 arg2 %}")

        expected = 'Url for: my_view'
        call = mock.call('my_view', args=('foo', 'bar'), kwargs={})

        self.assertEqual(expected, template1.render())
        self.assertEqual(call, self.reverse.call_args)
        self.assertEqual(expected, template2.render({'arg1': 'foo'}))
        self.assertEqual(call, self.reverse.call_args)
        self.assertEqual(expected, template3.render({'arg1': 'foo', 'arg2': 'bar'}))
        self.assertEqual(call, self.reverse.call_args)

    def test_kwargs(self):
        template1 = self.env.from_string("{% url 'my_view' kw1='foo' kw2='bar' %}")
        template2 = self.env.from_string("{% url 'my_view' kw1=arg1 kw2='bar' %}")
        template3 = self.env.from_string("{% url 'my_view' kw1=arg1 kw2=arg2 %}")

        expected = 'Url for: my_view'
        call = mock.call('my_view', args=(), kwargs={'kw1': 'foo', 'kw2': 'bar'})

        self.assertEqual(expected, template1.render())
        self.assertEqual(call, self.reverse.call_args)
        self.assertEqual(expected, template2.render({'arg1': 'foo'}))
        self.assertEqual(call, self.reverse.call_args)
        self.assertEqual(expected, template3.render({'arg1': 'foo', 'arg2': 'bar'}))
        self.assertEqual(call, self.reverse.call_args)

    def test_dotted_expr(self):
        template1 = self.env.from_string("{% url 'my_view' foo.bar %}")
        template2 = self.env.from_string("{% url 'my_view' kw1=foo.bar %}")

        class Foo(object):
            pass

        foo = Foo()
        foo.bar = 'argument'

        self.assertEqual('Url for: my_view', template1.render({'foo': foo}))
        self.reverse.assert_called_with('my_view', args=('argument',), kwargs={})
        self.assertEqual('Url for: my_view', template2.render({'foo': foo}))
        self.reverse.assert_called_with('my_view', args=(), kwargs={'kw1': 'argument'})

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
        self.reverse.assert_called_with('my_view', args=(), kwargs={})
        self.assertEqual(expected, template2.render({'arg1': 'foo'}))
        self.reverse.assert_called_with('my_view', args=('foo', 'bar'), kwargs={})
        self.assertEqual(expected, template3.render({'arg1': 'foo'}))
        self.reverse.assert_called_with('my_view', args=(), kwargs={'kw1': 'foo', 'kw2': 'bar'})

    def test_errors(self):
        template = "{% url 'my_view' kw1='foo' 123 %}"
        msg = "got 'integer', expected name for keyword argument"

        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.env.from_string(template)


class DjangoCompatTest(SimpleTestCase):
    classes = ['DjangoCsrf', 'DjangoI18n', 'DjangoStatic', 'DjangoUrl']

    class CalledParse(Exception):
        pass

    @classmethod
    def make_side_effect(cls, cls_name):
        def parse(self, parser):
            raise cls.CalledParse(cls_name)
        return parse

    def setUp(self):
        for class_name in self.classes:
            patcher = mock.patch(
                'jdj_tags.extensions.{}.parse'.format(class_name),
                side_effect=self.make_side_effect(class_name)
            )
            patcher.start()
            self.addCleanup(patcher.stop)

        self.env = Environment(extensions=[DjangoCompat])

    def test_compat(self):
        tags = [
            ('csrf_token', 'DjangoCsrf'),
            ('trans', 'DjangoI18n'),
            ('blocktrans', 'DjangoI18n'),
            ('static', 'DjangoStatic'),
            ('url', 'DjangoUrl'),
        ]

        for tag, class_name in tags:
            with self.assertRaisesMessage(self.CalledParse, class_name):
                self.env.from_string('{% ' + tag + ' %}')


if __name__ == '__main__':
    import unittest
    from django.conf import settings
    settings.configure()

    unittest.main()
