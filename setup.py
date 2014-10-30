#!/usr/bin/env python
import os
from setuptools import setup, find_packages

def get_readme():
    return open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

setup(
    name='DRF Ember',
    version='0.1.0',
    description="Django Rest Framework addons to integrate with Ember.js",
    long_description=get_readme(),
    author="Gordon Cassie",
    author_email='gordoncassie@gmail.com',
    url='https://github.com/ngenworks/rest_framework_ember',
    license='BSD',
    keywords="EmberJS Django REST",
    packages=find_packages(),
    install_requires=['django', 'djangorestframework', 'inflection'],
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