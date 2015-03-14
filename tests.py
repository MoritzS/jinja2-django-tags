# coding: utf-8
from __future__ import absolute_import, unicode_literals
import unittest
from jinja2 import Environment, TemplateError
from jdj_tags.extensions import DjangoI18n, DjangoStatic, DjangoUrl


class TestCase(unittest.TestCase):
    def assertStrEqual(self, first, second, msg=None):
        """
        Compares two strings but removes all 'u' prefixes for unicode
        strings first.
        """
        first = first.replace("u'", "'").replace('u"', '"')
        second = second.replace("u'", "'").replace('u"', '"')

        self.assertEqual(first, second, msg)


class DjangoI18nTransTest(TestCase):
    def setUp(self):
        self.env = Environment(extensions=[DjangoI18n])
        self.env.globals['gettext'] = lambda s: '{} - translated'.format(s)
        self.env.globals['pgettext'] = lambda c, s: '{} - alt translated'.format(s)

        self.str = 'Hello World'
        self.trans1 = '{} - translated'.format(self.str)
        self.trans2 = '{} - alt translated'.format(self.str)

    def test_simple_trans(self):
        template1 = self.env.from_string("{% trans 'Hello World' %}")
        template2 = self.env.from_string(
            "{% trans 'Hello World' context 'some context' %}"
        )

        self.assertStrEqual(self.trans1, template1.render())
        self.assertStrEqual(self.trans2, template2.render())

    def test_noop(self):
        template = self.env.from_string("{% trans 'Hello World' noop %}")

        self.assertEqual(self.str, template.render())

    def test_as_var(self):
        template = self.env.from_string(
            "{% trans 'Hello World' as myvar %}My var is: {{ myvar }}!"
        )

        self.assertEqual('My var is: {}!'.format(self.trans1), template.render())

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

    def test_fail_noop_context(self):
        template1 = lambda: self.env.from_string(
            "{% trans 'Hello World' noop context 'some context' %}"
        )
        template2 = lambda: self.env.from_string(
            "{% trans 'Hello World' context 'some context' noop %}"
        )

        self.assertRaises(TemplateError, template1)
        self.assertRaises(TemplateError, template2)


class DjangoI18nBlocktransTest(TestCase):
    def mock_blocktrans(self, trans_str, context=None, trans_vars=None):
        if trans_vars is None:
            trans_vars = {}
        return "translated '{}', context: {}, trans_vars: {}" \
               "".format(trans_str, context, trans_vars)

    def setUp(self):
        self.env = Environment(extensions=[DjangoI18n])
        self.env.extensions[DjangoI18n.identifier]._make_blocktrans = self.mock_blocktrans

    def test_simple(self):
        template1 = self.env.from_string('{% blocktrans %}Translate me!{% endblocktrans %}')
        template2 = self.env.from_string(
            "{% blocktrans context 'foo' %}Translate me!{% endblocktrans %}"
        )

        self.assertStrEqual(self.mock_blocktrans('Translate me!'), template1.render())
        self.assertStrEqual(self.mock_blocktrans('Translate me!', 'foo'), template2.render())

    def test_trimmed(self):
        template = self.env.from_string("""{% blocktrans trimmed %}
                Translate
                me!
            {% endblocktrans %}""")

        self.assertStrEqual(self.mock_blocktrans('Translate me!'), template.render())

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

        self.assertStrEqual(
            self.mock_blocktrans('Trans: %(foo)s', None, {'foo': 'barvar'}),
            template1.render({'bar': 'barvar'})
        )
        self.assertStrEqual(
            self.mock_blocktrans(
                'Trans: %(foo)s and %(spam)s',
                None,
                {'foo': 'barvar', 'spam': 'eggsvar'}
            ),
            template2.render({'bar': 'barvar', 'eggs': 'eggsvar'})
        )
        self.assertStrEqual(
            'foovar {} foovar'.format(
                self.mock_blocktrans(
                    'Trans: %(foo)s', None, {'foo': 'barvar'}
                )
            ),
            template3.render({'foo': 'foovar', 'bar': 'barvar'})
        )
        self.assertStrEqual(
            self.mock_blocktrans('Trans: %(foo)s', None, {'foo': 'BARVAR'}),
            template4.render({'bar': 'barvar'})
        )


