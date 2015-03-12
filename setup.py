#!/usr/bin/env python
import os
from setuptools import setup, find_packages

setup(
    name='emberdrf',
    version='0.1.8',
    description="Django Rest Framework addons to integrate with Ember.js",
    author="Gordon Cassie",
    author_email='gordoncassie@gmail.com',
    url='https://github.com/g-cassie/ember-drf',
    license='BSD',
    keywords="EmberJS Django REST",
    packages=find_packages(),
    install_requires=[],
    platforms=['any'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Environment :: Web Environment',
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
