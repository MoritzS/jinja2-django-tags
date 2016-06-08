==================
jinja2-django-tags
==================
.. image:: https://img.shields.io/pypi/v/jinja2-django-tags.svg
   :alt: jinja2-django-tags on pypi
   :target: https://pypi.python.org/pypi/jinja2-django-tags

This little library contains extensions for jinja2 that add template tags to
jinja2 that you are used to from django templates.

The following tags are included:

- `csrf_token`_
- `trans and blocktrans`_
- `now`_
- `static`_
- `url`_

There is also an extension for `localizing template variables`_.

.. _trans and blocktrans: trans-blocktrans_
.. _localizing template variables: Localization_

Requirements
============

This library requires at least Django 1.8 because there official jinja2 support
was added.

If you want to use jinja2 templates in older versions of Django, take a look
at `django-jinja <https://github.com/niwinz/django-jinja>`_.

This library has been tested on Python 2.7, 3.4 and 3.5, Jinja 2.7 and 2.8, and
Django 1.8, 1.9 and 1.10.

Usage
=====
To use the tags, just run ``setup.py install`` from the base directory or
``pip install jinja2-django-tags`` and add the extensions to your ``TEMPLATES``
settings:

.. code-block:: python

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

If you want all tags at once use ``jdj_tags.extensions.DjangoCompat`` in
the ``extensions`` Option.

Tags
====

csrf_token
----------
The ``{% csrf_token %}`` tag comes with ``jdj_tags.extensions.DjangoCsrf``.

.. _trans-blocktrans:
trans, blocktrans
-----------------
The i18n tags are defined in ``jdj_tags.extensions.DjangoI18n``.
The extension also tries to localize variables (such as dates and numbers) if
``USE_L10N`` is set in django settings.

``{% trans %}`` works as it does in django:

.. code-block:: html+django/jinja

    Simple example: {% trans 'Hello World' %}

    {% trans "I was saved to a variable!" as translated_var %}
    Save to a variable: {{ translated_var }}

    Translation with context:
    {% trans 'Hello World' context 'second hello world example' %}

    Noop translation: {% trans "Please don't translate me!" noop %}


``{% blocktrans %}`` works as it does in django including ``with``, ``trimmed``,
``context``, ``count`` and ``asvar`` arguments:


.. code-block:: html+django/jinja

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

You can also use ``_``, ``gettext`` and ``pgettext`` directly:

.. code-block:: html+django/jinja

    Simple example: {{ _('Hello World') }}
    More verbose: {{ gettext('Hello World') }}
    With context: {{ pgettext('Hello World', 'another example') }}


now
---
The ``{% now %}`` tag comes with ``jdj_tags.extensions.DjangoNow``.
It works the same as in Django:

.. code-block:: html+django/jinja

    Current year: {% now 'Y' %}

    {% now 'Y' as cur_year %}
    Copyright My Company, {{ cur_year }}


static
------
The ``{% static %}`` tag comes with ``jdj_tags.extensions.DjangoStatic``.
It works the same as in Django:

.. code-block:: html+django/jinja

    My static file: {% static 'my/static.file' %}

    {% static 'my/static.file' as my_file %}
    My static file in a var: {{ my_file }}


url
---
The ``{% url %}`` tag is defined in ``jdj_tags.extensions.DjangoUrl``.
It works as it does in django, therefore you can only specify either
args or kwargs:

.. code-block:: html+django/jinja
    Url with args: {% url 'my_view' arg1 "string arg2" %}
    Url with kwargs: {% url 'my_view' kwarg1=arg1 kwarg2="string arg2" %}

    Save to variable:
    {% url 'my_view' 'foo' 'bar' as my_url %}
    {{ my_url }}


Localization
============

The ``jdj_tags.extensions.DjangoL10n`` extension implements localization of template variables
with respect to ``USE_L10N`` and ``USE_TZ`` settings:

.. code-block:: python

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
