"""
jinja2 extensions that add django tags.
"""
from __future__ import unicode_literals

from django.conf import settings
from django.core.urlresolvers import reverse
from django.templatetags.static import static as django_static
from django.utils.encoding import force_text
from django.utils.formats import localize
from django.utils.translation import pgettext, ugettext
from jinja2 import lexer, nodes
from jinja2.ext import Extension


class DjangoCsrf(Extension):
    """
    Implements django's `{% csrf_token %}` tag.
    """
    tags = set(['csrf_token'])

    def parse(self, parser):
        lineno = parser.stream.expect('name:csrf_token').lineno
        call = self.call_method(
            '_csrf_token',
            [nodes.Name('csrf_token', 'load', lineno=lineno)],
            lineno=lineno
        )
        return nodes.Output([nodes.MarkSafe(call)])

    def _csrf_token(self, csrf_token):
        if not csrf_token or csrf_token == 'NOTPROVIDED':
            return ''
        else:
            return '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />' \
                   .format(csrf_token)


class DjangoI18n(Extension):
    """
    Implements django's `{% trans %}` and `{% blocktrans %}` tags.
    It also tries to localize variables (such as dates and numbers) if
    `USE_L10N` is set in django settings.

    `{% trans %}` works as it does in django::

        Simple example: {% trans 'Hello World' %}

        {% trans "I was saved to a variable!" as translated_var %}
        Save to a variable: {{ translated_var }}

        Translation with context:
        {% trans 'Hello World' context 'second hello world example' %}

        Noop translation: {% trans "Please don't translate me!" noop %}


    `{% blocktrans %}` currently doesn't support the `count` argument, but
    everything else works::

        Simple example: {% blocktrans %}Hello World!{% endblocktrans %}

        Variables:
        {% url 'my_view' as my_url %}
        {% blocktrans with my_upper_url=my_url|upper %}
            Normal url: {{ my_url }}
            Upper url: {{ my_upper_url }}
        {% endblocktrans %}

        Trim whitespace:
        {% blocktrans trimmed %}
            Trim those
            pescy newlines.
        {% endblocktrans %}

    You also can use `_`, `gettext` and `pgettext` directly::

        Simple example: {{ _('Hello World') }}
        More verbose: {{ gettext('Hello World') }}
        With context: {{ pgettext('Hello World', 'another example') }}

    """
    tags = set(['trans', 'blocktrans'])

    def __init__(self, environment):
        super(DjangoI18n, self).__init__(environment)
        environment.globals['_'] = ugettext
        environment.globals['gettext'] = ugettext
        environment.globals['pgettext'] = pgettext
        if settings.USE_L10N:
            if environment.finalize is None:
                environment.finalize = localize
            else:
                old_finalize = environment.finalize

                def wrapper(var):
                    return localize(old_finalize(var))
                environment.finalize = wrapper

    def _parse_trans(self, parser, lineno):
        string = parser.stream.expect(lexer.TOKEN_STRING)
        string = nodes.Const(string.value, lineno=string.lineno)
        is_noop = False
        context = None
        as_var = None
        for token in iter(lambda: parser.stream.next_if(lexer.TOKEN_NAME), None):
            if token.value == 'noop' and not is_noop:
                if context is not None:
                    parser.fail("noop translation can't have context", lineno=token.lineno)
                is_noop = True
            elif token.value == 'context' and context is None:
                if is_noop:
                    parser.fail("noop translation can't have context", lineno=token.lineno)
                context = parser.stream.expect(lexer.TOKEN_STRING)
                context = nodes.Const(context.value, lineno=context.lineno)
            elif token.value == 'as' and as_var is None:
                as_var = parser.stream.expect(lexer.TOKEN_NAME)
                as_var = nodes.Name(as_var.value, 'store', lineno=as_var.lineno)
            else:
                parser.fail("expected 'noop', 'context' or 'as'", lineno=token.lineno)
        if is_noop:
            output = string
        elif context is not None:
            func = nodes.Name('pgettext', 'load', lineno=lineno)
            output = nodes.Call(func, [context, string], [], None, None, lineno=lineno)
        else:
            func = nodes.Name('gettext', 'load')
            output = nodes.Call(func, [string], [], None, None, lineno=lineno)

        if as_var is None:
            return nodes.Output([output], lineno=lineno)
        else:
            return nodes.Assign(as_var, output, lineno=lineno)

    def _parse_blocktrans(self, parser, lineno):
        with_vars = {}
        context = None
        trimmed = False

        if parser.stream.skip_if('name:trimmed'):
            trimmed = True

        if parser.stream.skip_if('name:with'):
            while parser.stream.look().type == lexer.TOKEN_ASSIGN:
                token = parser.stream.expect(lexer.TOKEN_NAME)
                key = token.value
                next(parser.stream)
                with_vars[key] = parser.parse_expression(False)

        if parser.stream.skip_if('name:context'):
            context = parser.stream.expect(lexer.TOKEN_STRING).value

        parser.stream.expect(lexer.TOKEN_BLOCK_END)

        body = []
        additional_vars = set()
        while not parser.stream.current.test(lexer.TOKEN_BLOCK_BEGIN):
            for token in iter(lambda: parser.stream.next_if(lexer.TOKEN_DATA), None):
                body.append(token.value)
            token = parser.stream.next_if(lexer.TOKEN_VARIABLE_BEGIN)
            if token is None:
                # endblocktrans tag must come now
                parser.stream.expect(lexer.TOKEN_BLOCK_BEGIN)
                break
            else:
                name = parser.stream.expect(lexer.TOKEN_NAME).value
                if name not in with_vars:
                    additional_vars.add(name)
                parser.stream.expect(lexer.TOKEN_VARIABLE_END)
                # django converts variables inside the blocktrans tag into
                # "%(var_name)s" format, so we do the same.
                body.append('%({})s'.format(name))

        parser.stream.skip_if(lexer.TOKEN_BLOCK_BEGIN)
        parser.stream.expect('name:endblocktrans')

        trans_vars = [
            nodes.Pair(nodes.Const(key), val, lineno=lineno)
            for key, val in with_vars.items()
        ]

        trans_vars.extend(
            nodes.Pair(
                nodes.Const(key),
                nodes.Name(key, 'load', lineno=lineno),
                lineno=lineno
            )
            for key in additional_vars
        )

        kwargs = [nodes.Keyword('trans_vars', nodes.Dict(trans_vars))]

        if context is not None:
            kwargs.append(nodes.Keyword('context', nodes.Const(context)))

        body = ''.join(body)
        if trimmed:
            body = ' '.join(map(lambda s: s.strip(), body.strip().splitlines()))

        call = self.call_method(
            '_make_blocktrans',
            [nodes.TemplateData(body)],
            kwargs
        )

        return nodes.Output([nodes.MarkSafe(call)])

    def _make_blocktrans(self, trans_str, context=None, trans_vars=None):
        if trans_vars is None:
            trans_vars = {}  # pragma: no cover
        if context is None:
            return ugettext(force_text(trans_str)) % trans_vars
        else:
            return pgettext(force_text(context), force_text(trans_str)) % trans_vars

    def parse(self, parser):
        token = next(parser.stream)
        if token.value == 'blocktrans':
            return self._parse_blocktrans(parser, token.lineno)
        else:
            return self._parse_trans(parser, token.lineno)


