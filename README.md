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

Then either run:

    $ python manage.py syncdb
    ...

Or rename db.sqlite3.example to db.sqlite3:

    $ cp db.sqlite3.example db.sqlite3

Finally start the server:

    $ python manage.py runserver

Play around with it ([HTTPie](https://github.com/jakubroztocil/httpie) is recommended) by opening [http://localhost:8000/api/posts]()
