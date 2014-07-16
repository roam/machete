# Machete

Basic proof of concept of JSON API in Django.

Uses [Marshmallow](http://marshmallow.readthedocs.org/en/latest/) (v0.7.0)
for serialization and basic Django class-based views to implement at least part of the JSON API spec.


## Installation

First, get the source. Then:

    $ mkvirtualenv jsonapi
    ...
    $ pip install marshmallow==0.7.0
    ...
    $ pip install Django==1.6.5
    ...
    $ cd blogger
    $ python manage.py syncdb
    ...
    $ python manage.py runserver
    ...

