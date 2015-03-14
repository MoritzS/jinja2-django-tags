# jinja2-django-tags
This little library contains extensions for jinja2 that add template tags to jinja2
that your are used to from django templates.

## Usage
To use the tags, just run `setup.py install` and add the extensions to your `TEMPLATES` settings:
```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'extensions': [
                'jdj_tags.extensions.DjangoStatic',
                'jdj_tags.extensions.DjangoI18n',
            ]
        },
    },
}
```

If you want all tags at once use `jdj_tags.extensions.DjangoCompat` in the `extensions` Option.

## Tags

### csrf\_token
The `{% csrf_token %}` tag comes with `jdj_tags.extensions.DjangoCsrf`.

### trans, blocktrans
The i18n tags are defined in `jdj_tags.extensions.DjangoI18n`.
The extension also tries to localize variables (such as dates and numbers) if
`USE_L10N` is set in django settings.

`{% trans %}` works as it does in django:

```html+django
    Simple example: {% trans 'Hello World' %}

    {% trans "I was saved to a variable!" as translated_var %}
    Save to a variable: {{ translated_var }}

    Translation with context:
    {% trans 'Hello World' context 'second hello world example' %}

    Noop translation: {% trans "Please don't translate me!" noop %}
```

`{% blocktrans %}` currently doesn't support the `count` argument, but
everything else works:

```html+django
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
        pesky newlines.
    {% endblocktrans %}
```

You also can use `_`, `gettext` and `pgettext` directly:

```html+django
    Simple example: {{ _('Hello World') }}
    More verbose: {{ gettext('Hello World') }}
    With context: {{ pgettext('Hello World', 'another example') }}
```

### static
The `{% static %}` comes with `jdj_tags.extensions.DjangoStatic`.
It works the same as in Django:

```html+django
    My static file: {% static 'my/static.file' %}

    {% static 'my/static.file' as my_file %}
    My static file in a var: {{ my_file }}
```

### url
The `{% url %}` is defined in `jdj_tags.extensions.DjangoUrl`.
It works as it does in django, therefore you can only specify either
args or kwargs:

```html+django
    Url with args: {% url 'my_view' arg1 "string arg2" %}
    Url with kwargs: {% url 'my_view' kwarg1=arg1 kwarg2="string arg2" %}

    Save to variable:
    {% url 'my_view' 'foo' 'bar' as my_url %}
    {{ my_url }}
```
