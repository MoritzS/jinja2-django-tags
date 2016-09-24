"""
jinja2 extensions that add django tags.
"""
from __future__ import unicode_literals

from datetime import datetime

from django.conf import settings
from django.templatetags.static import static as django_static
from django.utils.encoding import force_text
from django.utils.formats import date_format, localize
from django.utils.timezone import get_current_timezone, template_localtime
from django.utils.translation import npgettext, pgettext, ugettext, ungettext
from jinja2 import lexer, nodes
from jinja2.ext import Extension

try:
    from django.urls import reverse
except:
    from django.core.urlresolvers import reverse


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

    `{% trans %}` works as it does in django::

        Simple example: {% trans 'Hello World' %}

        {% trans "I was saved to a variable!" as translated_var %}
        Save to a variable: {{ translated_var }}

        Translation with context:
        {% trans 'Hello World' context 'second hello world example' %}

        Noop translation: {% trans "Please don't translate me!" noop %}


    `{% blocktrans %}` works as it does in django including `with`, `trimmed`,
    `context`, `count` and `asvar` arguments::

        Simple example: {% blocktrans %}Hello World!{% endblocktrans %}

        Variables:
        {% url 'my_view' as my_url %}
        {% blocktrans with my_upper_url=my_url|upper %}
            Normal url: {{ my_url }}
            Upper url: {{ my_upper_url }}
        {% endblocktrans %}

        Trim whitespace and save to variable:
        {% blocktrans trimmed asvar translated_var %}
            Trim those
            pesky newlines.
        {% endblocktrans %}
        Translated text: {{ translated_var }}

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
        count = None
        context = None
        trimmed = False
        as_var = None

        if parser.stream.skip_if('name:trimmed'):
            trimmed = True

        if parser.stream.skip_if('name:asvar'):
            as_var = parser.stream.expect(lexer.TOKEN_NAME)
            as_var = nodes.Name(as_var.value, 'store', lineno=as_var.lineno)

        if parser.stream.skip_if('name:with'):
            while parser.stream.look().type == lexer.TOKEN_ASSIGN:
                token = parser.stream.expect(lexer.TOKEN_NAME)
                key = token.value
                next(parser.stream)
                with_vars[key] = parser.parse_expression(False)

        if parser.stream.skip_if('name:count'):
            name = parser.stream.expect(lexer.TOKEN_NAME).value
            parser.stream.expect(lexer.TOKEN_ASSIGN)
            value = parser.parse_expression(False)
            count = (name, value)

        if parser.stream.skip_if('name:context'):
            context = parser.stream.expect(lexer.TOKEN_STRING).value

        parser.stream.expect(lexer.TOKEN_BLOCK_END)

        body_singular = None
        body = []
        additional_vars = set()
        for token in parser.stream:
            if token is lexer.TOKEN_EOF:
                parser.fail('unexpected end of template, expected endblocktrans tag')
            if token.type is lexer.TOKEN_DATA:
                body.append(token.value)
            elif token.type is lexer.TOKEN_VARIABLE_BEGIN:
                name = parser.stream.expect(lexer.TOKEN_NAME).value
                if name not in with_vars and (count is None or count[0] != name):
                    additional_vars.add(name)
                parser.stream.expect(lexer.TOKEN_VARIABLE_END)
                # django converts variables inside the blocktrans tag into
                # "%(var_name)s" format, so we do the same.
                body.append('%({})s'.format(name))
            elif token.type is lexer.TOKEN_BLOCK_BEGIN:
                if body_singular is None and parser.stream.skip_if('name:plural'):
                    if count is None:
                        parser.fail('used plural without specifying count')
                    parser.stream.expect(lexer.TOKEN_BLOCK_END)
                    body_singular = body
                    body = []
                else:
                    parser.stream.expect('name:endblocktrans')
                    break

        if count is not None and body_singular is None:
            parser.fail('plural form not found')

        trans_vars = [
            nodes.Pair(nodes.Const(key), val, lineno=lineno)
            for key, val in with_vars.items()
        ]

        if count is not None:
            trans_vars.append(
                nodes.Pair(nodes.Const(count[0]), count[1], lineno=lineno)
            )

        trans_vars.extend(
            nodes.Pair(
                nodes.Const(key),
                nodes.Name(key, 'load', lineno=lineno),
                lineno=lineno
            )
            for key in additional_vars
        )

        kwargs = [
            nodes.Keyword('trans_vars', nodes.Dict(trans_vars, lineno=lineno), lineno=lineno)
        ]

        if context is not None:
            kwargs.append(
                nodes.Keyword('context', nodes.Const(context, lineno=lineno), lineno=lineno)
            )
        if count is not None:
            kwargs.append(
                nodes.Keyword('count_var', nodes.Const(count[0], lineno=lineno), lineno=lineno)
            )

        body = ''.join(body)
        if trimmed:
            body = ' '.join(map(lambda s: s.strip(), body.strip().splitlines()))

        if body_singular is not None:
            body_singular = ''.join(body_singular)
            if trimmed:
                body_singular = ' '.join(
                    map(lambda s: s.strip(), body_singular.strip().splitlines())
                )

        if body_singular is None:
            args = []
        else:
            args = [nodes.TemplateData(body_singular, lineno=lineno)]
        args.append(nodes.TemplateData(body, lineno=lineno))
        call = nodes.MarkSafe(self.call_method('_make_blocktrans', args, kwargs), lineno=lineno)

        if as_var is None:
            return nodes.Output([call], lineno=lineno)
        else:
            return nodes.Assign(as_var, call)

    def _make_blocktrans(self, singular, plural=None, context=None, trans_vars=None,
                         count_var=None):
        if trans_vars is None:
            trans_vars = {}  # pragma: no cover
        if self.environment.finalize:
            finalized_trans_vars = {
                key: self.environment.finalize(val) for key, val in trans_vars.items()
            }
        else:
            finalized_trans_vars = trans_vars
        if plural is None:
            if context is None:
                return ugettext(force_text(singular)) % finalized_trans_vars
            else:
                return pgettext(force_text(context), force_text(singular)) % finalized_trans_vars
        else:
            if context is None:
                return ungettext(
                    force_text(singular), force_text(plural), trans_vars[count_var]
                ) % finalized_trans_vars
            else:
                return npgettext(
                    force_text(context), force_text(singular), force_text(plural),
                    trans_vars[count_var]
                ) % finalized_trans_vars

    def parse(self, parser):
        token = next(parser.stream)
        if token.value == 'blocktrans':
            return self._parse_blocktrans(parser, token.lineno)
        else:
            return self._parse_trans(parser, token.lineno)