class DjangoStatic(Extension):
    """
    Implements django's `{% static %}` tag::

        My static file: {% static 'my/static.file' %}

        {% static 'my/static.file' as my_file %}
        My static file in a var: {{ my_file }}

    """
    tags = set(['static'])

    def _static(self, path):
        return django_static(path)

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        token = parser.stream.expect(lexer.TOKEN_STRING)
        path = nodes.Const(token.value)
        call = self.call_method('_static', [path], lineno=lineno)

        token = parser.stream.current
        if token.test('name:as'):
            next(parser.stream)
            as_var = parser.stream.expect(lexer.TOKEN_NAME)
            as_var = nodes.Name(as_var.value, 'store', lineno=as_var.lineno)
            return nodes.Assign(as_var, call, lineno=lineno)
        else:
            return nodes.Output([call], lineno=lineno)


class DjangoUrl(Extension):
    """
    Imlements django's `{% url %}` tag.
    It works as it does in django, therefore you can only specify either
    args or kwargs::

        Url with args: {% url 'my_view' arg1 "string arg2" %}
        Url with kwargs: {% url 'my_view' kwarg1=arg1 kwarg2="string arg2" %}

        Save to variable:
        {% url 'my_view' 'foo' 'bar' as my_url %}
        {{ my_url }}
    """
    tags = set(['url'])

    def _url_reverse(self, name, *args, **kwargs):
        return reverse(name, args=args, kwargs=kwargs)

    @staticmethod
    def parse_expression(parser):
        # Due to how the jinja2 parser works, it treats "foo" "bar" as a single
        # string literal as it is the case in python.
        # But the url tag in django supports multiple string arguments, e.g.
        # "{% url 'my_view' 'arg1' 'arg2' %}".
        # That's why we have to check if it's a string literal first.
        token = parser.stream.current
        if token.test(lexer.TOKEN_STRING):
            expr = nodes.Const(force_text(token.value), lineno=token.lineno)
            next(parser.stream)
        else:
            expr = parser.parse_expression(False)

        return expr

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        view_name = parser.stream.expect(lexer.TOKEN_STRING)
        view_name = nodes.Const(view_name.value, lineno=view_name.lineno)

        args = None
        kwargs = None
        as_var = None

        while parser.stream.current.type != lexer.TOKEN_BLOCK_END:
            token = parser.stream.current
            if token.test('name:as'):
                next(parser.stream)
                token = parser.stream.expect(lexer.TOKEN_NAME)
                as_var = nodes.Name(token.value, 'store', lineno=token.lineno)
                break
            if args is not None:
                args.append(self.parse_expression(parser))
            elif kwargs is not None:
                if token.type != lexer.TOKEN_NAME:
                    parser.fail(
                        "got '{}', expected name for keyword argument"
                        "".format(lexer.describe_token(token)),
                        lineno=token.lineno
                    )
                arg = token.value
                next(parser.stream)
                parser.stream.expect(lexer.TOKEN_ASSIGN)
                token = parser.stream.current
                kwargs[arg] = self.parse_expression(parser)
            else:
                if parser.stream.look().type == lexer.TOKEN_ASSIGN:
                    kwargs = {}
                else:
                    args = []
                continue

        if args is None:
            args = []
        args.insert(0, view_name)

        if kwargs is not None:
            kwargs = [nodes.Keyword(key, val) for key, val in kwargs.items()]

        call = self.call_method('_url_reverse', args, kwargs, lineno=lineno)
        if as_var is None:
            return nodes.Output([call], lineno=lineno)
        else:
            return nodes.Assign(as_var, call, lineno=lineno)


class DjangoCompat(DjangoCsrf, DjangoI18n, DjangoStatic, DjangoUrl):
    """
    Combines all extensions to one, so you don't have to put all of them
    in the django settings.
    """
    tags = set(['csrf_token', 'trans', 'blocktrans', 'static', 'url'])

    _tag_class = {
        'csrf_token': DjangoCsrf,
        'trans': DjangoI18n,
        'blocktrans': DjangoI18n,
        'static': DjangoStatic,
        'url': DjangoUrl,
    }

    def parse(self, parser):
        name = parser.stream.current.value
        cls = self._tag_class.get(name)
        if cls is None:
            parser.fail("got unexpected tag '{}'".format(name))  # pragma: no cover
        return cls.parse(self, parser)
