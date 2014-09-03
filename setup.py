# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='machete',
    version='0.1.0',
    author='Kevin Wetzels',
    author_email='kevin@roam.be',
    url='https://github.com/roam/machete',
    install_requires=['Django>=1.4'],
    packages=find_packages(exclude=['tests']),
    license='BSD',
    description='Django-based JSON API library',
    long_description=open('README.rst').read(),
    classifiers = [
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Framework :: Django',
   ],
)