class DjangoL10n(Extension):
    """
    Implements localization of template variables with respect to
    `USE_L10N` and `USE_TZ` settings::

        >>> from datetime import datetime
        >>> from django.utils import timezone, translation
        >>> from jinja2 import Extension
        >>> env = Environment(extensions=[DjangoL10n])
        >>> template = env.from_string("{{ a_number }} {{ a_date }}")
        >>> context = {
        ...     'a_number': 1.23,
        ...     'a_date': datetime(2000, 10, 1, 14, 10, 12, tzinfo=timezone.utc),
        ... }
        >>> translation.activate('en')
        >>> timezone.activate('America/Argentina/Buenos_Aires')
        >>> template.render(context)
        '1.23 Oct. 1, 2000, 11:10 a.m.'
        >>> translation.activate('de')
        >>> translation.activate('Europe/Berlin')
        >>> template.render(context)
        '1,23 1. Oktober 2000 16:10'

    """

    def __init__(self, environment):
        super(DjangoL10n, self).__init__(environment)
        finalize = []
        if settings.USE_TZ:
            finalize.append(template_localtime)
        if settings.USE_L10N:
            finalize.append(localize)

        if finalize:
            fns = iter(finalize)
            if environment.finalize is None:
                new_finalize = next(fns)
            else:
                new_finalize = environment.finalize
            for f in fns:
                new_finalize = self._compose(f, new_finalize)

            environment.finalize = new_finalize

    @staticmethod
    def _compose(f, g):
        return lambda var: f(g(var))


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


class DjangoNow(Extension):
    """
    Implements django's `{% now %}` tag.
    """
    tags = set(['now'])

    def _now(self, format_string):
        tzinfo = get_current_timezone() if settings.USE_TZ else None
        cur_datetime = datetime.now(tz=tzinfo)
        return date_format(cur_datetime, format_string)

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        token = parser.stream.expect(lexer.TOKEN_STRING)
        format_string = nodes.Const(token.value)
        call = self.call_method('_now', [format_string], lineno=lineno)

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


class DjangoCompat(DjangoCsrf, DjangoI18n, DjangoL10n, DjangoNow, DjangoStatic, DjangoUrl):
    """
    Combines all extensions to one, so you don't have to put all of them
    in the django settings.
    """
    tags = set(['csrf_token', 'trans', 'blocktrans', 'now', 'static', 'url'])

    _tag_class = {
        'csrf_token': DjangoCsrf,
        'trans': DjangoI18n,
        'blocktrans': DjangoI18n,
        'now': DjangoNow,
        'static': DjangoStatic,
        'url': DjangoUrl,
    }

    def parse(self, parser):
        name = parser.stream.current.value
        cls = self._tag_class.get(name)
        if cls is None:
            parser.fail("got unexpected tag '{}'".format(name))  # pragma: no cover
        return cls.parse(self, parser)
