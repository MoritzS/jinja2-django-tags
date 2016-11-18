#!/usr/bin/env python

from setuptools import setup

setup(
    name='jinja2-django-tags',
    version='0.5',
    author='Moritz Sichert',
    author_email='moritz.sichert@googlemail.com',
    url='https://github.com/MoritzS/jinja2-django-tags',
    description='jinja2 extensions that add django tags',
    license='BSD',
    packages=['jdj_tags'],
    install_requires=[
        'Django>=1.8',
        'Jinja2>=2.7',
    ],
    classifiers=[
        'Framework :: Django',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='jinja2 jinja django template tags',
)