class DjangoStaticTest(TestCase):
    def mock_static(self, path):
        return 'Static: {}'.format(path)

    def setUp(self):
        self.env = Environment(extensions=[DjangoStatic])
        self.env.extensions[DjangoStatic.identifier]._static = self.mock_static

    def test_simple(self):
        template = self.env.from_string("{% static 'static.png' %}")

        self.assertStrEqual(self.mock_static('static.png'), template.render())

    def test_as_var(self):
        template = self.env.from_string(
            "{% static 'static.png' as my_url %}My url is: {{ my_url }}!"
        )

        self.assertStrEqual(
            'My url is: {}!'.format(self.mock_static('static.png')),
            template.render()
        )


class DjangoUrlTest(TestCase):
    def mock_reverse(self, name, *args, **kwargs):
        return 'reversed {} with args {} and kwargs {}'.format(name, args, kwargs)

    def setUp(self):
        self.env = Environment(extensions=[DjangoUrl])
        self.env.extensions[DjangoUrl.identifier]._url_reverse = self.mock_reverse

    def test_simple(self):
        template = self.env.from_string("{% url 'my_view' %}")

        self.assertStrEqual(self.mock_reverse('my_view'), template.render())

    def test_args(self):
        template1 = self.env.from_string("{% url 'my_view' 'foo' 'bar' %}")
        template2 = self.env.from_string("{% url 'my_view' arg1 'bar' %}")
        template3 = self.env.from_string("{% url 'my_view' arg1 arg2 %}")

        url = self.mock_reverse('my_view', 'foo', 'bar')
        self.assertStrEqual(url, template1.render())
        self.assertStrEqual(url, template2.render({'arg1': 'foo'}))
        self.assertStrEqual(url, template3.render({'arg1': 'foo', 'arg2': 'bar'}))

    def test_kwargs(self):
        template1 = self.env.from_string("{% url 'my_view' kw1='foo' kw2='bar' %}")
        template2 = self.env.from_string("{% url 'my_view' kw1=arg1 kw2='bar' %}")
        template3 = self.env.from_string("{% url 'my_view' kw1=arg1 kw2=arg2 %}")

        url = self.mock_reverse('my_view', kw1='foo', kw2='bar')
        self.assertStrEqual(url, template1.render())
        self.assertStrEqual(url, template2.render({'arg1': 'foo'}))
        self.assertStrEqual(url, template3.render({'arg1': 'foo', 'arg2': 'bar'}))

    def test_dotted_expr(self):
        template1 = self.env.from_string("{% url 'my_view' foo.bar %}")
        template2 = self.env.from_string("{% url 'my_view' kw1=foo.bar %}")

        class Foo(object):
            pass

        foo = Foo()
        foo.bar = 'argument'

        self.assertStrEqual(
            self.mock_reverse('my_view', 'argument'),
            template1.render({'foo': foo})
        )
        self.assertStrEqual(
            self.mock_reverse('my_view', kw1='argument'),
            template2.render({'foo': foo})
        )

    def test_as_var(self):
        template1 = self.env.from_string("{% url 'my_view' as my_url %}Url: {{ my_url }}")
        template2 = self.env.from_string(
            "{% url 'my_view' arg1 'bar' as my_url %}Url: {{ my_url }}"
        )
        template3 = self.env.from_string(
            "{% url 'my_view' kw1=arg1 kw2='bar' as my_url %}Url: {{ my_url }}"
        )

        url1 = self.mock_reverse('my_view')
        url2 = self.mock_reverse('my_view', 'foo', 'bar')
        url3 = self.mock_reverse('my_view', kw1='foo', kw2='bar')

        self.assertStrEqual('Url: {}'.format(url1), template1.render())
        self.assertStrEqual('Url: {}'.format(url2), template2.render({'arg1': 'foo'}))
        self.assertStrEqual('Url: {}'.format(url3), template3.render({'arg1': 'foo'}))

    def test_fail_mixed_args(self):
        template1 = lambda: self.env.from_string("{% url 'my_view' 'foo' other_arg='bar' %}")
        template2 = lambda: self.env.from_string("{% url 'my_view' arg1='foo' 'bar' %}")

        self.assertRaises(TemplateError, template1)
        self.assertRaises(TemplateError, template2)


if __name__ == '__main__':
    from django.conf import settings
    settings.configure()

    unittest.main()
