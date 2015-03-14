#!/usr/bin/env python

from setuptools import setup

setup(
    name='jinja2-django-tags',
    version='0.1',
    author='Moritz Sichert',
    author_email='moritz.sichert@googlemail.com',
    description='jinja2 extensions that add django tags',
    license='BSD',
    packages=['jdj_tags'],
    install_requires=[
        'Django>=1.8b2',
        'Jinja2>=2.7',
    ],
    classifiers=[
        'Framework :: Django',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
    ],
)
